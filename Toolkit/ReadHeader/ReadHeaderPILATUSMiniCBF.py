#!/usr/bin/env cctbx.python
# ReadHeaderPILATUSMiniCBF.py
#
#   Copyright (C) 2010 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Code to read a pilatus minicbf image header and populate the contents of
# the standard image header ReadHeader class.

from ReadHeader import ReadHeader

import time

class ReadHeaderPILATUSMiniCBF(ReadHeader):
    '''A class to read pilatus minicbf image headers.'''

    def __init__(self, image = None):
        ReadHeader.__init__(self)

        if image:
            self._read_pilatus_minicbf(image)

        return

    def _read_pilatus_minicbf(self, image):

        for record in open(image):

            if 'X-Binary-Size-Padding' in record:
                break

            if 'Detector:' in record:
                self.detector_serial_number = record.split(
                    'S/N')[-1].split()[0]
                continue

            if 'Beam_xy' in record:
                data = record.replace('(', ' ').replace(')', ' ').replace(
                    ',', ' ')
                self.beam_centre_pixels_fast = float(data.split()[2])
                self.beam_centre_pixels_slow = float(data.split()[3])
                continue

            if '#' in record and '/' in record:
                datestring = record.replace('#', '').strip()
                format = '%Y/%b/%d %H:%M:%S'
                try:
                    self.date_struct = time.strptime(
                        datestring.split('.')[0], format)
                    self.epoch_ms = 0.001 * int(datestring.split('.')[1])
                except ValueError, e:
                    pass

                continue

            if 'Exposure_time' in record:
                self.exposure_time_s = float(record.split()[2])
                continue

            if 'Detector_distance' in record:
                self.distance_mm = 1000.0 * float(record.split()[2])
                continue

            if 'Wavelength' in record:
                self.wavelength_angstroms = float(record.split()[2])
                continue

            if 'Pixel_size' in record:
                self.pixel_size_mm_fast = 1000.0 * float(record.split()[2])
                self.pixel_size_mm_slow = 1000.0 * float(record.split()[5])
                continue

            if 'X-Binary-Size-Fastest-Dimension' in record:
                self.image_size_pixels_fast = int(record.split()[-1])
                continue

            if 'X-Binary-Size-Second-Dimension' in record:
                self.image_size_pixels_slow = int(record.split()[-1])
                continue

            if 'Start_angle' in record:
                self.osc_start_deg = float(record.split()[2])
                continue

            if 'Angle_increment' in record:
                self.osc_width_deg = float(record.split()[2])
                continue

            if 'Count_cutoff' in record:
                self.maximum_value = int(record.split()[2])
                continue

        self.image_offset = 0
        self.pixel_depth_bytes = 4
        self.angle_twotheta_deg = 0.0
        self.angle_kappa_deg = 0.0
        self.angle_chi_deg = 0.0

        return

if __name__ == '__main__':

    import sys

    for arg in sys.argv[1:]:
        print ReadHeaderPILATUSMiniCBF(arg)
