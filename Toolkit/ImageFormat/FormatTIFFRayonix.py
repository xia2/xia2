#!/usr/bin/env python
# FormatTIFFRayonix.py
#   Copyright (C) 2011 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# An implementation of the TIFF image reader for Rayonix images. Inherits from
# FormatTIFF.

import time
import struct

from FormatTIFF import FormatTIFF

class FormatTIFFRayonix(FormatTIFF):
    '''A class for reading TIFF format Rayonix images, and correctly constructing
    a model for the experiment from this.'''

    @staticmethod
    def understand(image_file):
        '''Check to see if this looks like an Rayonix TIFF format image,
        i.e. we can make sense of it.'''

        if FormatTIFF.understand(image_file) == 0:
            return 0

        width, height, depth, order, bytes = FormatTIFF.get_tiff_header(
            image_file)

        assert(len(bytes) == 4096)

        if order == FormatTIFF.LITTLE_ENDIAN:
            _width = struct.unpack('<I', bytes[1024 + 80:1024 + 84])[0]
            _height = struct.unpack('<I', bytes[1024 + 84:1024 + 88])[0]
            _depth = struct.unpack('<I', bytes[1024 + 88:1024 + 92])[0]
        else:
            _width = struct.unpack('>I', bytes[1024 + 80:1024 + 84])[0]
            _height = struct.unpack('>I', bytes[1024 + 84:1024 + 88])[0]
            _depth = struct.unpack('>I', bytes[1024 + 88:1024 + 92])[0]

        if width != _width or height != _height or depth != _depth:
            return 0

        if order == FormatTIFF.LITTLE_ENDIAN:
            nimages = struct.unpack('<I', bytes[1024 + 112:1024 + 116])[0]
            origin = struct.unpack('<I', bytes[1024 + 116:1024 + 120])[0]
            orientation = struct.unpack('<I', bytes[1024 + 120:1024 + 124])[0]
            view = struct.unpack('<I', bytes[1024 + 124:1024 + 128])[0]
        else:
            nimages = struct.unpack('>I', bytes[1024 + 112:1024 + 116])[0]
            origin = struct.unpack('>I', bytes[1024 + 116:1024 + 120])[0]
            orientation = struct.unpack('>I', bytes[1024 + 120:1024 + 124])[0]
            view = struct.unpack('>I', bytes[1024 + 124:1024 + 128])[0]

        if nimages != 1 or origin != 0 or orientation != 0 or view != 0:
            return 0

        return 2

    def __init__(self, image_file):
        '''Initialise the image structure from the given file, including a
        proper model of the experiment.'''

        assert(FormatTIFFRayonix.understand(image_file) > 0)
        
        FormatTIFF.__init__(self, image_file)

        return

    # FIXME have implemented none of those which follow...
    
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
        '''Return the scan information for this image.'''

        format = self._xscan_factory.Format('TIFF') 
        time = float(self._header_dictionary['TIME'])
        epoch =  time.mktime(time.strptime(self._header_dictionary['DATE']))
        osc_start = float(self._header_dictionary['OSC_START'])
        osc_range = float(self._header_dictionary['OSC_RANGE'])

        return self._xscan_factory.Single(
            self._image_file, format, time, osc_start, osc_range, epoch)

if __name__ == '__main__':

    import sys

    for arg in sys.argv[1:]:
        print FormatTIFFRayonix.understand(arg)
