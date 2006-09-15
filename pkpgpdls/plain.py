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

"""This modules implements a page counter for plain text documents."""

import sys
import os

import pdlparser
import version


class Parser(pdlparser.PDLParser) :
    """A parser for plain text documents."""
    enscript = 'enscript --quiet --portrait --no-header --columns 1 --output - | gs -sDEVICE=tiff24nc -dPARANOIDSAFER -dNOPAUSE -dBATCH -dQUIET -r%(dpi)i -sOutputFile="%(fname)s" -'
    a2ps = 'a2ps --borders 0 --quiet --portrait --no-header --columns 1 --output - | gs -sDEVICE=tiff24nc -dPARANOIDSAFER -dNOPAUSE -dBATCH -dQUIET -r%(dpi)i -sOutputFile="%(fname)s" -'
    def __init__(self, infile, debug=0, firstblock=None, lastblock=None) :
        """Initialize the plain text parser."""
        pdlparser.PDLParser.__init__(self, infile, debug, firstblock, lastblock)
        
        # Tries to detect is a plain text to PostScript command line tool is available
        # and use the first one we find.
        paths = os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin").split(os.pathsep)
        for cmd in ("enscript", "a2ps") :
            for path in paths :
                if os.path.exists(os.path.join(path, cmd)) :
                    self.totiffcommand = getattr(self, cmd)
                    return
        
    def isValid(self) :    
        """Returns True if data is plain text, else False.
        
           It's hard to detect a plain text file, so we just
           read the first line, and if it doesn't end in CR or LF
           we consider it's not plain text.
        """   
        line = self.infile.readline()
        self.infile.seek(0)
        if line.endswith("\n") or line.endswith("\r") :
            self.logdebug("DEBUG: Input file seems to be in the plain text format.")
            return True
        else :    
            return False
            
    def getJobSize(self) :
        """Counts pages in a plain text document."""
        pagesize = 66   # TODO : Does this vary wrt the default page size ?
                        # TODO : /etc/papersize and /etc/paper.config
        pagecount = 0
        linecount = 0
        for line in self.infile :
            if line.endswith("\n") or line.endswith("\r") :
                linecount += 1    
                if (linecount > pagesize) \
                   or (line.find("\f") != -1) :
                    pagecount += 1
                    linecount = 0
            else :        
                raise pdlparser.PDLParserError, "Unsupported file format. Please send the file to %s" % version.__authoremail__
        return pagecount + 1    # NB : empty files are catched in isValid()
        
if __name__ == "__main__" :    
    pdlparser.test(Parser)
