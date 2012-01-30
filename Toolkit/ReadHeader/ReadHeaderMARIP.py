#!/usr/bin/env cctbx.python
# ReadHeaderMARIP.py
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

class ReadHeaderMARIP(ReadHeader):
    '''A class to read MAR image plate image headers.'''

    def __init__(self, image = None):
        ReadHeader.__init__(self)

        if image:
            self._read_marip_header(image)

        return

    def _read_marip_header(self, image):
        '''Read the contents of the header of this image.'''

        marip_header_bytes = open(image, 'rb').read(4096)

        byte_order = struct.unpack('I', marip_header_bytes[:4])[0]

        little_endian = 1234

        # if this is the native byte order it will have been correctly read
        # as one or the other of these values

        if byte_order == little_endian:
            header_signed_ints = struct.unpack('16i', marip_header_bytes[:64])
        else:
            header_signed_ints = struct.unpack('16i', marip_header_bytes[:64])
            header_array = array.array('i', header_signed_ints)
            header_array.byteswap()
            header_signed_ints = tuple(header_array)

        self.image_size_pixels_fast = header_signed_ints[1]
        self.image_size_pixels_slow = header_signed_ints[1]

        self.pixel_size_mm_fast = 0.001 * header_signed_ints[6]
        self.pixel_size_mm_slow = 0.001 * header_signed_ints[7]

        self.wavelength_angstroms = 0.000001 * header_signed_ints[8]
        self.distance_mm = 0.001 * header_signed_ints[9]

        if header_signed_ints[10] != header_signed_ints[11]:
            self.axis_name = 'phi'
            self.osc_start_deg = 0.001 * header_signed_ints[10]
            self.osc_width_deg = 0.001 * (header_signed_ints[11] -
                                          header_signed_ints[10])
        else:
            self.axis_name = 'omega'
            self.osc_start_deg = 0.001 * header_signed_ints[12]
            self.osc_width_deg = 0.001 * (header_signed_ints[13] -
                                          header_signed_ints[12])

        self.angle_twotheta_deg = 0.001 * header_signed_ints[15]
        self.angle_kappa_deg = 0.0
        self.angle_chi_deg = 0.001 * header_signed_ints[14]

        # static things

        self.image_offset = 0
        self.maximum_value = 65535

        # now parse the text region of the header form more information

        for start in range(128, 4095, 64):
            record = marip_header_bytes[start:start + 64].strip()
            if not record:
                continue

            key = record.split()[0]

            if 'DATE' in key:
                self.date_struct = time.strptime(
                    record.replace('DATE', '').strip())
                continue

            if 'SCANNER' in key:
                self.detector_serial_number = record.split()[-1]
                continue

            if 'TIME' in key:
                self.exposure_time_s = float(record.split()[-1])
                continue

            if 'REMARK' in key and 'BEAM' in record:
                x = float(record.split()[2])
                y = float(record.split()[3])
                self.beam_centre_pixels_fast = x / self.pixel_size_mm_fast
                self.beam_centre_pixels_slow = y / self.pixel_size_mm_slow

        return

if __name__ == '__main__':

    import sys

    for arg in sys.argv[1:]:
        print ReadHeaderMARIP(arg)
