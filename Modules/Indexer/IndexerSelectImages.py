#!/usr/bin/env python
# IndexSelectImages.py
# 
#   Copyright (C) 2011 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# Code for the selection of images for autoindexing - selecting lone images
# from a list or wedges from a list, for Mosflm / Labelit and XDS respectively.

import math

def index_select_images_lone(phi_width, images):
    '''Select images close to 0, 45 and 90 degrees from the list of available
    frames. N.B. we assume all frames have the same oscillation width.'''

    
