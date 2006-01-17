#! /usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# pkpgcounter : a generic Page Description Language parser
#
# (c) 2003, 2004, 2005, 2006 Jerome Alet <alet@librelogiciel.com>
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
import os
import mmap
from struct import unpack

import pdlparser

class Parser(pdlparser.PDLParser) :
    """A parser for DVI documents."""
    def isValid(self) :        
        """Returns 1 if data is DVI, else 0."""
        try :
            if (ord(self.firstblock[0]) == 0xf7) and (ord(self.lastblock[-1]) == 0xdf) :
                self.logdebug("DEBUG: Input file is in the DVI format.")
                return 1
            else :    
                return 0
        except IndexError :          
            return 0
            
    def getJobSize(self) :
        """Counts pages in a DVI document.
        
           Algorithm by Jerome Alet.
           
           The documentation used for this was :
         
           http://www.math.umd.edu/~asnowden/comp-cont/dvi.html
        """
        infileno = self.infile.fileno()
        minfile = mmap.mmap(infileno, os.fstat(infileno)[6], prot=mmap.PROT_READ, flags=mmap.MAP_SHARED)
        pagecount = 0
        pos = -1
        eofchar = chr(0xdf)
        postchar = chr(0xf8)
        try :
            while minfile[pos] == eofchar :
                pos -= 1
            idbyte = minfile[pos]    
            if idbyte != minfile[1] :
                raise IndexError, "Invalid DVI file."
            pos = unpack(">I", minfile[pos - 4:pos])[0]
            if minfile[pos] != postchar :
                raise IndexError, "Invalid DVI file."
            pagecount = unpack(">H", minfile[pos + 27: pos + 29])[0]
        except IndexError : # EOF ?
            pass
        minfile.close() # reached EOF
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
