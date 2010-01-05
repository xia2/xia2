#!/bin/sh -fe
#
# CVS Id $Id: make_icons.sh,v 1.6 2010/01/05 11:12:03 pjx Exp $
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
#
# Create a "warning" symbol
#
convert -size 32x32 xc:transparent -fill yellow -stroke orange -draw "polygon 16,4 4,28 28,28" -stroke black -fill black -pointsize 22 -font Bitstream-Vera-Sans-Mono-Bold -draw "text 10,26 '!'" icons/warning.png
# Make it a bit smaller
convert icons/warning.png -resize 25 icons/warning.png
#
# Create an "info" symbol
#
convert -size 32x32 xc:transparent -fill orange -stroke orange -draw "circle 16,16 30,16" -stroke orange -strokewidth 1 -fill white -pointsize 34 -font Century-Schoolbook-Bold -draw "text 9,27 'i'" icons/info.png
# Make it a bit smaller
convert icons/info.png -resize 20 icons/info.png
