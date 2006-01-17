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
import zipfile

import pdlparser

class Parser(pdlparser.PDLParser) :
    """A parser for OpenOffice.org documents."""
    def isValid(self) :        
        """Returns 1 if data is DVI, else 0."""
        if self.firstblock[:2] == "PK" :
            try :
                self.archive = zipfile.ZipFile(self.infile)
                self.contentxml = self.archive.read("content.xml")
                self.metaxml = self.archive.read("meta.xml")
            except :    
                return 0
            else :
                self.logdebug("DEBUG: Input file is in the OpenOffice.org format.")
                return 1
        else :    
            return 0
            
    def getJobSize(self) :
        """Counts pages in an OpenOffice.org document.
        
           Algorithm by Jerome Alet.
        """
        pagecount = 0
        try :
            # First try with Text documents
            index = self.metaxml.index("meta:page-count=")
            pagecount = int(self.metaxml[index:].split('"')[1])
        except :
            # Now try with Impress documents
            pagecount = self.contentxml.count("<draw:page ")
            if not pagecount :
                # Probably a Spreadsheet document
                raise pdlparser.PDLParserError, "OpenOffice.org's spreadsheet documents are not yet supported."
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
