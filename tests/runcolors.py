#! /usr/bin/env python
# -*- coding: ISO-8859-15 -*-
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
#

"""This document was created with the help of the ReportLab ToolKit (tm)
available as Free Software from http://www.reportlab.org

It contains 9 pages, including this one.

Each page after this one is entirely filled with 100% of a particular
color, as described below :

Page 1 ====> This notice
Page 2 ====> Red
Page 3 ====> Green
Page 4 ====> Blue
Page 5 ====> Cyan
Page 6 ====> Magenta
Page 7 ====> Yellow
Page 8 ====> Black
Page 9 ====> White

This document helps to ensure that the computation of ink coverage
made by pkpgcounter works as expected.

To check by yourself :

  $ for cspace in BW RGB CMY CMYK ; do
        echo "Colorspace : $cspace" ;
        pkpgcounter --colorspace $cspace colors.pdf ;
        echo ;
    done    

Please report any problem to : alet@librelogiciel.com
"""

import sys
try :
    from reportlab.lib import colors
    from reportlab.lib import pagesizes
    from reportlab.lib.units import cm
    from reportlab.pdfgen import canvas
except ImportError :    
    sys.stderr.write("Please download and install ReportLab\n\tfrom http://www.reportlab.org\n")
    sys.exit(-1)

if __name__ == "__main__" :
    canv = canvas.Canvas("colors.pdf", pagesize=pagesizes.A4)
    (width, height) = pagesizes.A4
    xbase = 2*cm
    ybase = height - 2*cm
    
    # First we output the explanations on the first page.
    canv.setFont("Helvetica", 16)
    for line in __doc__.split("\n") :
        canv.drawString(xbase, ybase, line)
        ybase -= 24
    canv.showPage()
    
    # Then we output each page
    for color in (colors.Color(1, 0, 0),        # Red
                  colors.Color(0, 1, 0),        # Green
                  colors.Color(0, 0, 1)) :      # Blue
        canv.setStrokeColorRGB(*color.rgb())          
        canv.setFillColorRGB(*color.rgb())          
        canv.rect(0, 0, width, height, fill=1)
        canv.showPage()
        
    for color in (colors.CMYKColor(1, 0, 0, 0), # Cyan
                  colors.CMYKColor(0, 1, 0, 0), # Magenta
                  colors.CMYKColor(0, 0, 1, 0), # Yellow
                  colors.CMYKColor(0, 0, 0, 1), # Black
                  colors.CMYKColor(0, 0, 0, 0)) : # White
        canv.setStrokeColorCMYK(*color.cmyk())          
        canv.setFillColorCMYK(*color.cmyk())          
        canv.rect(0, 0, width, height, fill=1)
        canv.showPage()
    canv.save()        
