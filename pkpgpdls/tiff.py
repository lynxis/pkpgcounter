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
import os
import mmap
from struct import unpack

from pdlanalyzer import pdlparser

class Parser(pdlparser.PDLParser) :
    """A parser for TIFF documents."""
    def isValid(self) :        
        """Returns 1 if data is TIFF, else 0."""
        littleendian = (chr(0x49)*2) + chr(0x2a) + chr(0)
        bigendian = (chr(0x4d)*2) + chr(0) + chr(0x2a)
        if self.firstblock[:4] in (littleendian, bigendian) :
            if self.debug :  
                sys.stderr.write("DEBUG: Input file is in the TIFF format.\n")
            return 1
        else :    
            return 0
    
    def getJobSize(self) :
        """Counts pages in a TIFF document.
        
           Algorithm by Jerome Alet.
           
           The documentation used for this was :
           
           http://www.ee.cooper.edu/courses/course_pages/past_courses/EE458/TIFF/
        """
        infileno = self.infile.fileno()
        minfile = mmap.mmap(infileno, os.fstat(infileno)[6], prot=mmap.PROT_READ, flags=mmap.MAP_SHARED)
        pagecount = 0
        littleendian = (chr(0x49)*2) + chr(0x2a) + chr(0)
        bigendian = (chr(0x4d)*2) + chr(0) + chr(0x2a)
        if minfile[:4] == littleendian :
            integerbyteorder = "<I"
            shortbyteorder = "<H"
        else :    
            integerbyteorder = ">I"
            shortbyteorder = ">H"
        pos = 4    
        try :    
            nextifdoffset = unpack(integerbyteorder, minfile[pos : pos + 4])[0]
            while nextifdoffset :
                direntrycount = unpack(shortbyteorder, minfile[nextifdoffset : nextifdoffset + 2])[0]
                pos = nextifdoffset + 2 + (direntrycount * 12)
                nextifdoffset = unpack(integerbyteorder, minfile[pos : pos + 4])[0]
                pagecount += 1
        except IndexError :            
            pass
        minfile.close()
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
