#!/bin/sh -fe
#
# CVS Id $Id: make_icons.sh,v 1.2 2009/11/19 18:55:50 pjx Exp $
#
# Use ImageMagick convert to make little circle PNGs
# Each PNG represents one of the possible image statuses
# from XIA2
#
# Run this once to create the required PNGs
#
# Note to self for using convert...-draw:
# -draw "circle x0,y0 x1,y1"
# uses x0,y0 = centre and x1,y1 = any point on the perimeter
#
convert -size 12x12 xc:transparent -fill green -stroke white -draw "rectangle 0,0 12,12" icons/img_good.png

convert -size 12x12 xc:transparent -fill red -stroke white -draw "rectangle 0,0 12,12" icons/img_overloaded.png

convert -size 12x12 xc:transparent -fill lightblue -stroke white -draw "rectangle 0,0 12,12" icons/img_ok.png

convert -size 12x12 xc:transparent -fill black -stroke white -draw "rectangle 0,0 12,12" icons/img_many_bad.png

convert -size 12x12 xc:transparent -fill yellow -stroke white -draw "rectangle 0,0 12,12" icons/img_bad_rmsd.png

convert -size 12x12 xc:transparent -fill orange -stroke white -draw "rectangle 0,0 12,12" icons/img_abandoned.png

convert -size 12x12 xc:transparent icons/img_blank.png
