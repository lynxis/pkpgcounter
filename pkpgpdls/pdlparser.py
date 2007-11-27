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

"""This module defines the base class for all Page Description Language parsers."""

import sys
import os
import popen2

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
    totiffcommands = None        # Default command to convert to TIFF
    openmode = "rb"              # Default file opening mode
    def __init__(self, parent) :
        """Initialize the generic parser."""
        self.parent = parent
        self.infile = None
        if not self.isValid() :
            raise PDLParserError, "Invalid file format !"
        try :
            import psyco 
        except ImportError :    
            pass # Psyco is not installed
        else :    
            # Psyco is installed, tell it to compile
            # the CPU intensive methods : PCL and PCLXL
            # parsing will greatly benefit from this.
            psyco.bind(self.getJobSize)
        self.infile = open(self.parent.filename, self.openmode)
        # self.logdebug("Opened %s in '%s' mode." % (self.parent.filename, self.openmode))
            
    def __del__(self) :
        """Ensures the input file gets closed."""
        if self.infile :
            self.infile.close()
            
    def logdebug(self, message) :       
        """Logs a debug message if needed."""
        if self.parent.options.debug :
            sys.stderr.write("%s\n" % message)
            
    def isValid(self) :    
        """Returns True if data is in the expected format, else False."""
        raise RuntimeError, "Not implemented !"
        
    def getJobSize(self) :    
        """Counts pages in a document."""
        raise RuntimeError, "Not implemented !"
        
    def convertToTiffMultiPage24NC(self, outfname, dpi) :
        """Converts the input file to TIFF format, X dpi, 24 bits per pixel, uncompressed.
           Writes TIFF datas to the file named by outfname.
        """   
        if self.totiffcommands :
            infname = self.parent.filename
            for totiffcommand in self.totiffcommands :
                error = False
                commandline = totiffcommand % locals()
                # self.logdebug("Executing '%s'" % commandline)
                status = os.system(commandline)
                if os.WIFEXITED(status) :
                    if os.WEXITSTATUS(status) :
                        error = True
                else :        
                    error = True
                if not os.path.exists(outfname) :
                    error = True
                elif not os.stat(outfname).st_size :
                    error = True
                else :        
                    break       # Conversion worked fine it seems.
                sys.stderr.write("Command failed : %s\n" % repr(commandline))
            if error :
                raise PDLParserError, "Problem during conversion to TIFF."
        else :        
            raise PDLParserError, "Impossible to compute ink coverage for this file format."
