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

"""This is the main module of pkpgcounter.

It defines the PDLAnalyzer class, which provides a generic way to parse
input files, by automatically detecting the best parser to use."""

import sys
import os
import tempfile

import version, pdlparser, postscript, pdf, pcl345, pclxl, \
       escp2, dvi, tiff, ooo, zjstream, qpdl, spl1, plain
import inkcoverage

class AnalyzerOptions :
    """A class for use as the options parameter to PDLAnalyzer's constructor."""
    def __init__(self, debug=None,
                       colorspace=None,
                       resolution=None) :
        """Sets initial attributes."""
        self.debug = debug
        self.colorspace = colorspace
        self.resolution = resolution
    
    
class PDLAnalyzer :    
    """Class for PDL autodetection."""
    def __init__(self, filename, options=AnalyzerOptions()) :
        """Initializes the PDL analyzer.
        
           filename is the name of the file or '-' for stdin.
           filename can also be a file-like object which 
           supports read() and seek().
        """
        self.options = options
        self.filename = filename
        self.infile = None
        self.mustclose = None
        
    def getJobSize(self) :    
        """Returns the job's size."""
        size = 0
        self.openFile()
        try :
            try :
                pdlhandler = self.detectPDLHandler()
                size = pdlhandler.getJobSize()
            except pdlparser.PDLParserError, msg :    
                raise pdlparser.PDLParserError, "Unknown file format for %s (%s)" % (self.filename, msg)
        finally :    
            self.closeFile()
        return size
            
    def getInkCoverage(self, colorspace=None, resolution=None) :
        """Extracts the percents of ink coverage from the input file."""
        result = None
        cspace = colorspace or self.options.colorspace
        res = resolution or self.options.resolution
        if (not cspace) or (not res) :
            raise ValueError, "Invalid colorspace (%s) or resolution (%s)" % (cspace, res)
        self.openFile()
        try :
            try :
                pdlhandler = self.detectPDLHandler()
                tiffname = self.convertToTiffMultiPage24NC(pdlhandler)
                result = inkcoverage.getInkCoverage(tiffname, cspace)
                try :
                    os.remove(tiffname)
                except OSError :
                    sys.stderr.write("Problem when trying to remove temporary file %s\n" % tiffname)
            except pdlparser.PDLParserError, msg :    
                raise pdlparser.PDLParserError, "Unknown file format for %s (%s)" % (self.filename, msg)
        finally :    
            self.closeFile()
        return result
        
    def convertToTiffMultiPage24NC(self, handler) :    
        """Converts the input file to TIFF format, X dpi, 24 bits per pixel, uncompressed.
           Returns a temporary filename which names a file containing the TIFF datas.
           The temporary file has to be deleted by the caller.
        """   
        self.infile.seek(0)
        (handle, filename) = tempfile.mkstemp(".tmp", "pkpgcounter")    
        os.close(handle)
        handler.convertToTiffMultiPage24NC(filename, self.options.resolution)
        return filename
        
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
            except IOError :    
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
            # IMPORTANT : the order is important below. FIXME.
            for module in (postscript, \
                           pclxl, \
                           pdf, \
                           qpdl, \
                           spl1, \
                           dvi, \
                           tiff, \
                           zjstream, \
                           ooo, \
                           pcl345, \
                           escp2, \
                           plain) :     # IMPORTANT : don't move this one up !
                try :               
                    return module.Parser(self.infile, self.options.debug, firstblock, lastblock)
                except pdlparser.PDLParserError :
                    pass # try next parser
        raise pdlparser.PDLParserError, "Analysis of first data block failed."
            
def main() :    
    """Entry point for PDL Analyzer."""
    import optparse
    from copy import copy
    
    def check_cichoice(option, opt, value) :
        """To add a CaseIgnore Choice option type."""
        valower = value.lower()
        if valower in [v.lower() for v in option.cichoices] :
            return valower
        else :    
            choices = ", ".join([repr(o) for o in option.cichoices])
            raise optparse.OptionValueError(
                "option %s: invalid choice: %r (choose from %s)"
                % (opt, value, choices))
    
    class MyOption(optparse.Option) :
        """New Option class, with CaseIgnore Choice type."""
        TYPES = optparse.Option.TYPES + ("cichoice",)
        ATTRS = optparse.Option.ATTRS + ["cichoices"]
        TYPE_CHECKER = copy(optparse.Option.TYPE_CHECKER)
        TYPE_CHECKER["cichoice"] = check_cichoice
        
    parser = optparse.OptionParser(option_class=MyOption, 
                                   usage="python analyzer.py [options] file1 [file2 ...]")
    parser.add_option("-v", "--version", 
                            action="store_true", 
                            dest="version",
                            help="Show pkpgcounter's version number and exit.")
    parser.add_option("-d", "--debug", 
                            action="store_true", 
                            dest="debug",
                            help="Activate debug mode.")
    parser.add_option("-c", "--colorspace", 
                            dest="colorspace",
                            type="cichoice",
                            cichoices=["bw", "rgb", "cmyk", "cmy"],
                            help="Activate the computation of ink usage, and defines the colorspace to use. Supported values are 'BW', 'RGB', 'CMYK', and 'CMY'.")
    parser.add_option("-r", "--resolution", 
                            type="int", 
                            default=72, 
                            dest="resolution",
                            help="The resolution in DPI to use when checking ink usage. Lower resolution is faster but less accurate. Default is 72 dpi.")
    (options, arguments) = parser.parse_args()
    if options.version :
        print "%s" % version.__version__
    elif not (72 <= options.resolution <= 1200) :    
        sys.stderr.write("ERROR: the argument to the --resolution command line option must be between 72 and 1200.\n")
        sys.stderr.flush()
    else :
        if (not arguments) or ((not sys.stdin.isatty()) and ("-" not in arguments)) :
            arguments.append("-")
        totalsize = 0    
        lines = []
        try :
            for arg in arguments :
                try :
                    parser = PDLAnalyzer(arg, options)
                    if not options.colorspace :
                        totalsize += parser.getJobSize()
                    else :
                        (cspace, pages) = parser.getInkCoverage()
                        for page in pages :
                            lineparts = []
                            for k in cspace : # NB : this way we preserve the order of the planes
                                try :
                                    lineparts.append("%s : %s%%" % (k, ("%f" % page[k]).rjust(10)))
                                except KeyError :
                                    pass
                            lines.append("      ".join(lineparts))     
                except (IOError, pdlparser.PDLParserError), msg :    
                    sys.stderr.write("ERROR: %s\n" % msg)
                    sys.stderr.flush()
        except KeyboardInterrupt :            
            sys.stderr.write("WARN: Aborted at user's request.\n")
            sys.stderr.flush()
        if not options.colorspace :    
            print "%s" % totalsize
        else :    
            print "\n".join(lines)
    
if __name__ == "__main__" :    
    main()
