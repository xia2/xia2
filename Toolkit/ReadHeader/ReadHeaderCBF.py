#!/usr/bin/env cctbx.python
# ReadHeaderCBF.py
#
#   Copyright (C) 2010 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Code to read an ADXV image header and populate the contents of the standard
# image header ReadHeader class.

from ReadHeader import ReadHeader

import tempfile
import time
import os

from PyCifRW import CifFile

class ReadHeaderCBF(ReadHeader):
    '''A class to read CBF image headers. N.B. to work around features of the
    PyCIFRW library, will first read the file into memory and dumo out
    just the header text (i.e. everything to the first binary block.)'''

    def __init__(self, image = None):
        ReadHeader.__init__(self)

        if image:
            self._read_cbf_header(image)

        return

    def _read_cbf_header(self, image):
        '''Read the contents of the header of this image.'''

        # first copy to a temporary directory only the header information

        t = time.time()

        image_data = open(image, 'rb').read()
        header_text = image_data[:image_data.index('_array_data.array_id')]

        fid, fname = tempfile.mkstemp()
        fout = os.fdopen(fid, 'wb')
        fout.write(header_text)
        fout.close()

        # N.B. file:/ needed in here so as not to confuse the urllib on
        # windows systems
        if os.name == 'nt':
            cif = CifFile.ReadCif('file:/%s' % fname)
        else:
            cif = CifFile.ReadCif(fname)

        print cif

        os.remove(fname)

        # now pull the information from the image header...

        i1 = cif['image_1']

        pixel_order = tuple(map(int, i1['_array_element_size.index']))
        pixel_dim = tuple(map(float, i1['_array_element_size.size']))
        image_order = tuple(map(int, i1['_array_structure_list.precedence']))
        image_dim = tuple(map(int, i1['_array_structure_list.dimension']))

        # assume for the moment that this is fast, slow
        assert(image_order in [(1, 2), (2, 1)])

        overload = int(i1['_array_intensities.overload'])

        wavelength = float(i1['_diffrn_radiation_wavelength.wavelength'])
        distance = float(i1['_diffrn_measurement.sample_detector_distance'])
        exposure_time = float(i1['_diffrn_scan_frame.integration_time'])
        # this is YYYY-MM-DDTHH:MM:SS
        date_str = i1['_diffrn_scan_frame.date']

        scan_names = i1['_diffrn_scan_axis.axis_id']
        idx = scan_names.index('GONIOMETER_PHI')
        angle_start = float(i1['_diffrn_scan_axis.angle_start'][idx])
        angle_width = float(i1['_diffrn_scan_axis.angle_increment'][idx])

        serial = i1['_diffrn_detector.id']

        # begin hacky mess to get the beam centre out...
        axis_names = i1['_axis.id']
        idx = axis_names.index('ELEMENT_X')
        beam_centre_x_mm = -1 * float(i1['_axis.offset[1]'][idx])
        beam_centre_y_mm = float(i1['_axis.offset[2]'][idx])

        self.date_struct = time.strptime(date_str, '%Y-%m-%dT%H:%M:%S')
        self.epoch_ms = 0

        self.exposure_time_s = exposure_time
        self.distance_mm = distance
        self.wavelength_angstroms = wavelength

        # these were in m - why?!
        self.pixel_size_mm_fast = 1000 * pixel_dim[0]
        self.pixel_size_mm_slow = 1000 * pixel_dim[1]

        self.image_size_pixels_fast = image_dim[0]
        self.image_size_pixels_slow = image_dim[1]
        self.pixel_depth_bytes = 2

        self.osc_start_deg = angle_start
        self.osc_width_deg = angle_width
        self.angle_twotheta_deg = 0.0
        self.angle_kappa_deg = 0.0
        self.angle_chi_deg = 0.0

        self.detector_serial_number = serial

        self.image_offset = 0
        self.maximum_value = 65535

        # FIXME this should probably check with the fast and slow directions.

        self.beam_centre_pixels_fast = beam_centre_y_mm / (1000 * pixel_dim[1])
        self.beam_centre_pixels_slow = beam_centre_x_mm / (1000 * pixel_dim[0])

        self.header_length = 0

        return


if __name__ == '__main__':

    import sys

    for arg in sys.argv[1:]:
        print ReadHeaderCBF(arg)
