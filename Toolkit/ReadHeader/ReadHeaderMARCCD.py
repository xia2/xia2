#!/usr/bin/env cctbx.python
# ReadHeaderMARCCD.py
#
#   Copyright (C) 2010 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Code to read an MARCCD image header and populate the contents of the standard
# image header ReadHeader class.

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

class ReadHeaderMARCCD(ReadHeader):
    '''A class to read MARCCD image headers.'''

    def __init__(self, image = None):
        ReadHeader.__init__(self)

        if image:
            self._read_marccd_header(image)

        return

    def _read_marccd_header(self, image):
        '''Read the contents of the header of this image.'''

        marccd_header_bytes = open(image, 'rb').read(4096)[1024:]

        # first determine if the header byte order is little endian or
        # big endian

        byte_order = struct.unpack('I', marccd_header_bytes[28:32])[0]

        little_endian = 1234
        big_endian = 4321

        # if this is the native byte order it will have been correctly read
        # as one or the other of these values

        if byte_order == little_endian or byte_order == big_endian:
            header_unsigned_ints = struct.unpack('768I', marccd_header_bytes)
            header_signed_ints = struct.unpack('768i', marccd_header_bytes)
        else:
            header_unsigned_ints = struct.unpack('768I', marccd_header_bytes)
            header_array = array.array('I', header_unsigned_ints)
            header_array.byteswap()
            header_unsigned_ints = tuple(header_array)

            header_signed_ints = struct.unpack('768i', marccd_header_bytes)
            header_array = array.array('i', header_signed_ints)
            header_array.byteswap()
            header_signed_ints = tuple(header_array)

        # now we have the header right, copy & transform to correct format

        self.image_size_pixels_fast = header_unsigned_ints[20]
        self.image_size_pixels_slow = header_unsigned_ints[21]

        #self.date_struct =
        #self.epoch_ms =

        self.exposure_time_s = 0.001 * header_unsigned_ints[164]

        if header_unsigned_ints[160]:
            self.distance_mm = 0.001 * header_signed_ints[160]
        else:
            self.distance_mm = 0.001 * header_signed_ints[174]

        self.wavelength_angstroms = 0.00001 * header_unsigned_ints[227]

        self.pixel_size_mm_fast = 0.000001 * header_unsigned_ints[193]
        self.pixel_size_mm_slow = 0.000001 * header_unsigned_ints[194]

        self.pixel_depth_bytes = 2

        axis_names = ['twotheta', 'omega', 'chi', 'kappa',
                      'phi', 'delta', 'gamma']

        axis = header_unsigned_ints[183]
        self.axis_name = axis_names[axis]

        self.osc_start_deg = 0.001 * header_signed_ints[167 + axis]

        if header_signed_ints[175 + axis]:
            osc_end = 0.001 * header_signed_ints[175 + axis]
            self.osc_width_deg = osc_end - self.osc_start_deg
        else:
            self.osc_width_deg = 0.001 * header_signed_ints[184]

        self.angle_twotheta_deg = 0.001 * header_signed_ints[167]
        self.angle_kappa_deg = 0.001 * header_signed_ints[170]
        self.angle_chi_deg = 0.001 * header_signed_ints[169]

        self.image_offset = 0
        self.maximum_value = header_unsigned_ints[26]

        self.beam_centre_pixels_fast = 0.001 * header_signed_ints[161]
        self.beam_centre_pixels_slow = 0.001 * header_signed_ints[162]

        # Workaround: some beamlines store this position in mm despite the
        # fact that this according to the specification should be in pixels -
        # check if it would make more sense in pixels.

        self._check_marccd_beam_in_pixels()

        self.header_length = 4096

        datestring = marccd_header_bytes[1376:1408].strip()

        month = int(datestring[:2])
        day = int(datestring[2:4])
        hour = int(datestring[4:6])
        minute = int(datestring[6:8])
        year = int(datestring[8:12])
        second = int(datestring[13:15])
        self.date_struct = datetime.datetime(year, month, day,
                                             hour, minute, second).timetuple()

        self.detector_serial_number = 'N/A'

        comments = marccd_header_bytes[1440:1440 + 512]

        for record in comments.split('\n'):
            if 'Detector Serial Number' in record:
                self.detector_serial_number = record.split()[-1]

        return

    def _check_marccd_beam_in_pixels(self):
        '''Check that the beam centre we read is probably in pixels not mm.'''

        bx = self.beam_centre_pixels_fast
        by = self.beam_centre_pixels_slow

        nx = self.image_size_pixels_fast
        ny = self.image_size_pixels_slow

        dx = self.pixel_size_mm_fast
        dy = self.pixel_size_mm_slow

        distance_if_pixels = math.sqrt((bx - 0.5 * nx) * (bx - 0.5 * nx) +
                                       (by - 0.5 * ny) * (by - 0.5 * ny))

        distance_if_mm = math.sqrt(
            (bx / dx - 0.5 * nx) * (bx / dx - 0.5 * nx) +
            (by / dy - 0.5 * ny) * (by / dy - 0.5 * ny))

        if distance_if_pixels > 0.25 * math.sqrt(nx * nx + ny * ny) and \
           distance_if_mm < 0.25 * math.sqrt(nx * nx + ny * ny):
            self.beam_centre_pixels_fast /= dx
            self.beam_centre_pixels_slow /= dy

        return

if __name__ == '__main__':

    import sys

    for arg in sys.argv[1:]:
        print ReadHeaderMARCCD(arg)
