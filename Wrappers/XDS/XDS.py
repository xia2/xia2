#!/usr/bin/env python
# XDS.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# This module is a generic wrapper for the basic components needed to make
# XDS run, including writing the generic header information. This will 
# include the writing of the information from the image header, for instance,
# and should support all image types defined in the Printheader dictionary.
# That is:
# 
# detector_class = {('adsc', 2304, 81):'adsc q4',
#                   ('adsc', 1502, 163):'adsc q4 2x2 binned',
#                   ('adsc', 4096, 51):'adsc q210',
#                   ('adsc', 2048, 102):'adsc q210 2x2 binned',
#                   ('adsc', 6144, 51):'adsc q315',
#                   ('adsc', 3072, 102):'adsc q315 2x2 binned',
#                   ('marccd', 4096, 73):'mar 300',
#                   ('marccd', 3072, 73):'mar 225',
#                   ('marccd', 2048, 79):'mar 165',
#                   ('mar', 2300, 150):'mar 345'}
#
# as of starting this wrapper, 11th December 2006. These detector types
# will map onto standard input records, including the directions of the
# different axes (beam, detector x, detector y) trusted regions of the
# detector (e.g. does the picture go to the corners) and so on.
