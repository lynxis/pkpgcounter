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

import psyco

from PIL import Image

""" RGB to CMYK formula :

        Black = min(1 - r, 1 - g, 1 - b)
        Cyan = (1 - r - Black) / (1 - Black)
        Magenta = (1 - g - Black) / (1 - Black)
        Yellow = (1 - b - Black) / (1 - Black)
"""        

def percent_cmy(fname) :
    result = []
    img = Image.open(fname)
    (r, g, b) = [ p.histogram() for p in img.split() ]
    nbpix = sum(r)
    for histo in (r, g, b) :
        value = 0
        for i in range(len(histo)) :
            value += histo[i] * (255 - i)
        result.append((100 * (value / 255.0)) / nbpix)
    return tuple(result)        

if __name__ == "__main__" :
    psyco.bind(percent_cmy)
    print percent_cmy(sys.argv[1])
