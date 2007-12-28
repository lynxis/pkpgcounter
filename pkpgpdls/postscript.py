#! /usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# pkpgcounter : a generic Page Description Language parser
#
# (c) 2003, 2004, 2005, 2006, 2007 Jerome Alet <alet@librelogiciel.com>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# $Id$
#

"""This modules implements a page counter for PostScript documents."""

import sys
import os

import pdlparser
import inkcoverage

class Parser(pdlparser.PDLParser) :
    """A parser for PostScript documents."""
    totiffcommands = [ 'gs -sDEVICE=tiff24nc -dPARANOIDSAFER -dNOPAUSE -dBATCH -dQUIET -r"%(dpi)i" -sOutputFile="%(outfname)s" "%(infname)s"' ]
    required = [ "gs" ]
    openmode = "rU"
    format = "PostScript"
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
            return True
        else :    
            return False
        
    def throughGhostScript(self) :
        """Get the count through GhostScript, useful for non-DSC compliant PS files."""
        self.logdebug("Internal parser sucks, using GhostScript instead...")
        if self.isMissing(self.required) :
            raise pdlparser.PDLParserError, "The gs interpreter is nowhere to be found in your PATH (%s)" % os.environ.get("PATH", "")
        infname = self.filename
        command = 'gs -sDEVICE=bbox -dPARANOIDSAFER -dNOPAUSE -dBATCH -dQUIET "%(infname)s" 2>&1 | grep -c "%%HiResBoundingBox:" 2>/dev/null'
        pagecount = 0
        fromchild = os.popen(command % locals(), "r")
        try :
            try :
                pagecount = int(fromchild.readline().strip())
            except (IOError, OSError, AttributeError, ValueError), msg :
                raise pdlparser.PDLParserError, "Problem during analysis of Binary PostScript document : %s" % msg
        finally :        
            if fromchild.close() is not None :
                raise pdlparser.PDLParserError, "Problem during analysis of Binary PostScript document"
        self.logdebug("GhostScript said : %s pages" % pagecount)    
        return pagecount * self.copies
        
    def setcopies(self, pagenum, txtvalue) :    
        """Tries to extract a number of copies from a textual value and set the instance attributes accordingly."""
        try :
            number = int(txtvalue)
        except (ValueError, TypeError) :     
            pass
        else :    
            if number > self.pages[pagenum]["copies"] :
                self.pages[pagenum]["copies"] = number
                
    def natively(self) :
        """Count pages in a DSC compliant PostScript document."""
        pagecount = 0
        self.pages = { 0 : { "copies" : 1 } }
        oldpagenum = None
        previousline = ""
        notrust = False
        prescribe = False # Kyocera's Prescribe commands
        acrobatmarker = False
        pagescomment = None
        for line in self.infile :
            line = line.strip()
            parts = line.split()
            nbparts = len(parts)
            part0 = parts[0]
            if part0 == r"%ADOPrintSettings:" :
                acrobatmarker = True
            elif part0 == "!R!" :    
                prescribe = True
            elif part0 == r"%%Pages:" :
                try :
                    pagescomment = max(pagescomment or 0, int(parts[1]))
                except ValueError :
                    pass # strange, to say the least
            elif (part0 == r"%%BeginNonPPDFeature:") \
                  and (nbparts > 2) \
                  and (parts[1] == "NumCopies") :
                self.setcopies(pagecount, parts[2])
            elif (part0 == r"%%Requirements:") \
                  and (nbparts > 1) \
                  and (parts[1] == "numcopies(") :
                try :
                    self.setcopies(pagecount, line.split('(')[1].split(')')[0])
                except IndexError :
                    pass
            elif part0 == "/#copies" :
                if nbparts > 1 :
                    self.setcopies(pagecount, parts[1])
            elif part0 == r"%RBINumCopies:" :   
                if nbparts > 1 :
                    self.setcopies(pagecount, parts[1])
            elif (parts[:4] == ["1", "dict", "dup", "/NumCopies"]) \
                  and (nbparts > 4) :
                # handle # of copies set by mozilla/kprinter
                self.setcopies(pagecount, parts[4])
            elif (parts[:6] == ["{", "pop", "1", "dict", "dup", "/NumCopies"]) \
                  and (nbparts > 6) :
                # handle # of copies set by firefox/kprinter/cups (alternate syntax)
                self.setcopies(pagecount, parts[6])
            elif (part0 == r"%%Page:") or (part0 == r"(%%[Page:") :
                proceed = True
                try :
                    # treats both "%%Page: x x" and "%%Page: (x-y) z" (probably N-up mode)
                    newpagenum = int(line.split(']')[0].split()[-1])
                except :    
                    notinteger = True # It seems that sometimes it's not an integer but an EPS file name
                else :    
                    notinteger = False
                    if newpagenum == oldpagenum :
                        proceed = False
                    else :
                        oldpagenum = newpagenum
                if proceed and not notinteger :        
                    pagecount += 1
                    self.pages[pagecount] = { "copies" : self.pages[pagecount-1]["copies"] }
            elif (not prescribe) \
               and (parts[:3] == [r"%%BeginResource:", "procset", "pdf"]) \
               and not acrobatmarker :
                notrust = True # Let this stuff be managed by GhostScript, but we still extract number of copies
            elif line.startswith("/languagelevel where{pop languagelevel}{1}ifelse 2 ge{1 dict dup/NumCopies") :
                self.setcopies(pagecount, previousline[2:])
            elif (nbparts > 1) and (parts[1] == "@copies") :
                self.setcopies(pagecount, part0)
            previousline = line
            
        # extract max number of copies to please the ghostscript parser, just    
        # in case we will use it later
        self.copies = max([ v["copies"] for (k, v) in self.pages.items() ])
        
        # now apply the number of copies to each page
        if not pagecount and pagescomment :    
            pagecount = pagescomment
        for pnum in range(1, pagecount + 1) :
            page = self.pages.get(pnum, self.pages.get(1, self.pages.get(0, { "copies" : 1 })))
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
        if notrust or not nbpages :
            try :
                newnbpages = self.throughGhostScript()
            except pdlparser.PDLParserError, msg :
                self.logdebug(msg)
        return max(nbpages, newnbpages)    
