#! /usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# pkpgcounter : a generic Page Description Language parser
#
# (c) 2003, 2004, 2005, 2006, 2007 Jerome Alet <alet@librelogiciel.com>
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# $Id$
#

"""This modules implements a page counter for PostScript documents."""

import sys
import os
import tempfile
import popen2

import pdlparser
import inkcoverage

class Parser(pdlparser.PDLParser) :
    """A parser for PostScript documents."""
    totiffcommands = [ 'gs -sDEVICE=tiff24nc -dPARANOIDSAFER -dNOPAUSE -dBATCH -dQUIET -r%(dpi)i -sOutputFile="%(fname)s" -' ]
    def isValid(self) :    
        """Returns True if data is PostScript, else False."""
        if self.firstblock.startswith("%!") or \
           self.firstblock.startswith("\004%!") or \
           self.firstblock.startswith("\033%-12345X%!PS") or \
           ((self.firstblock[:128].find("\033%-12345X") != -1) and \
             ((self.firstblock.find("LANGUAGE=POSTSCRIPT") != -1) or \
              (self.firstblock.find("LANGUAGE = POSTSCRIPT") != -1) or \
              (self.firstblock.find("LANGUAGE = Postscript") != -1))) or \
              (self.firstblock.find("%!PS-Adobe") != -1) :
            self.logdebug("DEBUG: Input file is in the PostScript format.")
            return True
        else :    
            return False
        
    def throughGhostScript(self) :
        """Get the count through GhostScript, useful for non-DSC compliant PS files."""
        self.logdebug("Internal parser sucks, using GhostScript instead...")
        self.infile.seek(0)
        command = 'gs -sDEVICE=bbox -dPARANOIDSAFER -dNOPAUSE -dBATCH -dQUIET - 2>&1 | grep -c "%%HiResBoundingBox:" 2>/dev/null'
        child = popen2.Popen4(command)
        try :
            data = self.infile.read(pdlparser.MEGABYTE)    
            while data :
                child.tochild.write(data)
                data = self.infile.read(pdlparser.MEGABYTE)
            child.tochild.flush()
            child.tochild.close()    
        except (IOError, OSError), msg :    
            raise pdlparser.PDLParserError, "Problem during analysis of Binary PostScript document : %s" % msg
            
        pagecount = 0
        try :
            pagecount = int(child.fromchild.readline().strip())
        except (IOError, OSError, AttributeError, ValueError), msg :
            raise pdlparser.PDLParserError, "Problem during analysis of Binary PostScript document : %s" % msg
        child.fromchild.close()
        
        try :
            child.wait()
        except OSError, msg :    
            raise pdlparser.PDLParserError, "Problem during analysis of Binary PostScript document : %s" % msg
        self.logdebug("GhostScript said : %s pages" % pagecount)    
        return pagecount * self.copies
        
    def natively(self) :
        """Count pages in a DSC compliant PostScript document."""
        self.infile.seek(0)
        pagecount = 0
        self.pages = { 0 : { "copies" : 1 } }
        oldpagenum = None
        previousline = ""
        notrust = 0
        prescribe = 0 # Kyocera's Prescribe commands
        acrobatmarker = 0
        for line in self.infile.xreadlines() : 
            if (not prescribe) and line.startswith(r"%%BeginResource: procset pdf") \
               and not acrobatmarker :
                notrust = 1 # Let this stuff be managed by GhostScript, but we still extract number of copies
            elif line.startswith(r"%ADOPrintSettings: L") :
                acrobatmarker = 1
            elif line.startswith("!R!") :
                prescribe = 1
            elif line.startswith(r"%%Page: ") or line.startswith(r"(%%[Page: ") :
                proceed = 1
                try :
                    # treats both "%%Page: x x" and "%%Page: (x-y) z" (probably N-up mode)
                    newpagenum = int(line.split(']')[0].split()[-1])
                except :    
                    notinteger = 1 # It seems that sometimes it's not an integer but an EPS file name
                else :    
                    notinteger = 0
                    if newpagenum == oldpagenum :
                        proceed = 0
                    else :
                        oldpagenum = newpagenum
                if proceed and not notinteger :        
                    pagecount += 1
                    self.pages[pagecount] = { "copies" : self.pages[pagecount-1]["copies"] }
            elif line.startswith(r"%%Requirements: numcopies(") :    
                try :
                    number = int(line.strip().split('(')[1].split(')')[0])
                except :     
                    pass
                else :    
                    if number > self.pages[pagecount]["copies"] :
                        self.pages[pagecount]["copies"] = number
            elif line.startswith(r"%%BeginNonPPDFeature: NumCopies ") :
                # handle # of copies set by some Windows printer driver
                try :
                    number = int(line.strip().split()[2])
                except :     
                    pass
                else :    
                    if number > self.pages[pagecount]["copies"] :
                        self.pages[pagecount]["copies"] = number
            elif line.startswith("1 dict dup /NumCopies ") :
                # handle # of copies set by mozilla/kprinter
                try :
                    number = int(line.strip().split()[4])
                except :     
                    pass
                else :    
                    if number > self.pages[pagecount]["copies"] :
                        self.pages[pagecount]["copies"] = number
            elif line.startswith("{ pop 1 dict dup /NumCopies ") :
                # handle # of copies set by firefox/kprinter/cups (alternate syntax)
                try :
                    number = int(line.strip().split()[6])
                except :
                    pass
                else :
                    if number > self.pages[pagecount]["copies"] :
                        self.pages[pagecount]["copies"] = number
            elif line.startswith("/languagelevel where{pop languagelevel}{1}ifelse 2 ge{1 dict dup/NumCopies") :
                try :
                    number = int(previousline.strip()[2:])
                except :
                    pass
                else :
                    if number > self.pages[pagecount]["copies"] :
                        self.pages[pagecount]["copies"] = number
            elif line.startswith("/#copies ") :
                try :
                    number = int(line.strip().split()[1])
                except :     
                    pass
                else :    
                    if number > self.pages[pagecount]["copies"] :
                        self.pages[pagecount]["copies"] = number
            previousline = line
            
        # extract max number of copies to please the ghostscript parser, just    
        # in case we will use it later
        self.copies = max([ v["copies"] for (k, v) in self.pages.items() ])
        
        # now apply the number of copies to each page
        for pnum in range(1, pagecount + 1) :
            page = self.pages.get(pnum, self.pages.get(1, { "copies" : 1 }))
            copies = page["copies"]
            pagecount += (copies - 1)
            self.logdebug("%s * page #%s" % (copies, pnum))
        self.logdebug("Internal parser said : %s pages" % pagecount)
        return (pagecount, notrust)
        
    def getJobSize(self) :    
        """Count pages in PostScript document."""
        self.copies = 1
        (nbpages, notrust) = self.natively()
        newnbpages = nbpages
        if notrust :
            try :
                newnbpages = self.throughGhostScript()
            except pdlparser.PDLParserError, msg :
                self.logdebug(msg)
        return max(nbpages, newnbpages)    
        
if __name__ == "__main__" :    
    pdlparser.test(Parser)
