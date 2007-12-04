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
import md5
import tempfile

MEGABYTE = 1024 * 1024

def getAvailableDevices() :
    """Returns a list of available GhostScript devices.
    
       The list is returned without any x11, bbox, nor ijs related device.
    """
    answerfd = os.popen('/bin/echo "devicenames ==" | gs -dBATCH -dQUIET -dNOPAUSE -dPARANOIDSAFER -sDEVICE=nullpage -', "r")
    answer = answerfd.readline().strip()
    if not answerfd.close() :
        if answer.startswith("[/") and answer.endswith("]") :
            devices = [ dev[1:] for dev in answer[1:-1].split() \
                                    if dev.startswith("/") \
                                       and (not dev.startswith("/x11")) \
                                       and (not dev == "/ijs") \
                                       and (not dev == "/nullpage") \
                                       and (not dev == "/bbox") ]
            devices.sort()                           
            return devices
    return []
        
def getAvailableIJSPrintClasses() :
    """Returns a list of available IJS Print Classes.
    
       Currently the list is a static one and doesn't contain all the available print classes.
    """
    return [ "DJ3600", "DJ3320", "DJ9xx", "DJGenericVIP", "LJColor", 
             "DJ850", "DJ890", "DJ9xxVIP", "DJ8xx", "DJ540", "DJ660",
             "DJ6xx", "DJ350", "DJ6xxPhoto", "DJ630", "DJ8x5", "DJ4100",
             "AP21xx", "AP2560", "AP2xxx", "PSP100", "PSP470", "Undefined",
             "Postscript", "LJJetReady", "LJMono", "LJFastRaster",
             "LJZjsMono", ]
        
def batchGeneration(infilename, devices, root, command) :
    """Loops over a set of devices calling a particular command."""
    for device in devices :
        outfilename = "%(root)s.%(device)s" % locals()
        if os.path.exists(outfilename) and os.stat(outfilename).st_size :
            sys.stdout.write("Skipping %(outfilename)s : already exists.\n" % locals())
        else :    
            sys.stdout.write("Generating %(outfilename)s " % locals())
            sys.stdout.flush()
            os.system(command % locals())
            sys.stdout.write("\n")
            
        if not os.path.exists(outfilename) :
            sys.stderr.write("ERROR while generating %(outfilename)s\n" % locals())
    
def genTestSuite(infilename, root) :
    """Generate the testsuite."""
    batchGeneration(infilename, getAvailableDevices(), 
                                root, 
                                'gs -dQUIET -dBATCH -dNOPAUSE -dPARANOIDSAFER -sOutputFile="%(outfilename)s" -sDEVICE="%(device)s" "%(infilename)s"')
                                
    batchGeneration(infilename, getAvailableIJSPrintClasses(), 
                                "%(root)s.hpijs" % locals(), 
                                'gs -dBATCH -dQUIET -dPARANOIDSAFER -dNOPAUSE -sDEVICE=ijs -sIjsServer=hpijs -dIjsUseOutputFD -sDeviceManufacturer="HEWLETT-PACKARD" -sDeviceModel="%(device)s" -sOutputFile="%(outfilename)s" "%(infilename)s"')
            
def computeSize(filename) :    
    """Computes the size in pages of a file in the testsuite."""
    answerfd = os.popen('pkpgcounter "%(filename)s" 2>/dev/null' % locals(), "r")
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
    else :    
        sys.stdout.write("Master file's contains %(mastersize)i pages.\n" % locals())
    passed = failed = unsupported = 0
    testsuite = glob.glob("%(root)s.*" % locals())
    testsuite.sort()
    nbtests = len(testsuite)
    for testfname in testsuite :
        sys.stdout.write("Testing %(testfname)s ... " % locals())
        sys.stdout.flush()
        size = computeSize(testfname)
        if size != mastersize :
            if not size :
                sys.stdout.write("ERROR : Unsupported file format\n")
                unsupported += 1
            else :    
                sys.stdout.write("WARN : Found %(size)i pages instead of %(mastersize)i\n" % locals())
                failed += 1
        else :    
            sys.stdout.write("OK\n")
            passed += 1
    sys.stdout.write("     Passed : %i/%i (%.2f%%)\n" % (passed, nbtests, 100.0 * passed / nbtests))
    sys.stdout.write("     Failed : %i/%i (%.2f%%)\n" % (failed, nbtests, 100.0 * failed / nbtests))
    sys.stdout.write("Unsupported : %i/%i (%.2f%%)\n" % (unsupported, nbtests, 100.0 * unsupported / nbtests))
            
def main() :        
    """Main function."""
    if len(sys.argv) == 1 :
        sys.argv.append("-")
    if len(sys.argv) != 2 :
        sys.stderr.write("usage : gengstests.py [inputfile.ps]\n")
        sys.exit(-1)
    else :    
        checksum = md5.new() # Ensures we'll recreate a new testsuite if input is different
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
                checksum.update(data)
            tmp.flush()    
        else :    
            checksum.update(infilename)
        genTestSuite(infilename, "testsuite.%s" % checksum.hexdigest())
        runTests(infilename, "testsuite")
            
        if istemp :    
            # Cleanly takes care of the temporary file
            tmp.close()
            
if __name__ == "__main__" :
    sys.exit(main())
        
