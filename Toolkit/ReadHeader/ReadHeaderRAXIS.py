#!/usr/bin/env cctbx.python
# ReadHeaderRAXIS.py
#
#   Copyright (C) 2010 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Code to read an MAR image plate image header and populate the contents of
# the standard image header ReadHeader class.

import os
import sys
import copy
import time
import datetime
import math
import exceptions
import binascii
import struct
import array
from ReadHeader import ReadHeader

class ReadHeaderRAXIS(ReadHeader):
    '''A class to read RAXIS image plate image headers.'''

    def __init__(self, image = None):
        ReadHeader.__init__(self)

        if image:
            self._read_raxis_header(image)

        return

    def _read_raxis_header(self, image):
        '''Read the contents of the header of this image.'''

        raxis_header = open(sys.argv[1]).read(2048)

        # this should be SGI if the images are big endian - which
        # I assume below that they are....

        assert(raxis_header[812:822].strip() == 'SGI')

        # also assert that X is the fast direction and Z (vertical)
        # is the slow direction

        self.image_size_pixels_fast = struct.unpack(
            '>i', raxis_header[768:772])[0]
        self.image_size_pixels_slow = struct.unpack(
            '>i', raxis_header[772:776])[0]

        self.pixel_size_mm_fast = struct.unpack(
            '>f', raxis_header[776:780])[0]
        self.pixel_size_mm_slow = struct.unpack(
            '>f', raxis_header[780:784])[0]

        self.wavelength_angstroms = struct.unpack(
            '>f', raxis_header[292:296])[0]
        self.distance_mm = struct.unpack(
            '>f', raxis_header[344:348])[0]

        self.osc_start_deg = struct.unpack(
            '>f', raxis_header[524:528])[0]
        osc_end_deg = struct.unpack(
            '>f', raxis_header[528:532])[0]
        self.osc_width_deg = osc_end_deg - self.osc_start_deg

        self.angle_twotheta_deg = struct.unpack(
            '>f', raxis_header[556:560])[0]
        self.angle_kappa_deg = 0.0
        self.angle_chi_deg = struct.unpack(
            '>f', raxis_header[552:556])[0]

        # static things

        self.image_offset = 0
        self.maximum_value = 65535

        self.date_struct = time.strptime(
            raxis_header[256:268].strip(), '%Y-%m-%d')
        self.detector_serial_number = ''
        self.exposure_time_s = struct.unpack(
            '>f', raxis_header[536:540])[0]

        self.beam_centre_pixels_fast = struct.unpack(
            '>f', raxis_header[540:544])[0]
        self.beam_centre_pixels_slow = struct.unpack(
            '>f', raxis_header[544:548])[0]

        # FIXME - get the other axes out and record the values - e.g. for omega
        # scans etc. These are buried in:
        #
        # naxes = struct.unpack('>i', raxis_header[856:860])[0]
        # values = struct.unpack('>30f', raxis_header[860:980])
        #
        # (up to 5) * 3 values giving the dirctions of the axes then
        # up to 5 starts, up to 5 ends, up to 5 offsets gives total
        # of 30 floats

        return

if __name__ == '__main__':

    import sys

    for arg in sys.argv[1:]:
        print ReadHeaderRAXIS(arg)
