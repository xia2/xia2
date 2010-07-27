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

        cif = CifFile.ReadCif(fname)

        os.remove(fname)

        # now pull the information from the image header...

        i1 = cif['image_1']

        pixel_order = tuple(map(int, i1['_array_element_size.index']))
        pixel_dim = tuple(map(float, i1['_array_element_size.size']))
        image_order = tuple(map(int, i1['_array_structure_list.precedence']))
        image_dim = tuple(map(int, i1['_array_structure_list.dimension']))

        assert(image_order in [(1, 2), (2, 1)])

        overload = int(i1['_array_intensities.overload'])

        wavelength = float(i1['_diffrn_radiation_wavelength.wavelength'])
        distance = float(i1['_diffrn_measurement.sample_detector_distance'])
        exposure_time = float(i1['_diffrn_scan_frame.integration_time'])
        # this is YYYY-MM-DDTHH:MM:SS
        date_str = i1['_diffrn_scan_frame.date']

        
        
        if True:
            return
        
        beam_centre_x_mm = float(header['BEAM_CENTER_X'])
        beam_centre_y_mm = float(header['BEAM_CENTER_Y'])
        
        date = header['DATE']

        self.date_struct = time.strptime(date)
        self.epoch_ms = 0

        self.exposure_time_s = float(header['TIME'])
        self.distance_mm = float(header['DISTANCE'])
        self.wavelength_angstroms = float(header['WAVELENGTH'])

        self.pixel_size_mm_fast = pixel_size
        self.pixel_size_mm_slow = pixel_size
        
        self.image_size_pixels_fast = int(header['SIZE1'])
        self.image_size_pixels_slow = int(header['SIZE2'])
        self.pixel_depth_bytes = 2
        
        self.osc_start_deg = float(header['OSC_START'])
        self.osc_width_deg = float(header['OSC_RANGE'])
        self.angle_twotheta_deg = float(header.get('TWOTHETA', '0.0'))
        self.angle_kappa_deg = 0.0
        self.angle_chi_deg = 0.0
        
        self.detector_serial_number = header['DETECTOR_SN']

        self.image_offset = int(header.get('IMAGE_PEDESTAL', '0'))
        self.maximum_value = int(header['CCD_IMAGE_SATURATION'])

        # FIXME this should probably check with the fast and slow directions.

        self.beam_centre_pixels_fast = beam_centre_y_mm / pixel_size
        self.beam_centre_pixels_slow = beam_centre_x_mm / pixel_size

        self.header_length = size

        return


if __name__ == '__main__':

    import sys

    for arg in sys.argv[1:]:
        ReadHeaderCBF(arg)
