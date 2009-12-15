#!/bin/sh -fe
#
# CVS Id $Id: make_icons.sh,v 1.3 2009/12/15 09:47:54 pjx Exp $
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
convert -size 12x12 xc:white -fill green -stroke white -draw "rectangle 0,0 11,11" icons/img_good.png

convert -size 12x12 xc:white -fill red -stroke white -draw "rectangle 0,0 11,11" icons/img_overloaded.png

convert -size 12x12 xc:white -fill lightblue -stroke white -draw "rectangle 0,0 11,11" icons/img_ok.png

convert -size 12x12 xc:white -fill black -stroke white -draw "rectangle 0,0 11,11" icons/img_many_bad.png

convert -size 12x12 xc:white -fill yellow -stroke white -draw "rectangle 0,0 11,11" icons/img_bad_rmsd.png

convert -size 12x12 xc:white -fill orange -stroke white -draw "rectangle 0,0 11,11" icons/img_abandoned.png

convert -size 12x12 xc:white icons/img_blank.png
