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
import tempfile
import optparse

import version, pdlparser, postscript, pdf, pcl345, pclxl, \
       escp2, dvi, tiff, ooo, zjstream

class PDLAnalyzer :    
    """Class for PDL autodetection."""
    def __init__(self, filename, debug=0) :
        """Initializes the PDL analyzer.
        
           filename is the name of the file or '-' for stdin.
           filename can also be a file-like object which 
           supports read() and seek().
        """
        self.debug = debug
        self.filename = filename
        
    def getJobSize(self) :    
        """Returns the job's size."""
        self.openFile()
        try :
            pdlhandler = self.detectPDLHandler()
        except pdlparser.PDLParserError, msg :    
            self.closeFile()
            raise pdlparser.PDLParserError, "Unknown file format for %s (%s)" % (self.filename, msg)
        else :
            try :
                size = pdlhandler.getJobSize()
            finally :    
                self.closeFile()
            return size
        
    def openFile(self) :    
        """Opens the job's data stream for reading."""
        self.mustclose = 0  # by default we don't want to close the file when finished
        if hasattr(self.filename, "read") and hasattr(self.filename, "seek") :
            # filename is in fact a file-like object 
            infile = self.filename
        elif self.filename == "-" :
            # we must read from stdin
            infile = sys.stdin
        else :    
            # normal file
            self.infile = open(self.filename, "rb")
            self.mustclose = 1
            return
            
        # Use a temporary file, always seekable contrary to standard input.
        self.infile = tempfile.TemporaryFile(mode="w+b")
        while 1 :
            data = infile.read(pdlparser.MEGABYTE) 
            if not data :
                break
            self.infile.write(data)
        self.infile.flush()    
        self.infile.seek(0)
            
    def closeFile(self) :        
        """Closes the job's data stream if we can close it."""
        if self.mustclose :
            self.infile.close()    
        else :    
            # if we don't have to close the file, then
            # ensure the file pointer is reset to the 
            # start of the file in case the process wants
            # to read the file again.
            try :
                self.infile.seek(0)
            except :    
                pass    # probably stdin, which is not seekable
        
    def detectPDLHandler(self) :    
        """Tries to autodetect the document format.
        
           Returns the correct PDL handler class or None if format is unknown
        """   
        # Try to detect file type by reading first and last blocks of datas    
        # Each parser can read them automatically, but here we do this only once.
        self.infile.seek(0)
        firstblock = self.infile.read(pdlparser.FIRSTBLOCKSIZE)
        try :
            self.infile.seek(-pdlparser.LASTBLOCKSIZE, 2)
            lastblock = self.infile.read(pdlparser.LASTBLOCKSIZE)
        except IOError :    
            lastblock = ""
        self.infile.seek(0)
        if not firstblock :
            raise pdlparser.PDLParserError, "input file %s is empty !" % str(self.filename)
        else :    
            for module in (postscript, \
                           pclxl, \
                           pdf, \
                           pcl345, \
                           escp2, \
                           dvi, \
                           tiff, \
                           zjstream, \
                           ooo) :
                try :               
                    return module.Parser(self.infile, self.debug, firstblock, lastblock)
                except pdlparser.PDLParserError :
                    pass # try next parser
        raise pdlparser.PDLParserError, "Analysis of first data block failed."
            
def main() :    
    """Entry point for PDL Analyzer."""
    parser = optparse.OptionParser(usage="python analyzer.py [options] file1 [file2 ...]")
    parser.add_option("-v", "--version", 
                            action="store_true", 
                            dest="version",
                            help="show pkpgcounter's version number and exit.")
    parser.add_option("-d", "--debug", 
                            action="store_true", 
                            dest="debug",
                            help="activate debug mode.")
    (options, arguments) = parser.parse_args()
    if options.version :
        print "%s" % version.__version__
    else :
        if (not arguments) or ((not sys.stdin.isatty()) and ("-" not in arguments)) :
            arguments.append("-")
        totalsize = 0    
        for arg in arguments :
            try :
                parser = PDLAnalyzer(arg, options.debug)
                totalsize += parser.getJobSize()
            except (IOError, pdlparser.PDLParserError), msg :    
                sys.stderr.write("ERROR: %s\n" % msg)
                sys.stderr.flush()
        print "%s" % totalsize
    
if __name__ == "__main__" :    
    main()
