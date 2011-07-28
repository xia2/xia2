#!/usr/bin/env python
# FormatCBFMiniPilatus.py
#   Copyright (C) 2011 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# An implementation of the CBF image reader for Pilatus images. Inherits from
# FormatCBFMini.

import time

from Toolkit.ImageFormat.FormatCBFMini import FormatCBFMini
from Toolkit.ImageFormat.FormatCBFMiniPilatusHelpers import \
     get_pilatus_timestamp
from Toolkit.ImageFormat.FormatPilatusHelpers import determine_pilatus_mask

class FormatCBFMiniPilatus(FormatCBFMini):
    '''A class for reading mini CBF format Pilatus images, and correctly
    constructing a model for the experiment from this.'''

    @staticmethod
    def understand(image_file):
        '''Check to see if this looks like an Pilatus mini CBF format image,
        i.e. we can make sense of it.'''

        if FormatCBFMini.understand(image_file) == 0:
            return 0

        header = FormatCBFMini.get_cbf_header(image_file)

        for record in header.split('\n'):
            if '_array_data.header_convention' in record and \
                   'PILATUS' in record:
                return 3
        
        return 0

    def __init__(self, image_file):
        '''Initialise the image structure from the given file, including a
        proper model of the experiment.'''

        assert(FormatCBFMiniPilatus.understand(image_file) > 0)
        
        FormatCBFMini.__init__(self, image_file)

        return
    
    def _xgoniometer(self):
        '''Return a model for a simple single-axis goniometer. This should
        probably be checked against the image header, though for miniCBF
        there are limited options for this.'''

        assert(not 'Phi' in self._cif_header_dictionary)

        return self._xgoniometer_factory.SingleAxis()

    def _xdetector(self):
        '''Return a model for a simple detector, presuming no one has
        one of these on a two-theta stage. Assert that the beam centre is
        provided in the Mosflm coordinate frame.'''

        distance = float(
            self._cif_header_dictionary['Detector_distance'].split()[0])

        beam_xy = self._cif_header_dictionary['Beam_xy'].replace(
            '(', '').replace(')', '').replace(',', '').split()[:2]

        beam_x, beam_y = map(float, beam_xy)

        pixel_xy = self._cif_header_dictionary['Pixel_size'].replace(
            'm', '').replace('x', '').split()

        pixel_x, pixel_y = map(float, pixel_xy)

        nx = int(
            self._cif_header_dictionary['X-Binary-Size-Fastest-Dimension'])
        ny = int(
            self._cif_header_dictionary['X-Binary-Size-Second-Dimension'])

        overload = int(
            self._cif_header_dictionary['Count_cutoff'].split()[0])

        xdetector = self._xdetector_factory.Simple(
            distance * 1000.0, (beam_x * pixel_x * 1000.0,
                                beam_y * pixel_y * 1000.0), '+x', '-y',
            (pixel_x, pixel_y), (nx, ny), overload, [])

        for f0, s0, f1, s1 in determine_pilatus_mask(xdetector):
            xdetector.add_mask(f0, s0, f1, s1)

        return xdetector
        
    def _xbeam(self):
        '''Return a simple model for the beam.'''

        wavelength = float(
            self._cif_header_dictionary['Wavelength'].split()[0])
        
        return self._xbeam_factory.Simple(wavelength)

    def _xscan(self):
        '''Return the scan information for this image.'''

        format = self._xscan_factory.Format('CBF') 

        exposure_time = float(
            self._cif_header_dictionary['Exposure_period'].split()[0])

        osc_start = float(
            self._cif_header_dictionary['Start_angle'].split()[0])
        osc_range = float(
            self._cif_header_dictionary['Angle_increment'].split()[0])

        timestamp = get_pilatus_timestamp(
            self._cif_header_dictionary['timestamp'])

        return self._xscan_factory.Single(
            self._image_file, format, exposure_time,
            osc_start, osc_range, timestamp)

if __name__ == '__main__':

    import sys

    for arg in sys.argv[1:]:
        print FormatCBFMiniPilatus.understand(arg)
