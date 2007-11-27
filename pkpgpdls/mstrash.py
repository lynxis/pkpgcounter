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

"""This module implements a page counter for Microsoft Word (r) (tm) (c) (etc...) documents"""

import os
import urllib2

import pdlparser
import version

class Parser(pdlparser.PDLParser) :
    """A parser for that MS crap thing."""
    totiffcommands = [ ]
    def isValid(self) :    
        """Returns True if data is MS crap, else False.
        
           Identifying datas taken from the file command's magic database.
           IMPORTANT : some magic values are not reused here because they
           IMPORTANT : seem to be specific to some particular i18n release.
        """   
        if self.parent.firstblock.startswith("PO^Q`") \
           or self.parent.firstblock.startswith("\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1") \
           or self.parent.firstblock.startswith("\xfe7\x00#") \
           or self.parent.firstblock.startswith("\xdb\xa5-\x00\x00\x00") \
           or self.parent.firstblock.startswith("\x31\xbe\x00\x00") \
           or self.parent.firstblock[2112:].startswith("MSWordDoc") :
            self.logdebug("DEBUG: Input file seems to be in a Microsoft shitty file format.")
            return True
        else :    
            return False
            
    def getJobSize(self) :
        """Counts pages in a Microsoft Word (r) (tm) (c) (etc...) document."""
        return 0
