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
#

"""This script generates a testsuite from a PostScript input file and ghostscript."""

import sys
import os
import glob
import tempfile

MEGABYTE = 1024 * 1024

def getAvailableDevices() :
    """Returns a list of available GhostScript devices.
    
       The list is returned without any x11, bbox, nor ijs related device.
    """
    answerfd = os.popen('/bin/echo "devicenames ==" | gs -dBATCH -dQUIET -dNOPAUSE -dPARANOIDSAFER -sDEVICE=nullpage -', "r")
    answer = answerfd.readline().strip()
    answerfd.close()
    if answer.startswith("[/") and answer.endswith("]") :
        devices = [ dev[1:] for dev in answer[1:-1].split() \
                                if dev.startswith("/") \
                                   and (not dev.startswith("/x11")) \
                                   and (not dev == "/ijs") \
                                   and (not dev == "/nullpage") \
                                   and (not dev == "/bbox") ]
        devices.sort()                           
        return devices
    else :
        return []
        
def genTestSuite(infilename, root) :
    """Generate the testsuite."""
    for device in getAvailableDevices() :
        outfilename = "%(root)s.%(device)s" % locals()
        if not os.path.exists(outfilename) :
            sys.stdout.write("Generating %(outfilename)s " % locals())
            sys.stdout.flush()
            os.system('gs -dQUIET -dBATCH -dNOPAUSE -dPARANOIDSAFER -sOutputFile="%(outfilename)s" -sDEVICE="%(device)s" "%(infilename)s"' % locals())
            sys.stdout.write("\n")
        else :    
            sys.stdout.write("Skipping %(outfilename)s : already exists.\n" % locals())
            
        if not os.path.exists(outfilename) :
            sys.stderr.write("ERROR while generating %(outfilename)s\n" % locals())
            
def computeSize(filename) :    
    """Computes the size in pages of a file in the testsuite."""
    answerfd = os.popen('pkpgcounter "%(filename)s"' % locals(), "r")
    try :
        try :
            return int(answerfd.readline().strip())
        except (ValueError, TypeError) :    
            return 0
    finally :        
        answerfd.close()
    
def runTests(masterfilename, root) :
    """Launches the page counting tests against the testsuite."""
    mastersize = computeSize(masterfilename)
    if not mastersize :
        raise RuntimeError, "Unable to compute the size of the testsuite's master file %(masterfilename)s" % locals()
        
    passed = 0
    failed = 0
    testsuite = glob.glob("%(root)s.*" % locals())
    nbtests = len(testsuite)
    for testfname in testsuite :
        sys.stdout.write("Testing %(testfname)s ... " % locals())
        sys.stdout.flush()
        size = computeSize(testfname)
        if size != mastersize :
            sys.stdout.write("ERROR\n")
            failed += 1
        else :    
            sys.stdout.write("OK\n")
            passed += 1
    print "Passed : %i (%.2f%%)" % (passed, 100.0 * passed / nbtests)
    print "Failed : %i (%.2f%%)" % (failed, 100.0 * failed / nbtests)
            
def main() :        
    """Main function."""
    if len(sys.argv) == 1 :
        sys.argv.append("-")
    if len(sys.argv) != 2 :
        sys.stderr.write("usage : gengstests.py [inputfile.ps]\n")
        sys.exit(-1)
    else :    
        infilename = sys.argv[1]
        istemp = False
        if infilename == "-" :
            # Input is standard input, so we must use a temporary
            # file to be able to loop over all available devices.
            tmp = tempfile.NamedTemporaryFile(mode="w+b")
            istemp = True
            infilename = tmp.name
            while True :
                data = sys.stdin.read(MEGABYTE)
                if not data :
                    break
                tmp.write(data)
            tmp.flush()    
            
        genTestSuite(infilename, "testsuite")
        runTests(infilename, "testsuite")
            
        if istemp :    
            # Cleanly takes care of the temporary file
            tmp.close()
            
if __name__ == "__main__" :
    sys.exit(main())
        
