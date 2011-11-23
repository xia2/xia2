import math
import os
import sys

from scitbx import matrix

from coordinate_frame_helpers import is_xds_xparm, import_xds_xparm

class coordinate_frame_converter:
    '''A class which is instantiated from a supported file (initially an
    imgCIF image or an XDS XPARM / INTEGRATE.HKL / XDS_ASCII.HKL file) and
    will make available the rotation axis, beam vector, detector position
    and attitude, detector origin, fast and slow directions and so on in
    a range of different program specific coordinate frames.'''

    DTREK = 'd*TREK'
    CBF = 'CBF'
    XDS = 'XDS'

    def __init__(self, configuration_file):
        '''Construct a coordinate frame converter from a configuration file.'''

        if is_xds_xparm(configuration_file):
            self._coordinate_frame_information = import_xds_xparm(
                configuration_file)

        else:
            raise RuntimeError, 'unknown configuration file %s' % \
                  configuration_file

        
        
