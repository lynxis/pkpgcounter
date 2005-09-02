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

KILOBYTE = 1024    
MEGABYTE = 1024 * KILOBYTE    
FIRSTBLOCKSIZE = 16 * KILOBYTE
LASTBLOCKSIZE = int(KILOBYTE / 4)

class PDLParserError(Exception):
    """An exception for PDLParser related stuff."""
    def __init__(self, message = ""):
        self.message = message
        Exception.__init__(self, message)
    def __repr__(self):
        return self.message
    __str__ = __repr__
        
class PDLParser :
    """Generic PDL parser."""
    def __init__(self, infile, debug=0, firstblock=None, lastblock=None) :
        """Initialize the generic parser."""
        self.infile = infile
        self.debug = debug
        if firstblock is None :
            self.infile.seek(0)
            firstblock = self.infile.read(FIRSTBLOCKSIZE)
            try :
                self.infile.seek(-LASTBLOCKSIZE, 2)
                lastblock = self.infile.read(LASTBLOCKSIZE)
            except IOError :    
                lastblock = ""
            self.infile.seek(0)
        self.firstblock = firstblock
        self.lastblock = lastblock
        if not self.isValid() :
            raise PDLParserError, "Invalid file format !"
        try :
            import psyco 
        except ImportError :    
            sys.stderr.write("WARN: If you are running on a 32 Bits x86 platform, you should install the Python Psyco module if possible, this would greatly speedup parsing. NB : Psyco doesn't work on other platforms, so don't worry if you're in this case.\n")
            pass # Psyco is not installed
        else :    
            # Psyco is installed, tell it to compile
            # the CPU intensive methods : PCL and PCLXL
            # parsing will greatly benefit from this, 
            # for PostScript and PDF the difference is
            # barely noticeable since they are already
            # almost optimal, and much more speedy anyway.
            psyco.bind(self.getJobSize)
            
    def logdebug(self, message) :       
        """Logs a debug message if needed."""
        if self.debug :
            sys.stderr.write("%s\n" % message)
            
    def isValid(self) :    
        """Returns 1 if data is in the expected format, else 0."""
        raise RuntimeError, "Not implemented !"
        
    def getJobSize(self) :    
        """Counts pages in a document."""
        raise RuntimeError, "Not implemented !"
