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

"""This modules implements a page counter for TIFF documents."""

import sys
import os
import mmap
from struct import unpack

import pdlparser
import pjl

class Parser(pdlparser.PDLParser) :
    """A parser for ESC/PAGES03 documents."""
    def isValid(self) :        
        """Returns True if data is TIFF, else False."""
        if self.firstblock.startswith("\033\1@EJL") and \
            (self.firstblock.find("=ESC/PAGES03\n") != -1) :
            self.logdebug("DEBUG: Input file is in the ESC/PAGES03 format.")
            return True
        else :    
            return False
    
    def getJobSize(self) :
        """Counts pages in an ESC/PAGES03 document.
        
           Algorithm by Jerome Alet.
           Reverse engineered the file format.
        """
        infileno = self.infile.fileno()
        minfile = mmap.mmap(infileno, os.fstat(infileno)[6], prot=mmap.PROT_READ, flags=mmap.MAP_SHARED)
        pagecount = 0
        marker = "=ESC/PAGES03\n"
        startpos = minfile.find(marker)
        startsequence = chr(0x1d)
        if startpos == -1 :
            raise pdlparser.PDLParserError, "Invalid ESC/PAGES03 file."
        startpos += len(marker)
        if minfile[startpos] != startsequence :
            raise pdlparser.PDLParserError, "Invalid ESC/PAGES03 file."
        endsequence = "eps{I"
        lgendsequence = len(endsequence)
        try :
            try :    
                while True :
                    if minfile[startpos] == startsequence :
                        #self.logdebug("Start sequence at %08x" % startpos)
                        skiplen = 0
                        while True :
                            startpos += 1
                            c = minfile[startpos]
                            if not c.isdigit() :
                                #self.logdebug("stop on %02x at %08x" % (ord(c), startpos))
                                break
                            else :
                                skiplen = (skiplen * 10) + int(c)
                        if minfile[startpos:startpos+lgendsequence] == endsequence :
                            #self.logdebug("skipped %i bytes at %08x until %08x" % (skiplen, startpos, startpos+skiplen+lgendsequence))
                            startpos += skiplen + lgendsequence
                        else :    
                            #self.logdebug("Problem at %08x" % startpos)
                            pass
                    else :
                        if minfile[startpos:startpos+6] == "\033\1@EJL" :
                            # self.logdebug("EJL found at %08x" % startpos)
                            ejlparser = pjl.EJLParser(minfile[startpos:])
                            pagecount = ejlparser.environment_variables.get("PAGES", "1")
                            if pagecount.startswith('"') and pagecount.endswith('"') :
                                pagecount = pagecount[1:-1]
                            pagecount = int(pagecount)    
                            if pagecount <= 0 :
                                pagecount = 1 # TODO : 1000000 ;-)
                            break
                        else :    
                            #self.logdebug("Skipped byte at %08x" % startpos)
                            pass
                        startpos += 1    
            except IndexError :            
                pass
        finally :        
            minfile.close()
        return pagecount
        
if __name__ == "__main__" :    
    pdlparser.test(Parser)
