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

        self.exposure_time_s = float(header['TIME'])
        self.distance_mm = float(header['DISTANCE'])
        self.wavelength_angstroms = float(header['WAVELENGTH'])

        pixel_size = float(header['PIXEL_SIZE'])

        self.pixel_size_mm_fast = pixel_size
        self.pixel_size_mm_slow = pixel_size
        
        self.image_size_pixels_fast = float(header['SIZE1'])
        self.image_size_pixels_slow = float(header['SIZE2'])
        self.pixel_depth_bytes = 2
        
        self.osc_start_deg = float(header['OSC_START'])
        self.osc_range_deg = float(header['OSC_RANGE'])
        self.angle_twotheta_deg = float(header['TWO_THETA'])
        self.angle_kappa_deg = 0.0
        self.angle_chi_deg = 0.0
        
        self.detector_serial_number = int(header['DETECTOR_SN'])

        self.image_offset = int(header['IMAGE_PEDESTAL'])
        self.maximum_value = int(header['CCD_IMAGE_SATURATION'])

        # FIXME this should probably check with the fast and slow directions.

        self.beam_centre_pixels_fast = beam_centre_y_mm / pixel_size
        self.beam_centre_pixels_slow = beam_centre_x_mm / pixel_size



        

        return
