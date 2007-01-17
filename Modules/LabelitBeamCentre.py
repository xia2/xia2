#!/usr/bin/env python
# LabelitBeamCentre.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#  
# A module to get the "best" beam centre from a labelit run. This will be
# used from within xia2setup.py as a key part of configuring the .xinfo
# file.
# 
# Note well that this will check the input beam centres from the header to 
# see what they are before they start, and perhaps will set a sensible
# input default (e.g. the middle of the image) for the labelit run.
#
#

import os
import sys
import exceptions
import time

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])



