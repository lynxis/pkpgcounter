#! /usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# pkpgcounter : a generic Page Description Language parser
#
# (c) 2003, 2004, 2005, 2006, 2007 Jerome Alet <alet@librelogiciel.com>
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

"""This modules implements a page counter for PNM (ascii) documents."""

import pdlparser
import version

class Parser(pdlparser.PDLParser) :
    """A parser for PNM (ascii) documents."""
    openmode = "rU"                 
    def isValid(self) :    
        """Returns True if data is plain text, else False.
        
           It's hard to detect a plain text file, so we just try to
           extract lines from the first block (sufficiently large).
           If it's impossible to find one we consider it's not plain text.
        """   
        if (self.firstblock[:2] in ("P1", "P2", "P3")) :
            self.logdebug("DEBUG: Input file seems to be in the PNM (ascii) format.")
            self.marker = self.firstblock[:2]
            return True
        else :    
            return False
            
    def getJobSize(self) :
        """Counts pages in a PNM (ascii) document."""
        pagecount = 0
        marker = self.marker
        for line in self.infile :
            pagecount += line.split().count(marker)
        return pagecount
