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

"""This modules implements a page counter for SPL1 documents."""

import sys
import os
import mmap
from struct import unpack

import pdlparser
import pjl
import version

ESCAPECHARS = (chr(0x1b), chr(0x24))

class Parser(pdlparser.PDLParser) :
    """A parser for SPL1 documents."""
    def isValid(self) :    
        """Returns True if data is QPDL aka SPL2, else False."""
        if ((self.firstblock[:128].find("\033%-12345X") != -1) and \
            (self.firstblock.find("$PJL ") != -1) and \
             ((self.firstblock.find("LANGUAGE=SMART") != -1) or \
              (self.firstblock.find("LANGUAGE = SMART") != -1))) :
            self.logdebug("DEBUG: Input file is in the SPL1 (aka SPL12) format.")
            return True
        else :    
            return False
            
    def littleEndian(self) :
        """Toggles to little endianness."""
        self.unpackType = { 1 : "B", 2 : "<H", 4 : "<I" }
        self.unpackShort = self.unpackType[2]
        self.unpackLong = self.unpackType[4]
        return 0
        
    def bigEndian(self) :
        """Toggles to big endianness."""
        self.unpackType = { 1 : "B", 2 : ">H", 4 : ">I" }
        self.unpackShort = self.unpackType[2]
        self.unpackLong = self.unpackType[4]
        return 0
    
    def escape(self, nextpos) :    
        """Handles the ESC code."""
        self.isbitmap = False
        pos = endpos = nextpos
        minfile = self.minfile
        if minfile[pos : pos+8] == r"%-12345X" :
            endpos = pos + 9
        elif minfile[pos-1] in ESCAPECHARS :    
            endpos = pos
        else :    
            return 0
        endmark = (chr(0x1b), chr(0x00))
        asciilimit = chr(0x80)
        quotes = 0
        while (minfile[endpos] not in endmark) and \
               ((minfile[endpos] < asciilimit) or (quotes % 2)) :
            if minfile[endpos] == '"' :
                quotes += 1
            endpos += 1
            
        # Store this in a per page mapping.    
        # NB : First time will be at page 0 (i.e. **before** page 1) !
        stuff = self.escapedStuff.setdefault(self.pagecount, [])
        datas = minfile[pos-1 : endpos]
        stuff.append(datas)
        if datas.endswith("$PJL BITMAP START\r\n") :
            self.isbitmap = True
        self.logdebug("Escaped datas : [%s]" % repr(datas))
        return endpos - pos + 1
        
    def getJobSize(self) :
        """Counts pages in an SPL1 document.
        
           Algorithm by Jerome Alet.
        """
        infileno = self.infile.fileno()
        self.minfile = minfile = mmap.mmap(infileno, os.fstat(infileno)[6], prot=mmap.PROT_READ, flags=mmap.MAP_SHARED)
        self.pagecount = 0
        self.escapedStuff = {}   # For escaped datas, mostly PJL commands
        self.bigEndian()
        
        self.isbitmap = False
        pos = 0
        try :
            try :
                while 1 :
                    tag = minfile[pos]
                    if tag in ESCAPECHARS :
                        pos += self.escape(pos+1)
                    else :    
                        if not self.isbitmap :
                            raise pdlparser.PDLParserError, "Unfortunately SPL1 is incompletely recognized. Parsing aborted. Please report the problem to %s" % version.__authoremail__
                        offset = unpack(self.unpackLong, minfile[pos:pos+4])[0]
                        sequencenum = unpack(self.unpackShort, minfile[pos+4:pos+6])[0]
                        codesop = " ".join([ "%02x" % ord(v) for v in minfile[pos+6:pos+12]])
                        if codesop != "06 00 00 80 13 40" :
                            raise pdlparser.PDLParserError, "Unfortunately SPL1 is incompletely recognized. Parsing aborted. Please report the problem to %s" % version.__authoremail__
                        if not sequencenum :
                            self.pagecount += 1
                        pos += 4 + offset
            except IndexError : # EOF ?            
                pass
        finally :
            minfile.close()
        return self.pagecount
        
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
