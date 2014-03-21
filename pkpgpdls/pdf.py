# -*- coding: utf-8 -*-
#
# pkpgcounter: a generic Page Description Language parser
#
# (c) 2003-2009 Jerome Alet <alet@librelogiciel.com>
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

from . import pdlparser

PDFWHITESPACE = chr(0) \
                + chr(9) \
                + chr(10) \
                + chr(12) \
                + chr(13) \
                + chr(32)
PDFDELIMITERS = r"()<>[]{}/%"
PDFMEDIASIZE = "/MediaBox [xmin ymin xmax ymax]" # an example. MUST be present in Page objects

class Parser(pdlparser.PDLParser):
    """A parser for PDF documents."""
    totiffcommands = [ 'gs -sDEVICE=tiff24nc -dPARANOIDSAFER -dNOPAUSE -dBATCH -dQUIET -r"%(dpi)i" -sOutputFile="%(outfname)s" "%(infname)s"' ]
    required = [ "gs" ]
    openmode = "rU"
    format = "PDF"
    def isValid(self):
        """Returns True if data is PDF, else False."""
        if self.firstblock.startswith(b"%PDF-") or \
           self.firstblock.startswith(b"\033%-12345X%PDF-") or \
           ((self.firstblock[:128].find(b"\033%-12345X") != -1) and (self.firstblock.upper().find(b"LANGUAGE=PDF") != -1)) or \
           (self.firstblock.find(b"%PDF-") != -1):
            return True
        else:
            return False

    def veryFastAndNotAlwaysCorrectgetJobSize(self):
        """Counts pages in a PDF document.

           This method works great in the general case,
           and is around 30 times faster than the active
           one.
           Unfortunately it doesn't take into account documents
           with redacted pages (only made with FrameMaker ?)
           where an existing PDF object is replaced with one
           with the same major number a higher minor number.
        """
        newpageregexp = re.compile(r"/Type\s*/Page[/>\s]")
        return len(newpageregexp.findall(self.infile.read()))

    def getJobSize(self):
        """Counts pages in a PDF document.

           A faster way seems to be possible by extracting the
           "/Type/Pages/Count xxxx" value where there's no /Parent
           (i.e. the root of the page tree)
           Unfortunately I can't make a regexp work for this currently.

           At least the actual method below is accurate, even if 25%
           slower than the old one. But we will be able to extract
           other informations as well when needed, like orientation
           and size.
        """
        # Regular expression to extract objects from a PDF document
        oregexp = re.compile(r"\s+(\d+)\s+(\d+)\s+(obj\s*.+?\s*?endobj)", \
                             re.DOTALL)

        # Regular expression indicating a new page
        npregexp = re.compile(r"/Type\s*/Page[/>\s]")

        # Regular expression indicating an empty page
        # (usually to delete an existing one with a lower minor number)
        epregexp = re.compile(r"obj\s*<<\s*/Type\s*/Page\s*>>\s*endobj")

        # First we build a mapping of objects to keep because
        # if two objects with the same major number are found,
        # we only keep the one with the higher minor number:
        # this is the way in PDF to replace existing objects.
        objtokeep = {}
        for (smajor, sminor, content) in oregexp.findall(self.infile.read()):
            major = int(smajor)
            minor = int(sminor)
            (prevmin, prevcont) = objtokeep.get(major, (None, None))
            if (minor >= prevmin): # Handles both None and real previous minor
                objtokeep[major] = (minor, content)
                #if prevmin is not None:
                #    self.logdebug("Object %i.%i overwritten with %i.%i" \
                #                     % (major, prevmin, \
                #                        major, minor))
                #else:
                #    self.logdebug("Object %i.%i OK" % (major, minor))

        # Now that we have deleted all unneeded objects, we
        # can count the ones which are new pages, minus the ones
        # which are empty and not displayed pages (in fact pages
        # used to redact existing content).
        pagecount = 0
        for (major, (minor, content)) in list(objtokeep.items()):
            count = len(npregexp.findall(content))
            if count:
                emptycount = len(epregexp.findall(content))
                #if not emptycount:
                #    self.logdebug("%i.%i: %s\n" % (major, minor, repr(content)))
                pagecount += count - emptycount
        return pagecount
