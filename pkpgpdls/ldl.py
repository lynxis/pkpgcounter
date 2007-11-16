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

"""This modules implements a page counter for HP LIDIL format."""

import sys
import os
import mmap
from struct import unpack

import pdlparser

class Parser(pdlparser.PDLParser) :
    """A parser for HP LIDIL documents."""
    def isValid(self) :    
        """Returns True if data is LIDIL, else False."""
	# Beginning Of File marker is a Sync packet, followed with
	# a Sync Complete packet followed with a Reset packet.
	# We just look at the start of the Sync packet for simplicity's sake.
	BOFMarker = "$\x01\x00\x00\x07"
	# End Of File marker is a Sync Complete packet followed
	# with a Reset packet. We ignore the preceding Sync packet
	# for simplicity's sake.
        EOFMarker = "$\x00\x10\x00\x08\x00\x00\x00\x00\x00\xff\xff\xff\xff\xff$$\x00\x10\x00\x06\x00\x00\x00\x00\x00\xff\xff\xff\xff\xff$" 
        if self.firstblock.startswith(BOFMarker) \
	   and self.lastblock.endswith(EOFMarker) :
            self.logdebug("DEBUG: Input file is in the Hewlett-Packard LIDIL format.")
            return True
        else :    
            return False
        
    def getJobSize(self) :
        """Computes the number of pages in a HP LIDIL document."""
        return 0

if __name__ == "__main__" :    
    pdlparser.test(Parser)
