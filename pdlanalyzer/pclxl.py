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
    """A parser for PCLXL (aka PCL6) documents."""
    mediasizes = { 
                    0 : "Letter",
                    1 : "Legal",
                    2 : "A4",
                    3 : "Executive",
                    4 : "Ledger",
                    5 : "A3",
                    6 : "COM10Envelope",
                    7 : "MonarchEnvelope",
                    8 : "C5Envelope",
                    9 : "DLEnvelope",
                    10 : "JB4",
                    11 : "JB5",
                    12 : "B5Envelope",
                    14 : "JPostcard",
                    15 : "JDoublePostcard",
                    16 : "A5",
                    17 : "A6",
                    18 : "JB6",
                 }   
                 
    mediasources = {             
                     0 : "Default",
                     1 : "Auto",
                     2 : "Manual",
                     3 : "MultiPurpose",
                     4 : "UpperCassette",
                     5 : "LowerCassette",
                     6 : "EnvelopeTray",
                     7 : "ThirdCassette",
                   }
                   
    orientations = {               
                     0 : "Portrait",
                     1 : "Landscape",
                     2 : "ReversePortrait",
                     3 : "ReverseLandscape",
                   }
            
    def isValid(self) :    
        """Returns 1 if data is PCLXL aka PCL6, else 0."""
        if ((self.firstblock[:128].find("\033%-12345X") != -1) and \
             (self.firstblock.find(" HP-PCL XL;") != -1) and \
             ((self.firstblock.find("LANGUAGE=PCLXL") != -1) or \
              (self.firstblock.find("LANGUAGE = PCLXL") != -1))) :
            if self.debug :  
                sys.stderr.write("DEBUG: Input file is in the PCLXL (aka PCL6) format.\n")
            return 1
        else :    
            return 0
            
    def beginPage(self) :
        """Indicates the beginning of a new page, and extracts media information."""
        self.pagecount += 1
        
        # Default values
        mediatypelabel = "Plain"
        mediasourcelabel = "Main"
        mediasizelabel = "Default"
        orientationlabel = "Portrait"
        
        # Now go upstream to decode media type, size, source, and orientation
        # this saves time because we don't need a complete parser !
        minfile = self.minfile
        pos = self.pos - 2
        while pos > 0 : # safety check : don't go back to far !
            val = ord(minfile[pos])
            if val in (0x44, 0x48, 0x41) : # if previous endPage or openDataSource or beginSession (first page)
                break
            if val == 0x26 :    
                mediasource = ord(minfile[pos - 2])
                mediasourcelabel = self.mediasources.get(mediasource, str(mediasource))
                pos = pos - 4
            elif val == 0x25 :
                mediasize = ord(minfile[pos - 2])
                mediasizelabel = self.mediasizes.get(mediasize, str(mediasize))
                pos = pos - 4
            elif val == 0x28 :    
                orientation = ord(minfile[pos - 2])
                orienationlabel = self.orientations.get(orientation, str(orientation))
                pos = pos - 4
            elif val == 0x27 :    
                savepos = pos
                pos = pos - 1
                while pos > 0 : # safety check : don't go back to far !
                    val = ord(minfile[pos])
                    pos -= 1    
                    if val == 0xc8 :
                        break
                mediatypelabel = minfile[pos:savepos] # TODO : INCORRECT, WE HAVE TO STRIP OUT THE UBYTE ARRAY'S LENGTH !!!
            # else : TODO : CUSTOM MEDIA SIZE AND UNIT ! 
            else :    
                pos = pos - 2   # ignored
        self.pages[self.pagecount] = { "copies" : 1, 
                                       "orientation" : orientationlabel, 
                                       "mediatype" : mediatypelabel, 
                                       "mediasize" : mediasizelabel,
                                       "mediasource" : mediasourcelabel,
                                     } 
        return 0
        
    def endPage(self) :    
        """Indicates the end of a page."""
        pos = self.pos
        pos3 = pos - 3
        minfile = self.minfile
        if minfile[pos3:pos-1] == self.setNumberOfCopies :
            # The EndPage operator may be preceded by a PageCopies attribute
            # So set number of copies for current page.
            # From what I read in PCLXL documentation, the number
            # of copies is an unsigned 16 bits integer
            self.pages[self.pagecount]["copies"] = unpack(self.endianness + "H", minfile[pos-5:pos3])[0]
        return 0
        
    def setColorSpace(self) :    
        """Changes the color space."""
        if self.minfile[self.pos-4:self.pos-1] == self.RGBColorSpace :
            self.iscolor = 1
        return 0
            
    def array_8(self) :    
        """Handles byte arrays."""
        pos = self.pos
        datatype = self.minfile[pos]
        pos += 1
        length = self.tags[ord(datatype)]
        if callable(length) :
            self.pos = pos
            length = length()
            pos = self.pos
        posl = pos + length
        self.pos = posl
        if length == 1 :    
            return unpack("B", self.minfile[pos:posl])[0]
        elif length == 2 :    
            return unpack(self.endianness + "H", self.minfile[pos:posl])[0]
        elif length == 4 :    
            return unpack(self.endianness + "I", self.minfile[pos:posl])[0]
        else :    
            raise pdlparser.PDLParserError, "Error on array size at %s" % self.pos
        
    def array_16(self) :    
        """Handles byte arrays."""
        pos = self.pos
        datatype = self.minfile[pos]
        pos += 1
        length = self.tags[ord(datatype)]
        if callable(length) :
            self.pos = pos
            length = length()
            pos = self.pos
        posl = pos + length
        self.pos = posl
        if length == 1 :    
            return 2 * unpack("B", self.minfile[pos:posl])[0]
        elif length == 2 :    
            return 2 * unpack(self.endianness + "H", self.minfile[pos:posl])[0]
        elif length == 4 :    
            return 2 * unpack(self.endianness + "I", self.minfile[pos:posl])[0]
        else :    
            raise pdlparser.PDLParserError, "Error on array size at %s" % self.pos
        
    def array_32(self) :    
        """Handles byte arrays."""
        pos = self.pos
        datatype = self.minfile[pos]
        pos += 1
        length = self.tags[ord(datatype)]
        if callable(length) :
            self.pos = pos
            length = length()
            pos = self.pos
        posl = pos + length
        self.pos = posl
        if length == 1 :    
            return 4 * unpack("B", self.minfile[pos:posl])[0]
        elif length == 2 :    
            return 4 * unpack(self.endianness + "H", self.minfile[pos:posl])[0]
        elif length == 4 :    
            return 4 * unpack(self.endianness + "I", self.minfile[pos:posl])[0]
        else :    
            raise pdlparser.PDLParserError, "Error on array size at %s" % self.pos
        
    def embeddedDataSmall(self) :
        """Handle small amounts of data."""
        pos = self.pos
        length = ord(self.minfile[pos])
        self.pos = pos + 1
        return length
        
    def embeddedData(self) :
        """Handle normal amounts of data."""
        pos = self.pos
        pos4 = pos + 4
        self.pos = pos4
        return unpack(self.endianness + "I", self.minfile[pos:pos4])[0]
        
    def littleEndian(self) :        
        """Toggles to little endianness."""
        self.endianness = "<" # little endian
        return 0
        
    def bigEndian(self) :    
        """Toggles to big endianness."""
        self.endianness = ">" # big endian
        return 0
    
    def getJobSize(self) :
        """Counts pages in a PCLXL (PCL6) document.
        
           Algorithm by Jerome Alet.
           
           The documentation used for this was :
         
           HP PCL XL Feature Reference
           Protocol Class 2.0
           http://www.hpdevelopersolutions.com/downloads/64/358/xl_ref20r22.pdf 
        """
        self.iscolor = None
        self.endianness = None
        found = 0
        while not found :
            line = self.infile.readline()
            if not line :
                break
            if line[1:12] == " HP-PCL XL;" :
                found = 1
                endian = ord(line[0])
                if endian == 0x29 :
                    self.littleEndian()
                elif endian == 0x28 :    
                    self.bigEndian()
                # elif endian == 0x27 : # TODO : This is the ESC code : parse it for PJL statements !
                # 
                else :    
                    raise pdlparser.PDLParserError, "Unknown endianness marker 0x%02x at start !" % endian
        if not found :
            raise pdlparser.PDLParserError, "This file doesn't seem to be PCLXL (aka PCL6)"
            
        # Initialize table of tags
        self.tags = [ 0 ] * 256    
        
        # GhostScript's sources tell us that HP printers
        # only accept little endianness, but we can handle both.
        self.tags[0x28] = self.bigEndian    # BigEndian
        self.tags[0x29] = self.littleEndian # LittleEndian
        
        self.tags[0x43] = self.beginPage    # BeginPage
        self.tags[0x44] = self.endPage      # EndPage
        
        self.tags[0x6a] = self.setColorSpace    # to detect color/b&w mode
        
        self.tags[0xc0] = 1 # ubyte
        self.tags[0xc1] = 2 # uint16
        self.tags[0xc2] = 4 # uint32
        self.tags[0xc3] = 2 # sint16
        self.tags[0xc4] = 4 # sint32
        self.tags[0xc5] = 4 # real32
        
        self.tags[0xc8] = self.array_8  # ubyte_array
        self.tags[0xc9] = self.array_16 # uint16_array
        self.tags[0xca] = self.array_32 # uint32_array
        self.tags[0xcb] = self.array_16 # sint16_array
        self.tags[0xcc] = self.array_32 # sint32_array
        self.tags[0xcd] = self.array_32 # real32_array
        
        self.tags[0xd0] = 2 # ubyte_xy
        self.tags[0xd1] = 4 # uint16_xy
        self.tags[0xd2] = 8 # uint32_xy
        self.tags[0xd3] = 4 # sint16_xy
        self.tags[0xd4] = 8 # sint32_xy
        self.tags[0xd5] = 8 # real32_xy
        
        self.tags[0xe0] = 4  # ubyte_box
        self.tags[0xe1] = 8  # uint16_box
        self.tags[0xe2] = 16 # uint32_box
        self.tags[0xe3] = 8  # sint16_box
        self.tags[0xe4] = 16 # sint32_box
        self.tags[0xe5] = 16 # real32_box
        
        self.tags[0xf8] = 1 # attr_ubyte
        self.tags[0xf9] = 2 # attr_uint16
        
        self.tags[0xfa] = self.embeddedData      # dataLength
        self.tags[0xfb] = self.embeddedDataSmall # dataLengthByte
            
        # color spaces    
        self.BWColorSpace = "".join([chr(0x00), chr(0xf8), chr(0x03)])
        self.GrayColorSpace = "".join([chr(0x01), chr(0xf8), chr(0x03)])
        self.RGBColorSpace = "".join([chr(0x02), chr(0xf8), chr(0x03)])
        
        # set number of copies
        self.setNumberOfCopies = "".join([chr(0xf8), chr(0x31)]) 
        
        infileno = self.infile.fileno()
        self.pages = {}
        self.minfile = minfile = mmap.mmap(infileno, os.fstat(infileno)[6], prot=mmap.PROT_READ, flags=mmap.MAP_SHARED)
        tags = self.tags
        self.pagecount = 0
        self.pos = pos = self.infile.tell()
        try :
            while 1 :
                char = minfile[pos]
                pos += 1
                length = tags[ord(char)]
                if not length :
                    continue
                if callable(length) :    
                    self.pos = pos
                    length = length()
                    pos = self.pos
                pos += length    
        except IndexError : # EOF ?
            self.minfile.close() # reached EOF
            
        # now handle number of copies for each page (may differ).
        if self.iscolor :
            colormode = "Color"
        else :    
            colormode = "Black"
        for pnum in range(1, self.pagecount + 1) :
            # if no number of copies defined, take 1, as explained
            # in PCLXL documentation.
            # NB : is number of copies is 0, the page won't be output
            # but the formula below is still correct : we want 
            # to decrease the total number of pages in this case.
            page = self.pages.get(pnum, 1)
            copies = page["copies"]
            self.pagecount += (copies - 1)
            if self.debug :
                sys.stderr.write("%s*%s*%s*%s*%s*%s\n" % (copies, 
                                                          page["mediatype"], 
                                                          page["mediasize"], 
                                                          page["orientation"], 
                                                          page["mediasource"], 
                                                          colormode))
            
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
