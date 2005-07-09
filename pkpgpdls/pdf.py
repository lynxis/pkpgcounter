#! /usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# pkpgcounter : a generic Page Description Language parser
#
# (c) 2003, 2004, 2005 Jerome Alet <alet@librelogiciel.com>
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

import sys
import re

import pdlparser

class Parser(pdlparser.PDLParser) :
    """A parser for PDF documents."""
    def isValid(self) :    
        """Returns 1 if data is PDF, else 0."""
        if self.firstblock.startswith("%PDF-") or \
           self.firstblock.startswith("\033%-12345X%PDF-") or \
           ((self.firstblock[:128].find("\033%-12345X") != -1) and (self.firstblock.upper().find("LANGUAGE=PDF") != -1)) or \
           (self.firstblock.find("%PDF-") != -1) :
            if self.debug :  
                sys.stderr.write("DEBUG: Input file is in the PDF format.\n")
            return 1
        else :    
            return 0
        
    def getJobSize(self) :    
        """Counts pages in a PDF document."""
        self.iscolor = None
        newpageregexp = re.compile(r"(/Type) ?(/Page)[/ \t\r\n]", re.I)
        colorregexp = re.compile(r"(/ColorSpace) ?(/DeviceRGB|/DeviceCMYK)[/ \t\r\n]", re.I)
        pagecount = 0
        for line in self.infile.xreadlines() : 
            pagecount += len(newpageregexp.findall(line))
            if colorregexp.match(line) :
                self.iscolor = 1
                if self.debug :
                    sys.stderr.write("ColorSpace : %s\n" % line)
        return pagecount    
        
def test() :        
    """Test function."""
    if (len(sys.argv) < 2) or ((not sys.stdin.isatty()) and ("-" not in sys.argv[1:])) :
        sys.argv.append("-")
    totalsize = 0    
    for arg in sys.argv[1:] :
        if arg == "-" :
            infile = sys.stdin
            mustclose = 0
        else :    
            infile = open(arg, "rb")
            mustclose = 1
        try :
            parser = Parser(infile, debug=1)
            totalsize += parser.getJobSize()
        except pdlparser.PDLParserError, msg :    
            sys.stderr.write("ERROR: %s\n" % msg)
            sys.stderr.flush()
        if mustclose :    
            infile.close()
    print "%s" % totalsize
    
if __name__ == "__main__" :    
    test()
