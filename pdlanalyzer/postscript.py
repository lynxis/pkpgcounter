#! /usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# pkpgcounter : a generic Page Description Language parser
#
# (c) 2003,2004,2005 Jerome Alet <alet@librelogiciel.com>
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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.
#
# $Id$
#

import sys
import popen2

from pdlanalyzer import pdlparser

class PostScriptParser(pdlparser.PDLParser) :
    """A parser for PostScript documents."""
    def throughGhostScript(self) :
        """Get the count through GhostScript, useful for non-DSC compliant PS files."""
        if self.debug :
            sys.stderr.write("Internal parser sucks, using GhostScript instead...\n")
        self.infile.seek(0)
        command = 'gs -sDEVICE=bbox -dNOPAUSE -dBATCH -dQUIET - 2>&1 | grep -c "%%HiResBoundingBox:" 2>/dev/null'
        child = popen2.Popen4(command)
        try :
            data = self.infile.read(MEGABYTE)    
            while data :
                child.tochild.write(data)
                data = self.infile.read(MEGABYTE)
            child.tochild.flush()
            child.tochild.close()    
        except (IOError, OSError), msg :    
            raise pdlparser.PDLParserError, "Problem during analysis of Binary PostScript document : %s" % msg
            
        pagecount = 0
        try :
            pagecount = int(child.fromchild.readline().strip())
        except (IOError, OSError, AttributeError, ValueError), msg :
            raise pdlparser.PDLParserError, "Problem during analysis of Binary PostScript document : %s" % msg
        child.fromchild.close()
        
        try :
            child.wait()
        except OSError, msg :    
            raise pdlparser.PDLParserError, "Problem during analysis of Binary PostScript document : %s" % msg
        return pagecount * self.copies
        
    def natively(self) :
        """Count pages in a DSC compliant PostScript document."""
        self.infile.seek(0)
        pagecount = 0
        for line in self.infile.xreadlines() : 
            if line.startswith("%%Page: ") :
                pagecount += 1
            elif line.startswith("%%Requirements: numcopies(") :    
                try :
                    number = int(line.strip().split('(')[1].split(')')[0])
                except :     
                    pass
                else :    
                    if number > self.copies :
                        self.copies = number
            elif line.startswith("%%BeginNonPPDFeature: NumCopies ") :
                # handle # of copies set by some Windows printer driver
                try :
                    number = int(line.strip().split()[2])
                except :     
                    pass
                else :    
                    if number > self.copies :
                        self.copies = number
            elif line.startswith("1 dict dup /NumCopies ") :
                # handle # of copies set by mozilla/kprinter
                try :
                    number = int(line.strip().split()[4])
                except :     
                    pass
                else :    
                    if number > self.copies :
                        self.copies = number
        return pagecount * self.copies
        
    def getJobSize(self) :    
        """Count pages in PostScript document."""
        return self.natively() or self.throughGhostScript()
        
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
            parser = PostScriptParser(infile, debug=1)
            totalsize += parser.getJobSize()
        except pdlparser.PDLParserError, msg :    
            sys.stderr.write("ERROR: %s\n" % msg)
            sys.stderr.flush()
        if mustclose :    
            infile.close()
    print "%s" % totalsize
    
if __name__ == "__main__" :    
    test()
