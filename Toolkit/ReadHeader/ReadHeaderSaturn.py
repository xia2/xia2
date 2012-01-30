#!/usr/bin/env cctbx.python
# ReadHeaderSaturn.py
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

import time

class ReadHeaderSaturn(ReadHeader):
    '''A class to read Saturn image headers.'''

    def __init__(self, image = None):
        ReadHeader.__init__(self)

        if image:
            self._read_a200_header(image)

        return

    def _read_a200_header(self, image):
        '''Read the contents of the header of this image.'''

        size, header = ReadHeaderSMV(image)

        beam_centre_pixels_xy = map(
            float, header['CCD_SPATIAL_BEAM_POSITION'].split())

        self.date_struct = (1970, 1, 1, 1, 1, 1, 1, 1, -1)
        self.epoch_ms = 0

        # ROTATION= start end incr time nosc ndark ndarkup dlim ndc ndcup

        self.exposure_time_s = float(header['ROTATION'].split()[3])
        distance_index = header['CCD_GONIO_NAMES'].split().index('Distance')
        self.distance_mm = float(
            header['CCD_GONIO_VALUES'].split()[distance_index])
        self.wavelength_angstroms = float(header['SCAN_WAVELENGTH'])

        pixel_xy = map(
            float, header['CCD_SPATIAL_DISTORTION_INFO'].split()[-2:])

        self.pixel_size_mm_fast = pixel_xy[0]
        self.pixel_size_mm_slow = pixel_xy[1]

        self.image_size_pixels_fast = int(header['SIZE1'])
        self.image_size_pixels_slow = int(header['SIZE2'])
        self.pixel_depth_bytes = 2

        scan_rotation = map(float, header['SCAN_ROTATION'].split())

        # FIXME verify that this is correct in other definitions

        self.osc_start_deg = scan_rotation[0]
        self.osc_width_deg = scan_rotation[2]

        # FIXME assume that this is in place for the moment

        twotheta_index = header['CCD_GONIO_NAMES'].split().index('2Theta')
        self.angle_twotheta_deg = float(
            header['CCD_GONIO_VALUES'].split()[twotheta_index])

        # and assume that these are not in the image header

        self.angle_kappa_deg = 0.0
        self.angle_chi_deg = 0.0

        self.detector_serial_number = header['CCD_SERIAL_NUMBER']

        self.image_offset = int(header.get('DARK_PEDESTAL', '0'))
        self.maximum_value = int(header.get('OVERLOAD_THRESHOLD', '65535'))

        # FIXME this should probably check with the fast and slow directions.

        self.beam_centre_pixels_fast = beam_centre_pixels_xy[0]
        self.beam_centre_pixels_slow = beam_centre_pixels_xy[1]

        self.header_length = size

        return


if __name__ == '__main__':

    import sys

    for arg in sys.argv[1:]:
        print ReadHeaderSaturn(arg)
