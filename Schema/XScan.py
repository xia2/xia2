#!/usr/bin/env python
# XScan.py
#   Copyright (C) 2011 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#  
# A model for the scan for the "updated experimental model" project documented
# in internal ticket #1555. This is not designed to be used outside of the 
# XSweep classes.

import pycbf
import math

class XScan:
    '''A class to represent the scan used to perform a rotation method X-ray
    diffraction experiment. In essence this is the information provided to the
    camera on where the images should go, how long the exposures should be
    and how the frames are formatted.'''

    def __init__(self, template, directory, image_range, exposure_time,
                 format, epochs):
        '''Construct a new scan class, which represents the information given
        to the camera to perform the diffraction experiment. N.B. though some
        of this information could be derived from image headers within the
        class it was felt to be more flexible to expose that kind of cleverness
        in factory functions. (i) format must be one of the types enumerated
        in XScanHelper.FORMAT_NAME (ii) Require that the exposure times and
        epochs are passed in as dictionaries incexed by image numbers in
        range image_range[0] to image_range[1] inclusive however (iii) do not
        presume in here that the images must exist when the XScan object is
        constructed.'''

        


        
class XScanFactory:

    @staticmethod
    def Simple():
        return XScan('template', 'directory', 'image_range', 'exposure_time',
                     'format', 'epochs')
