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

from FormatCBFMini import FormatCBFMini

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

        # FIXME IMPLEMENT
        
        return self._xgoniometer_factory.SingleAxis()

    def _xdetector(self):
        '''Return a model for a simple detector, presuming no one has
        one of these on a two-theta stage. Assert that the beam centre is
        provided in the Mosflm coordinate frame.'''

        # FIXME IMPLEMENT
        
        return self._xdetector_factory.Simple(
            distance, (beam_y, beam_x), '+x', '-y', (pixel_size, pixel_size),
            image_size, overload, [])

    def _xbeam(self):
        '''Return a simple model for the beam.'''

        # FIXME IMPLEMENT
        
        return self._xbeam_factory.Simple(wavelength)

    def _xscan(self):
        '''Return the scan information for this image.'''

        # FIXME IMPLEMENT
        format = self._xscan_factory.Format('CBF') 

        return self._xscan_factory.Single(
            self._image_file, format, exposure_time,
            osc_start, osc_range, epoch)

if __name__ == '__main__':

    import sys

    for arg in sys.argv[1:]:
        print FormatCBFADSC.understand(arg)
