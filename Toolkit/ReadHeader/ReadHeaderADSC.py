#!/usr/bin/env cctbx.python
# ReadHeaderADSC.py
# 
#   Copyright (C) 2010 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# Code to read an ADXV image header and populate the contents of the standard
# image header ReadHeader class.

from ReadHeader import ReadHeader
from ReadHeaderSMV import ReadHeaderSMV

class ReadHeaderADSC(ReadHeader):
    '''A class to read ADSC image headers.'''

    def __init__(self, image = None):
        ReadHeader.__init__(self)

        if image:
            self._read_adsc_header(image)

        return

    def _read_adsc_header(self, image):
        '''Read the contents of the header of this image.'''

        # first: boring, fetch the things we want and rename them

        size, header = ReadHeaderSMV(image)

        beam_centre_x_mm = float(header['BEAM_CENTRE_X'])
        beam_centre_y_mm = float(header['BEAM_CENTRE_Y'])
        
        date = header['DATE']

        exposure_time = float(header['TIME'])
        distance = float(header['DISTANCE'])
        wavelength = float(header['WAVELENGTH'])

        pixel_size = float(header['PIXEL_SIZE'])
        width = float(header['SIZE1'])
        height = float(header['SIZE2'])
        pixel_depth = 2
        
        osc_start = float(header['OSC_START'])
        osc_range = float(header['OSC_RANGE'])
        two_theta = float(header['TWO_THETA'])

        detector_sn = int(header['DETECTOR_SN'])

        image_offset = int(header['IMAGE_PEDESTAL'])
        maximum_value = int(header['CCD_IMAGE_SATURATION'])

        # then transform them the way I want

        image_size_pixels_fast = width
        image_size_pixels_slow = height

        pixel_size_mm_fast = pixel_size
        pixel_size_mm_slow = pixel_size

        beam_centre_pixels_fast = beam_centre_y_mm
        beam_centre_pixels_slow = beam_centre_x_mm

        # then store them

        

        return
