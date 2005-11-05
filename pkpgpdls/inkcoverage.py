#! /usr/bin/env python
# -*- coding: ISO-8859-15 -*-
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

from PIL import Image

""" RGB to CMYK formula :

        Black = min(1 - r, 1 - g, 1 - b)
        Cyan = (1 - r - Black) / (1 - Black)
        Magenta = (1 - g - Black) / (1 - Black)
        Yellow = (1 - b - Black) / (1 - Black)
"""        

def getPercentCMY(img, nbpix) :
    result = []
    (r, g, b) = [ p.histogram() for p in img.split() ]
    for colorhisto in (r, g, b) :
        result.append(100.0 * (reduce(lambda current, next: current + (next[1] * (255 - next[0])), enumerate(colorhisto), 0) / 255.0) / nbpix)
    return tuple(result)
    
def getPercentBlack(img, nbpix) :
    if img.mode != "L" :
        img = img.convert("L")
    return 100.0 * (reduce(lambda current, next: current + (next[1] * (255 - next[0])), enumerate(img.histogram()[:-1]), 0) / 255.0) / nbpix
    
def getPercents(fname) :
    """Extracts the ink percentages from an image."""
    image = Image.open(fname)
    nbpixels = image.size[0] * image.size[1]
    result = {}
    try :
        result["black"] = getPercentBlack(image, nbpixels)
    except :     
        sys.stderr.write("Problem when extracting BLACK !\n")
    try :    
        result["cmy"] = getPercentCMY(image, nbpixels)
    except :     
        sys.stderr.write("Problem when extracting CMY !\n")
    return result

if __name__ == "__main__" :
    print getPercents(sys.argv[1])
