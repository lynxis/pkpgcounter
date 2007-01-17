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

"""This modules implements a page counter for ZjStream documents."""

import sys
import os
import mmap
from struct import unpack

import pdlparser

class Parser(pdlparser.PDLParser) :
    """A parser for ZjStream documents."""
    def isValid(self) :    
        """Returns True if data is ZjStream, else False."""
        if self.firstblock[:4] == "ZJZJ" :
            self.logdebug("DEBUG: Input file is in the Zenographics ZjStream (little endian) format.")
            self.littleEndian()
            return True
        elif self.firstblock[:4] == "JZJZ" :    
            self.logdebug("DEBUG: Input file is in the Zenographics ZjStream (big endian) format.")
            self.bigEndian()
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
        
    def getJobSize(self) :
        """Computes the number of pages in a ZjStream document."""
        infileno = self.infile.fileno()
        minfile = mmap.mmap(infileno, os.fstat(infileno)[6], prot=mmap.PROT_READ, flags=mmap.MAP_SHARED)
        pos = 4
        startpagecount = endpagecount = 0
        try :
            try :
                while 1 :
                    header = minfile[pos:pos+16]
                    if len(header) != 16 :
                        break
                    totalChunkSize = unpack(self.unpackLong, header[:4])[0]
                    chunkType = unpack(self.unpackLong, header[4:8])[0]
                    numberOfItems = unpack(self.unpackLong, header[8:12])[0]
                    reserved = unpack(self.unpackShort, header[12:14])[0]
                    signature = unpack(self.unpackShort, header[14:])[0]
                    pos += totalChunkSize
                    if chunkType == 0 :
                        self.logdebug("startDoc")
                    elif chunkType == 1 :    
                        self.logdebug("endDoc")
                    elif chunkType == 2 :    
                        self.logdebug("startPage")
                        startpagecount += 1
                    elif chunkType == 3 :
                        self.logdebug("endPage")
                        endpagecount += 1
                        
                    #self.logdebug("Chunk size : %s" % totalChunkSize)
                    #self.logdebug("Chunk type : 0x%08x" % chunkType)
                    #self.logdebug("# items : %s" % numberOfItems)
                    #self.logdebug("reserved : 0x%04x" % reserved)
                    #self.logdebug("signature : 0x%04x" % signature)
                    #self.logdebug("\n")
            except IndexError : # EOF ?
                pass 
        finally :        
            minfile.close()
            
        if startpagecount != endpagecount :    
            sys.stderr.write("ERROR: Incorrect ZjStream datas.\n")
        return max(startpagecount, endpagecount)
        
if __name__ == "__main__" :    
    pdlparser.test(Parser)
