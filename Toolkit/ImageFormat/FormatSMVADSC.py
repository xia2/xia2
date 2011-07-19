#!/usr/bin/env python
# FormatSMVADSC.py
#   Copyright (C) 2011 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# An implementation of the SMV image reader for ADSC images. Inherits from
# FormatSMV.

from FormatSMV import FormatSMV

class FormatSMVADSC(FormatSMV):
    '''A class for reading SMV format ADSC images, and correctly constructing
    a model for the experiment from this.'''

    @staticmethod
    def understand(image_file):
        '''Check to see if this looks like an SMV format image, i.e. we can
        make sense of it. Essentially that will be if it contains all of the
        keys we are looking for and not some we are not (i.e. that belong to
        a Rigaku Saturn.)'''

        if FormatSMV.understand(image_file) == 0:
            return 0

        size, header = FormatSMV.get_smv_header(image_file)

        wanted_header_items = ['BEAM_CENTER_X', 'BEAM_CENTER_Y',
                               'DISTANCE', 'WAVELENGTH', 'PIXEL_SIZE',
                               'OSC_START', 'OSC_RANGE', 'SIZE1', 'SIZE2']

        for header_item in wanted_header_items:
            if not header_item in header:
                return 0

        unwanted_header_items = ['DTREK_DATE_TIME']

        for header_item in unwanted_header_items:
            if header_item in header:
                return 0
        
        return 2

    def __init__(self, image_file):
        '''Initialise the image structure from the given file, including a
        proper model of the experiment.'''

        assert(FormatSMVADSC.understand(image_file) > 0)
        
        FormatSMV.__init__(self, image_file)

        return
    
    def _xgoniometer(self):
        '''Return a model for a simple single-axis goniometer. This should
        probably be checked against the image header.'''
        
        return self._xgoniometer_factory.SingleAxis()

    def _xdetector(self):
        '''Return a model for a simple detector, presuming no one has
        one of these on a two-theta stage. Assert that the beam centre is
        provided in the Mosflm coordinate frame.'''

        distance = float(self._header_dictionary['DISTANCE'])
        beam_x = float(self._header_dictionary['BEAM_CENTER_X'])
        beam_y = float(self._header_dictionary['BEAM_CENTER_Y'])
        pixel_size = float(self._header_dictionary['PIXEL_SIZE'])
        image_size = (float(self._header_dictionary['SIZE1']),
                      float(self._header_dictionary['SIZE2']))
        overload = 65535
        
        return self._xdetector_factory.Simple(
            distance, (beam_y, beam_x), '+x', '-y', (pixel_size, pixel_size),
            image_size, overload, [])

    def _xbeam(self):
        '''Return a simple model for the beam.'''

        wavelength = float(self._header_dictionary['WAVELENGTH'])
        
        return self._xbeam_factory.Simple(wavelength)

    def _xscan(self):

        return self._xscan_factory.Simple()

    
        
        
    
