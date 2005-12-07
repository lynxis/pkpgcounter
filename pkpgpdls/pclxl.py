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

import pdlparser
import pjl

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
                    12 : "B5",
                    14 : "JPostcard",
                    15 : "JDoublePostcard",
                    16 : "A5",
                    17 : "A6",
                    18 : "JB6",
                    19 : "JIS8K",
                    20 : "JIS16K",
                    21 : "JISExec",
                    96 : "Default",
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
                     4 : "Default",
                   }
            
    def isValid(self) :    
        """Returns 1 if data is PCLXL aka PCL6, else 0."""
        if ((self.firstblock[:128].find("\033%-12345X") != -1) and \
             (self.firstblock.find(" HP-PCL XL;") != -1) and \
             ((self.firstblock.find("LANGUAGE=PCLXL") != -1) or \
              (self.firstblock.find("LANGUAGE = PCLXL") != -1))) :
            self.logdebug("DEBUG: Input file is in the PCLXL (aka PCL6) format.")
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
                orientationlabel = self.orientations.get(orientation, str(orientation))
                pos = pos - 4
            elif val == 0x27 :    
                savepos = pos
                pos = pos - 1
                startpos = size = None 
                while pos > 0 : # safety check : don't go back to far !
                    val = ord(minfile[pos])
                    pos -= 1    
                    if val == 0xc8 :
                        length = self.tags[ord(minfile[pos+2])] # will probably always be a byte or uint16
                        if length == 1 :    
                            startpos = pos + 4
                            size = unpack("B", self.minfile[pos+3:startpos])[0]
                        elif length == 2 :    
                            startpos = pos + 5
                            size = unpack(self.endianness + "H", self.minfile[pos+3:startpos])[0]
                        elif length == 4 :    
                            startpos = pos + 7
                            size = unpack(self.endianness + "I", self.minfile[pos+3:startpos])[0]
                        else :    
                            raise pdlparser.PDLParserError, "Error on size at %s" % pos+2
                        break
                mediatypelabel = minfile[startpos:startpos+size]
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
            try :
                self.pages[self.pagecount]["copies"] = unpack(self.endianness + "H", minfile[pos-5:pos3])[0]
            except KeyError :    
                self.logdebug("It looks like this PCLXL file is corrupted.")
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
    
    def reservedForFutureUse(self) :
        """Outputs something when a reserved byte is encountered."""
        self.logdebug("Byte at %s is out of the PCLXL Protocol Class 2.0 Specification" % self.pos)
        return 0    
        
    def escape(self) :    
        """Handles the ESC code."""
        pos = endpos = self.pos
        if self.minfile[pos : pos+8] == r"%-12345X" :
            endpos = pos + 9
            endmark = chr(0x0c) + chr(0x00) + chr(0x1b)
            asciilimit = chr(0x80)
            quotes = 0
            while (self.minfile[endpos] not in endmark) and \
                   ((self.minfile[endpos] < asciilimit) or (quotes % 2)) :
                if self.minfile[endpos] == '"' :
                    quotes += 1
                endpos += 1
                
            # Store this in a per page mapping.    
            # NB : First time will be at page 0 (i.e. **before** page 1) !
            stuff = self.escapedStuff.setdefault(self.pagecount, [])
            stuff.append(self.minfile[pos : endpos])
            self.logdebug("Escaped datas : [%s]" % repr(self.minfile[pos : endpos]))
        return endpos - pos
        
    def getJobSize(self) :
        """Counts pages in a PCLXL (PCL6) document.
        
           Algorithm by Jerome Alet.
           
           The documentation used for this was :
         
           HP PCL XL Feature Reference
           Protocol Class 2.0
           http://www.hpdevelopersolutions.com/downloads/64/358/xl_ref20r22.pdf 
           
           Protocol Class 2.1 Supplement
           xl_ref21.pdf
           
           Protocol Class 3.0 Supplement
           xl_refsup30r089.pdf
        """
        self.iscolor = None
        self.endianness = None
        found = 0
        while not found :
            line = self.infile.readline()
            if not line :
                break
            pos = line.find(" HP-PCL XL;")    
            if pos != -1 :
                found = 1
                endian = ord(line[pos - 1])
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
            
        # Initialize Media Sources
        for i in range(8, 256) :
            self.mediasources[i] = "ExternalTray%03i" % (i - 7)
            
        # Initialize table of tags
        self.tags = [ 0 ] * 256    
        
        self.tags[0x1b] = self.escape # The escape code
        
        # GhostScript's sources tell us that HP printers
        # only accept little endianness, but we can handle both.
        self.tags[0x28] = self.bigEndian    # BigEndian
        self.tags[0x29] = self.littleEndian # LittleEndian
        
        self.tags[0x43] = self.beginPage    # BeginPage
        self.tags[0x44] = self.endPage      # EndPage
        self.tags[0x45] = self.reservedForFutureUse # reserved
        self.tags[0x46] = self.reservedForFutureUse # reserved
        
        self.tags[0x4a] = self.reservedForFutureUse # reserved
        self.tags[0x4b] = self.reservedForFutureUse # reserved
        self.tags[0x4c] = self.reservedForFutureUse # reserved
        self.tags[0x4d] = self.reservedForFutureUse # reserved
        self.tags[0x4e] = self.reservedForFutureUse # reserved
        
        self.tags[0x56] = self.reservedForFutureUse # TODO : documentation not clear about reserved status
        
        self.tags[0x57] = self.reservedForFutureUse # reserved
        self.tags[0x58] = self.reservedForFutureUse # reserved
        self.tags[0x59] = self.reservedForFutureUse # reserved
        self.tags[0x5a] = self.reservedForFutureUse # reserved
        
        self.tags[0x6a] = self.setColorSpace    # to detect color/b&w mode
        
        self.tags[0x83] = self.reservedForFutureUse # reserved
        
        self.tags[0x87] = self.reservedForFutureUse # reserved
        self.tags[0x88] = self.reservedForFutureUse # reserved
        self.tags[0x89] = self.reservedForFutureUse # reserved
        self.tags[0x8a] = self.reservedForFutureUse # reserved
        self.tags[0x8b] = self.reservedForFutureUse # reserved
        self.tags[0x8c] = self.reservedForFutureUse # reserved
        self.tags[0x8d] = self.reservedForFutureUse # reserved
        self.tags[0x8e] = self.reservedForFutureUse # reserved
        self.tags[0x8f] = self.reservedForFutureUse # reserved
        self.tags[0x90] = self.reservedForFutureUse # reserved
        
        self.tags[0x92] = self.reservedForFutureUse # reserved
        
        self.tags[0x94] = self.reservedForFutureUse # reserved
        
        self.tags[0x9a] = self.reservedForFutureUse # reserved
        self.tags[0x9c] = self.reservedForFutureUse # reserved
        
        self.tags[0xa4] = self.reservedForFutureUse # reserved
        self.tags[0xa5] = self.reservedForFutureUse # reserved
        self.tags[0xa6] = self.reservedForFutureUse # reserved
        self.tags[0xa7] = self.reservedForFutureUse # reserved
        
        self.tags[0xaa] = self.reservedForFutureUse # reserved
        self.tags[0xab] = self.reservedForFutureUse # reserved
        self.tags[0xac] = self.reservedForFutureUse # reserved
        self.tags[0xad] = self.reservedForFutureUse # reserved
        self.tags[0xae] = self.reservedForFutureUse # reserved
        self.tags[0xaf] = self.reservedForFutureUse # reserved
        
        self.tags[0xb7] = self.reservedForFutureUse # reserved
        
        self.tags[0xba] = self.reservedForFutureUse # reserved
        self.tags[0xbb] = self.reservedForFutureUse # reserved
        self.tags[0xbc] = self.reservedForFutureUse # reserved
        self.tags[0xbd] = self.reservedForFutureUse # reserved
        self.tags[0xbe] = self.reservedForFutureUse # reserved
        
        self.tags[0xc0] = 1 # ubyte
        self.tags[0xc1] = 2 # uint16
        self.tags[0xc2] = 4 # uint32
        self.tags[0xc3] = 2 # sint16
        self.tags[0xc4] = 4 # sint32
        self.tags[0xc5] = 4 # real32
        
        self.tags[0xc6] = self.reservedForFutureUse # reserved
        self.tags[0xc7] = self.reservedForFutureUse # reserved
        
        self.tags[0xc8] = self.array_8  # ubyte_array
        self.tags[0xc9] = self.array_16 # uint16_array
        self.tags[0xca] = self.array_32 # uint32_array
        self.tags[0xcb] = self.array_16 # sint16_array
        self.tags[0xcc] = self.array_32 # sint32_array
        self.tags[0xcd] = self.array_32 # real32_array
        
        self.tags[0xce] = self.reservedForFutureUse # reserved
        self.tags[0xcf] = self.reservedForFutureUse # reserved
        
        self.tags[0xd0] = 2 # ubyte_xy
        self.tags[0xd1] = 4 # uint16_xy
        self.tags[0xd2] = 8 # uint32_xy
        self.tags[0xd3] = 4 # sint16_xy
        self.tags[0xd4] = 8 # sint32_xy
        self.tags[0xd5] = 8 # real32_xy
        self.tags[0xd6] = self.reservedForFutureUse # reserved
        self.tags[0xd7] = self.reservedForFutureUse # reserved
        self.tags[0xd8] = self.reservedForFutureUse # reserved
        self.tags[0xd9] = self.reservedForFutureUse # reserved
        self.tags[0xda] = self.reservedForFutureUse # reserved
        self.tags[0xdb] = self.reservedForFutureUse # reserved
        self.tags[0xdc] = self.reservedForFutureUse # reserved
        self.tags[0xdd] = self.reservedForFutureUse # reserved
        self.tags[0xde] = self.reservedForFutureUse # reserved
        self.tags[0xdf] = self.reservedForFutureUse # reserved
        
        self.tags[0xe0] = 4  # ubyte_box
        self.tags[0xe1] = 8  # uint16_box
        self.tags[0xe2] = 16 # uint32_box
        self.tags[0xe3] = 8  # sint16_box
        self.tags[0xe4] = 16 # sint32_box
        self.tags[0xe5] = 16 # real32_box
        self.tags[0xe6] = self.reservedForFutureUse # reserved
        self.tags[0xe7] = self.reservedForFutureUse # reserved
        self.tags[0xe8] = self.reservedForFutureUse # reserved
        self.tags[0xe9] = self.reservedForFutureUse # reserved
        self.tags[0xea] = self.reservedForFutureUse # reserved
        self.tags[0xeb] = self.reservedForFutureUse # reserved
        self.tags[0xec] = self.reservedForFutureUse # reserved
        self.tags[0xed] = self.reservedForFutureUse # reserved
        self.tags[0xee] = self.reservedForFutureUse # reserved
        self.tags[0xef] = self.reservedForFutureUse # reserved
        
        self.tags[0xf0] = self.reservedForFutureUse # reserved
        self.tags[0xf1] = self.reservedForFutureUse # reserved
        self.tags[0xf2] = self.reservedForFutureUse # reserved
        self.tags[0xf3] = self.reservedForFutureUse # reserved
        self.tags[0xf4] = self.reservedForFutureUse # reserved
        self.tags[0xf5] = self.reservedForFutureUse # reserved
        self.tags[0xf6] = self.reservedForFutureUse # reserved
        self.tags[0xf7] = self.reservedForFutureUse # reserved
        
        self.tags[0xf8] = 1 # attr_ubyte
        self.tags[0xf9] = 2 # attr_uint16
        
        self.tags[0xfa] = self.embeddedData      # dataLength
        self.tags[0xfb] = self.embeddedDataSmall # dataLengthByte
        
        self.tags[0xfc] = self.reservedForFutureUse # reserved
        self.tags[0xfd] = self.reservedForFutureUse # reserved
        self.tags[0xfe] = self.reservedForFutureUse # reserved
        self.tags[0xff] = self.reservedForFutureUse # reserved
            
        # color spaces    
        self.BWColorSpace = "".join([chr(0x00), chr(0xf8), chr(0x03)])
        self.GrayColorSpace = "".join([chr(0x01), chr(0xf8), chr(0x03)])
        self.RGBColorSpace = "".join([chr(0x02), chr(0xf8), chr(0x03)])
        
        # set number of copies
        self.setNumberOfCopies = "".join([chr(0xf8), chr(0x31)]) 
        
        infileno = self.infile.fileno()
        self.pages = { 0 : { "copies" : 1, 
                             "orientation" : "Default", 
                             "mediatype" : "Plain", 
                             "mediasize" : "Default", 
                             "mediasource" : "Default", 
                           } 
                     }      
        self.minfile = minfile = mmap.mmap(infileno, os.fstat(infileno)[6], prot=mmap.PROT_READ, flags=mmap.MAP_SHARED)
        tags = self.tags
        self.pagecount = 0
        self.escapedStuff = {}
        self.pos = pos = 0
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
            colormode = "BW"
            
        defaultduplexmode = "Simplex"
        defaultpapersize = ""
        defaultpjlcopies = 1    
        oldpjlcopies = -1
        oldduplexmode = ""
        oldpapersize = ""
        for pnum in range(1, self.pagecount + 1) :
            # if no number of copies defined, take 1, as explained
            # in PCLXL documentation.
            # NB : is number of copies is 0, the page won't be output
            # but the formula below is still correct : we want 
            # to decrease the total number of pages in this case.
            page = self.pages.get(pnum, self.pages.get(1, { "copies" : 1, "mediasize" : "Default" }))
            pjlstuff = self.escapedStuff.get(pnum, self.escapedStuff.get(0, []))
            if pjlstuff :
                pjlparser = pjl.PJLParser("".join(pjlstuff))
                nbdefaultcopies = int(pjlparser.default_variables.get("COPIES", -1))
                nbcopies = int(pjlparser.environment_variables.get("COPIES", -1))
                nbdefaultqty = int(pjlparser.default_variables.get("QTY", -1))
                nbqty = int(pjlparser.environment_variables.get("QTY", -1))
                if nbdefaultcopies > -1 :
                    defaultpjlcopies = nbdefaultcopies
                if nbdefaultqty > -1 :
                    defaultpjlcopies = nbdefaultqty
                if nbcopies > -1 :
                    pjlcopies = nbcopies
                elif nbqty > -1 :
                    pjlcopies = nbqty
                else :
                    if oldpjlcopies == -1 :    
                        pjlcopies = defaultpjlcopies
                    else :    
                        pjlcopies = oldpjlcopies    
                defaultdm = pjlparser.default_variables.get("DUPLEX", "")
                if defaultdm :
                    if defaultdm.upper() == "ON" :
                        defaultduplexmode = "Duplex"
                    else :    
                        defaultduplexmode = "Simplex"
                envdm = pjlparser.environment_variables.get("DUPLEX", "")
                if envdm :
                    if envdm.upper() == "ON" :
                        duplexmode = "Duplex"
                    else :    
                        duplexmode = "Simplex"
                else :        
                    if not oldduplexmode :
                        duplexmode = defaultduplexmode
                    else :    
                        duplexmode = oldduplexmode
                defaultps = pjlparser.default_variables.get("PAPER", "")
                if defaultps :
                    defaultpapersize = defaultps
                envps = pjlparser.environment_variables.get("PAPER", "")
                if envps :
                    papersize = envps
                else :    
                    if not oldpapersize :
                        papersize = defaultpapersize
                    else :    
                        papersize = oldpapersize
            else :        
                if oldpjlcopies == -1 :
                    pjlcopies = defaultpjlcopies
                else :    
                    pjlcopies = oldpjlcopies
                if not oldduplexmode :
                    duplexmode = defaultduplexmode
                else :    
                    duplexmode = oldduplexmode
                if not oldpapersize :    
                    papersize = defaultpapersize
                else :    
                    papersize = oldpapersize
                duplexmode = oldduplexmode
                papersize = oldpapersize or page["mediasize"]
            if page["mediasize"] != "Default" :
                papersize = page["mediasize"]
            if not duplexmode :    
                duplexmode = oldduplexmode or defaultduplexmode
            oldpjlcopies = pjlcopies    
            oldduplexmode = duplexmode
            oldpapersize = papersize
            copies = pjlcopies * page["copies"]
            self.pagecount += (copies - 1)
            self.logdebug("%s*%s*%s*%s*%s*%s*%s" % (copies, 
                                                 page["mediatype"], 
                                                 papersize, 
                                                 page["orientation"], 
                                                 page["mediasource"], 
                                                 duplexmode, 
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
