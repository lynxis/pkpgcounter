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

from pdlanalyzer import pdlparser

class Parser(pdlparser.PDLParser) :
    """A parser for PCL3, PCL4, PCL5 documents."""
    mediasizes = {  # ESC&l####A
                    0 : "Default",
                    1 : "Executive",
                    2 : "Letter",
                    3 : "Legal",
                    6 : "Ledger", 
                    25 : "A5",
                    26 : "A4",
                    27 : "A3",
                    45 : "JB5",
                    46 : "JB4",
                    71 : "HagakiPostcard",
                    72 : "OufukuHagakiPostcard",
                    80 : "MonarchEnvelope",
                    81 : "COM10Envelope",
                    90 : "DLEnvelope",
                    91 : "C5Envelope",
                    100 : "B5Envelope",
                    101 : "Custom",
                 }   
                 
    mediasources = { # ESC&l####H
                     0 : "Default",
                     1 : "Main",
                     2 : "Manual",
                     3 : "ManualEnvelope",
                     4 : "Alternate",
                     5 : "OptionalLarge",
                     6 : "EnvelopeFeeder",
                     7 : "Auto",
                     8 : "Tray1",
                   }
                   
    orientations = { # ESC&l####O
                     0 : "Portrait",
                     1 : "Landscape",
                     2 : "ReversePortrait",
                     3 : "ReverseLandscape",
                   }
                   
    mediatypes = { # ESC&l####M
                     0 : "Plain",
                     1 : "Bond",
                     2 : "Special",
                     3 : "Glossy",
                     4 : "Transparent",
                   }
        
    def isValid(self) :    
        """Returns 1 if data is PCL, else 0."""
        if self.firstblock.startswith("\033E\033") or \
           (self.firstblock.startswith("\033*rbC") and (not self.lastblock[-3:] == "\f\033@")) or \
           self.firstblock.startswith("\033%8\033") or \
           (self.firstblock.find("\033%-12345X") != -1) :
            if self.debug :  
                sys.stderr.write("DEBUG: Input file is in the PCL3/4/5 format.\n")
            return 1
        else :    
            return 0
        
    def setPageDict(self, pages, number, attribute, value) :
        """Initializes a page dictionnary."""
        dict = pages.setdefault(number, { "copies" : 1, "mediasource" : "Main", "mediasize" : "Default", "mediatype" : "Plain", "orientation" : "Portrait"})
        dict[attribute] = value
        
    def getJobSize(self) :     
        """Count pages in a PCL5 document.
         
           Should also work for PCL3 and PCL4 documents.
           
           Algorithm from pclcount
           (c) 2003, by Eduardo Gielamo Oliveira & Rodolfo Broco Manin 
           published under the terms of the GNU General Public Licence v2.
          
           Backported from C to Python by Jerome Alet, then enhanced
           with more PCL tags detected. I think all the necessary PCL tags
           are recognized to correctly handle PCL5 files wrt their number
           of pages. The documentation used for this was :
         
           HP PCL/PJL Reference Set
           PCL5 Printer Language Technical Quick Reference Guide
           http://h20000.www2.hp.com/bc/docs/support/SupportManual/bpl13205/bpl13205.pdf 
        """
        infileno = self.infile.fileno()
        minfile = mmap.mmap(infileno, os.fstat(infileno)[6], prot=mmap.PROT_READ, flags=mmap.MAP_SHARED)
        tagsends = { "&n" : "W", 
                     "&b" : "W", 
                     "*i" : "W", 
                     "*l" : "W", 
                     "*m" : "W", 
                     "*v" : "W", 
                     "*c" : "W", 
                     "(f" : "W", 
                     "(s" : "W", 
                     ")s" : "W", 
                     "&p" : "X", 
                     # "&l" : "XHAOM",  # treated specially
                     "&a" : "G", # TODO : 0 means next side, 1 front side, 2 back side
                     "*g" : "W",
                     "*r" : "sbABC",
                     "*t" : "R",
                     # "*b" : "VW", # treated specially because it occurs very often
                   }  
        pagecount = resets = ejects = backsides = startgfx = endgfx = 0
        starb = ampl = ispcl3 = escstart = 0
        mediasourcecount = mediasizecount = orientationcount = mediatypecount = 0
        tag = None
        pages = {}
        pos = 0
        try :
            while 1 :
                char = minfile[pos] ; pos += 1
                if char == "\014" :    
                    pagecount += 1
                elif char == "\033" :    
                    starb = ampl = 0
                    #
                    #     <ESC>*b###y#m###v###w... -> PCL3 raster graphics
                    #     <ESC>*b###W -> Start of a raster data row/block
                    #     <ESC>*b###V -> Start of a raster data plane
                    #     <ESC>*c###W -> Start of a user defined pattern
                    #     <ESC>*i###W -> Start of a viewing illuminant block
                    #     <ESC>*l###W -> Start of a color lookup table
                    #     <ESC>*m###W -> Start of a download dither matrix block
                    #     <ESC>*v###W -> Start of a configure image data block
                    #     <ESC>*r1A -> Start Gfx 
                    #     <ESC>(s###W -> Start of a characters description block
                    #     <ESC>)s###W -> Start of a fonts description block
                    #     <ESC>(f###W -> Start of a symbol set block
                    #     <ESC>&b###W -> Start of configuration data block
                    #     <ESC>&l###X -> Number of copies for current page
                    #     <ESC>&n###W -> Starts an alphanumeric string ID block
                    #     <ESC>&p###X -> Start of a non printable characters block
                    #     <ESC>&a2G -> Back side when duplex mode as generated by rastertohp
                    #     <ESC>*g###W -> Needed for planes in PCL3 output
                    #     <ESC>&l###H (or only 0 ?) -> Eject if NumPlanes > 1, as generated by rastertohp. Also defines mediasource
                    #     <ESC>&l###A -> mediasize
                    #     <ESC>&l###O -> orientation
                    #     <ESC>&l###M -> mediatype
                    #     <ESC>*t###R -> gfx resolution
                    #
                    tagstart = minfile[pos] ; pos += 1
                    if tagstart in "E9=YZ" : # one byte PCL tag
                        if tagstart == "E" :
                            resets += 1
                        continue             # skip to next tag
                    tag = tagstart + minfile[pos] ; pos += 1
                    if tag == "*b" : 
                        starb = 1
                        tagend = "VW"
                    elif tag == "&l" :    
                        ampl = 1
                        tagend = "XHAOM"
                    else :    
                        try :
                            tagend = tagsends[tag]
                        except KeyError :    
                            continue # Unsupported PCL tag
                    # Now read the numeric argument
                    size = 0
                    while 1 :
                        char = minfile[pos] ; pos += 1
                        if not char.isdigit() :
                            break
                        size = (size * 10) + int(char)    
                    if char in tagend :    
                        if tag == "&l" :
                            if char == "X" : 
                                self.setPageDict(pages, pagecount, "copies", size)
                            elif char == "H" :
                                self.setPageDict(pages, pagecount, "mediasource", self.mediasources.get(size, str(size)))
                                mediasourcecount += 1
                                ejects += 1 
                            elif char == "A" :
                                self.setPageDict(pages, pagecount, "mediasize", self.mediasizes.get(size, str(size)))
                                mediasizecount += 1
                            elif char == "O" :
                                self.setPageDict(pages, pagecount, "orientation", self.orientations.get(size, str(size)))
                                orientationcount += 1
                            elif char == "M" :
                                self.setPageDict(pages, pagecount, "mediatype", self.mediatypes.get(size, str(size)))
                                mediatypecount += 1
                        elif tag == "*r" :
                            # Special tests for PCL3
                            if (char == "s") and size :
                                while 1 :
                                    char = minfile[pos] ; pos += 1
                                    if char == "A" :
                                        break
                            elif (char == "b") and (minfile[pos] == "C") and not size :
                                ispcl3 = 1 # Certainely a PCL3 file
                            startgfx += (char == "A") and (minfile[pos - 2] in ("0", "1", "2", "3")) # Start Gfx
                            endgfx += (not size) and (char in ("C", "B")) # End Gfx
                        elif tag == "*t" :    
                            escstart += 1
                        elif (tag == "&a") and (size == 2) :
                            backsides += 1      # Back side in duplex mode
                        else :    
                            # we just ignore the block.
                            if tag == "&n" : 
                                # we have to take care of the operation id byte
                                # which is before the string itself
                                size += 1
                            pos += size    
                else :                            
                    if starb :
                        # special handling of PCL3 in which 
                        # *b introduces combined ESCape sequences
                        size = 0
                        while 1 :
                            char = minfile[pos] ; pos += 1
                            if not char.isdigit() :
                                break
                            size = (size * 10) + int(char)    
                        if char in ("w", "v") :    
                            ispcl3 = 1  # certainely a PCL3 document
                            pos += size - 1
                        elif char in ("y", "m") :    
                            ispcl3 = 1  # certainely a PCL3 document
                            pos -= 1    # fix position : we were ahead
                    elif ampl :        
                        # special handling of PCL3 in which 
                        # &l introduces combined ESCape sequences
                        size = 0
                        while 1 :
                            char = minfile[pos] ; pos += 1
                            if not char.isdigit() :
                                break
                            size = (size * 10) + int(char)    
                        if char in ("a", "o", "h", "m") :    
                            ispcl3 = 1  # certainely a PCL3 document
                            pos -= 1    # fix position : we were ahead
                            if char == "h" :
                                self.setPageDict(pages, pagecount, "mediasource", self.mediasources.get(size, str(size)))
                                mediasourcecount += 1
                            elif char == "a" :
                                self.setPageDict(pages, pagecount, "mediasize", self.mediasizes.get(size, str(size)))
                                mediasizecount += 1
                            elif char == "o" :
                                self.setPageDict(pages, pagecount, "orientation", self.orientations.get(size, str(size)))
                                orientationcount += 1
                            elif char == "m" :
                                self.setPageDict(pages, pagecount, "mediatype", self.mediatypes.get(size, str(size)))
                                mediatypecount += 1
        except IndexError : # EOF ?
            minfile.close() # reached EOF
                            
        # if pagecount is still 0, we will use the number
        # of resets instead of the number of form feed characters.
        # but the number of resets is always at least 2 with a valid
        # pcl file : one at the very start and one at the very end
        # of the job's data. So we substract 2 from the number of
        # resets. And since on our test data we needed to substract
        # 1 more, we finally substract 3, and will test several
        # PCL files with this. If resets < 2, then the file is
        # probably not a valid PCL file, so we use 0
        
        if self.debug :
            sys.stderr.write("pagecount : %s\n" % pagecount)
            sys.stderr.write("resets : %s\n" % resets)
            sys.stderr.write("ejects : %s\n" % ejects)
            sys.stderr.write("backsides : %s\n" % backsides)
            sys.stderr.write("startgfx : %s\n" % startgfx)
            sys.stderr.write("endgfx : %s\n" % endgfx)
            sys.stderr.write("mediasourcecount : %s\n" % mediasourcecount)
            sys.stderr.write("mediasizecount : %s\n" % mediasizecount)
            sys.stderr.write("orientationcount : %s\n" % orientationcount)
            sys.stderr.write("mediatypecount : %s\n" % mediatypecount)
            sys.stderr.write("escstart : %s\n" % escstart)
        
#        if not pagecount :
#            pagecount = (pagecount or ((resets - 3) * (resets > 2)))
#        else :    
#            # here we add counters for other ways new pages may have
#            # been printed and ejected by the printer
#            pagecount += ejects + backsides
#        
#        # now handle number of copies for each page (may differ).
#        # in duplex mode, number of copies may be sent only once.
#        for pnum in range(pagecount) :
#            # if no number of copies defined, take the preceding one else the one set before any page else 1.
#            page = pages.get(pnum, pages.get(pnum - 1, pages.get(0, { "copies" : 1 })))
#            pagecount += (page["copies"] - 1)
#            
#        # in PCL3 files, there's one Start Gfx tag per page
#        if ispcl3 :
#            if endgfx == int(startgfx / 2) : # special case for cdj1600
#                pagecount = endgfx 
#            elif startgfx :
#                pagecount = startgfx
#            elif endgfx :    
#                pagecount = endgfx
                
            
        if pagecount == mediasourcecount == escstart : 
            pass        # should be OK.
        elif (not startgfx) and (not endgfx) :
            pagecount = ejects or pagecount
        elif startgfx == endgfx :    
            pagecount = startgfx
        elif startgfx == (endgfx - 1) :    
            pagecount = startgfx
        elif (startgfx == 1) and not endgfx :    
            pass
        else :    
            pagecount = abs(startgfx - endgfx)
            
        if self.debug :        
            for pnum in range(pagecount) :
                # if no number of copies defined, take the preceding one else the one set before any page else 1.
                page = pages.get(pnum, pages.get(pnum - 1, pages.get(0, { "copies" : 1, "mediasource" : "Main", "mediasize" : "Default", "mediatype" : "Plain", "orientation" : "Portrait"})))
                sys.stderr.write("%s*%s*%s*%s*%s\n" % (page["copies"], page["mediatype"], page["mediasize"], page["orientation"], page["mediasource"]))
                
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
