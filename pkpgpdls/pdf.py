# -*- coding: UTF-8 -*-
#
# pkpgcounter : a generic Page Description Language parser
#
# (c) 2003, 2004, 2005, 2006, 2007, 2008 Jerome Alet <alet@librelogiciel.com>
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

"""This modules implements a page counter for PDF documents.

   Some informations taken from PDF Reference v1.7 by Adobe.
"""

import re

import pdlparser

PDFWHITESPACE = chr(0) \
                + chr(9) \
                + chr(10) \
                + chr(12) \
                + chr(13) \
                + chr(32)
                 
PDFDELIMITERS = r"()<>[]{}/%"                 
PDFCOMMENT = r"%"        # Up to next EOL

PDFPAGEMARKER = "<< /Type /Page " # Where spaces are any whitespace char

PDFMEDIASIZE = "/MediaBox [xmin ymin xmax ymax]" # an example. MUST be present in Page objects
PDFOBJREGEX = r"\s+(\d+)\s+(\d+)\s+(obj\s*.+\s*endobj)" # Doesn't work as expected

class PDFObject :
    """A class for PDF objects."""
    def __init__(self, major, minor, description) :
        """Initialize the PDF object."""
        self.major = major
        self.minor = minor
        self.majori = int(major)
        self.minori = int(minor)
        self.description = description
        self.comments = []
        self.content = []
        self.parent = None
        self.kids = []
        
class Parser(pdlparser.PDLParser) :
    """A parser for PDF documents."""
    totiffcommands = [ 'gs -sDEVICE=tiff24nc -dPARANOIDSAFER -dNOPAUSE -dBATCH -dQUIET -r"%(dpi)i" -sOutputFile="%(outfname)s" "%(infname)s"' ]
    required = [ "gs" ]
    openmode = "rU"
    format = "PDF"
    def isValid(self) :    
        """Returns True if data is PDF, else False."""
        if self.firstblock.startswith("%PDF-") or \
           self.firstblock.startswith("\033%-12345X%PDF-") or \
           ((self.firstblock[:128].find("\033%-12345X") != -1) and (self.firstblock.upper().find("LANGUAGE=PDF") != -1)) or \
           (self.firstblock.find("%PDF-") != -1) :
            return True
        else :    
            return False
        
    def getJobSize(self) :    
        """Counts pages in a PDF document."""
        # First we start with a generic PDF parser.
        lastcomment = None
        objects = {}
        inobject = 0
        objre = re.compile(r"\s?(\d+)\s+(\d+)\s+obj[<\s/]?")
        for line in self.infile :
            line = line.strip()    
            if line.startswith("% ") :    
                if inobject :
                    obj.comments.append(line)
                else :
                    lastcomment = line[2:]
            else :
                # New object begins here
                result = objre.search(line)
                if result is not None :
                    (major, minor) = line[result.start():result.end()].split()[:2]
                    obj = PDFObject(major, minor, lastcomment)
                    obj.content.append(line[result.end():])
                    inobject = 1
                elif line.startswith("endobj") \
                  or line.startswith(">> endobj") \
                  or line.startswith(">>endobj") :
                    # Handle previous object, if any
                    if inobject :
                        # only overwrite older versions of this object
                        # same minor seems to be possible, so the latest one
                        # found in the file will be the one we keep.
                        # if we want the first one, just use > instead of >=
                        oldobject = objects.setdefault(major, obj)
                        if int(minor) >= oldobject.minori :
                            objects[major] = obj
                            # self.logdebug("Object(%i, %i) overwritten with Object(%i, %i)" % (oldobject.majori, oldobject.minori, obj.majori, obj.minori))
                        # self.logdebug("Object(%i, %i)" % (obj.majori, obj.minori))
                        inobject = 0        
                else :    
                    if inobject :
                        obj.content.append(line)
                        
        # Now we check each PDF object we've just created.
        newpageregexp = re.compile(r"(/Type)\s?(/Page)[/>\s]", re.I)
        pagecount = 0
        for obj in objects.values() :
            content = "".join(obj.content)
            count = len(newpageregexp.findall(content))
            if count and (content != r"<</Type /Page>>") : # Empty pages which are not rendered ?
                pagecount += count
        return pagecount    
        
    def veryFastAndNotAlwaysCorrectgetJobSize(self) :    
        """Counts pages in a PDF document."""
        newpageregexp = re.compile(r"/Type\s*/Page[/>\s]")
        return len(newpageregexp.findall(self.infile.read()))

    def thisOneIsSlowButCorrectgetJobSize(self) :
        """Counts pages in a PDF document."""
        oregexp = re.compile(r"\s+(\d+)\s+(\d+)\s+(obj\s*.+?\s*?endobj)", \
                             re.DOTALL)
        objtokeep = {}
        for (smajor, sminor, content) in oregexp.findall(self.infile.read()) :
            major = int(smajor)
            minor = int(sminor)
            (prevmin, prevcont) = objtokeep.get(major, (None, None))
            if (minor >= prevmin) : # Handles both None and real previous minor
                objtokeep[major] = (minor, content)
                #if prevmin is not None :
                #    self.logdebug("Object %i.%i overwritten with %i.%i" \
                #                     % (major, prevmin, \
                #                        major, minor))
                #else :
                #    self.logdebug("Object %i.%i OK" % (major, minor))
        npregexp = re.compile(r"/Type\s*/Page[/>\s]")
        pagecount = 0
        for (major, (minor, content)) in objtokeep.items() :
            count = len(npregexp.findall(content))
            if count :
                emptycount = content.count("obj\n<< \n/Type /Page \n>> \nendobj") + content.count("obj\n<< \n/Type /Page \n\n>> \nendobj") # TODO : make this clean
                if not emptycount :
                    self.logdebug("%i.%i : %s\n" % (major, minor, repr(content)))
                pagecount += count - emptycount
        return pagecount