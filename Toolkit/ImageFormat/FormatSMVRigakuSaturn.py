#!/usr/bin/env python
# FormatSMVRigakuSaturn.py
#   Copyright (C) 2011 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# An implementation of the SMV image reader for Rigaku Saturn images.
# Inherits from FormatSMV.

from FormatSMV import FormatSMV

class FormatSMVRigakuSaturn(FormatSMV):
    '''A class for reading SMV format Rigaku Saturn images, and correctly
    constructing a model for the experiment from this.'''

    @staticmethod
    def understand(image_file):
        '''Check to see if this looks like a Rigaku Saturn SMV format image,
        i.e. we can make sense of it. Essentially that will be if it contains
        all of the keys we are looking for.'''

        if FormatSMV.understand(image_file) == 0:
            return 0

        size, header = FormatSMV.get_smv_header(image_file)

        wanted_header_items = [
            'DETECTOR_NUMBER', 'DETECTOR_NAMES',
            'CRYSTAL_GONIO_NUM_VALUES', 'CRYSTAL_GONIO_NAMES',
            'CRYSTAL_GONIO_UNITS', 'CRYSTAL_GONIO_VALUES',
            'DTREK_DATE_TIME',
            'ROTATION', 'ROTATION_AXIS_NAME', 'ROTATION_VECTOR',
            'SOURCE_VECTORS', 'SOURCE_WAVELENGTH',
            'SOURCE_POLARZ', 'DIM', 'SIZE1', 'SIZE2',
            ]

        for header_item in wanted_header_items:
            if not header_item in header:
                return 0

        detector_prefix = header['DETECTOR_NAMES'].split()[0].strip()

        more_wanted_header_items = [
            'DETECTOR_DIMENSIONS', 'DETECTOR_SIZE', 'DETECTOR_VECTORS',
            'GONIO_NAMES', 'GONIO_UNITS', 'GONIO_VALUES', 'GONIO_VECTORS',
            'SPATIAL_BEAM_POSITION'
            ]

        for header_item in more_wanted_header_items:
            if not '%s%s' % (detector_prefix, header_item) in header:
                return 0

        return 2

if __name__ == '__main__':

    import sys

    for arg in sys.argv[1:]:
        print FormatSMVRigakuSaturn.understand(arg)
