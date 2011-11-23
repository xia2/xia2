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

        return

    def get(self, parameter, convention = CBF):

        parameter_value = self._coordinate_frame_information.get(parameter)

        if convention == coordinate_frame_converter.CBF:
            if hasattr(parameter_value, 'elems'):
                return parameter_value.elems
            else:
                return parameter_value
        else:
            raise RuntimeError, 'convention %s not currently supported'

        return 

    def derive_beam_centre_pixels_fast_slow(self):
        '''Derive the pixel position at which the direct beam would intersect
        with the detector plane, and return this in terms of fast and slow.'''
        
        cfi = self._coordinate_frame_information

        detector_origin = cfi.get('detector_origin')
        detector_fast = cfi.get('detector_fast')
        detector_slow = cfi.get('detector_slow')
        sample_to_source = cfi.get('sample_to_source')
        pixel_size_fast, pixel_size_slow = cfi.get(
            'detector_pixel_size_fast_slow')

        detector_normal = detector_fast.cross(detector_slow)

        if not sample_to_source.dot(detector_normal):
            raise RuntimeError, 'beam parallel to detector'

        distance = detector_origin.dot(detector_normal)

        sample_to_detector = sample_to_source * distance / \
                             sample_to_source.dot(detector_normal)

        beam_centre = sample_to_detector - detector_origin

        beam_centre_fast_mm = beam_centre.dot(detector_fast)
        beam_centre_slow_mm = beam_centre.dot(detector_slow)

        return beam_centre_fast_mm / pixel_size_fast, \
               beam_centre_slow_mm / pixel_size_slow 
        
    def __str__(self):

        return '\n'.join([
            'detector origin: %.3f %.3f %.3f' % self.get('detector_origin'),
            'detector fast: %6.3f %6.3f %6.3f' % self.get('detector_fast'),
            'detector slow: %6.3f %6.3f %6.3f' % self.get('detector_slow'),
            'rotation axis: %6.3f %6.3f %6.3f' % self.get('rotation_axis'),
            '- s0 vector:   %6.3f %6.3f %6.3f' % self.get('sample_to_source')
            ])

if __name__ == '__main__':

    if len(sys.argv) < 2:
        raise RuntimeError, '%s configuration-file' % sys.argv[0]
    
    configuration_file = sys.argv[1]

    cfc = coordinate_frame_converter(configuration_file)

    print cfc
    
