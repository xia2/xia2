#!/usr/bin/env python
# XDetector.py
#   Copyright (C) 2011 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#  
# A model for the detector for the "updated experimental model" project
# documented in internal ticket #1555. This is not designed to be used outside
# of the XSweep classes.

import math
import pycbf
from scitbx import matrix
from scitbx.math import r3_rotation_axis_and_angle_from_matrix

class XDetector:
    '''A class to represent the area detector for a standard rotation geometry
    diffraction experiment. We assume (i) that the detector is flat (ii) that
    the detector is rectangular and (iii) that it is fixed in position for the
    duration of the experiment.'''

    def __init__(self, origin, fast, slow, pixel_size, image_size,
                 overload, mask):
        '''Initialize the detector, with the origin (i.e. the outer corner of
        the zeroth pixel in the image) provided in mm, the fast and slow
        directions provided as unit vectors, the pixel size given as a tuple
        of fast, slow in mm, the image size given as fast, slow in pixels,
        the overload given in counts and the mask given as a list of

        fi, si, fj, sj

        pixel positions marking the extreme limits of the region to be
        excluded in the fast and slow directions.'''

        assert(len(origin) == 3)
        assert(len(fast) == 3)
        assert(len(slow) == 3)
        assert(len(pixel_size) == 2)
        assert(len(image_size) == 2)

        assert(type(mask) == type([]))

        for m in mask:
            assert(len(m) == 4)

        self._origin = matrix.col(origin)
        self._fast = matrix.col(fast)
        self._slow = matrix.col(slow)
        self._pixel_size = pixel_size
        self._image_size = image_size
        self._overload = overload
        self._mask = mask

        return

    def get_origin(self):
        '''Get the detector origin.'''
        
        return self._origin.elems

    def get_origin_c(self):
        '''Get the detector origin as a cctbx vector.'''
        
        return self._origin

    def get_fast(self):
        '''Get the detector fast direction.'''
        
        return self._fast.elems

    def get_fast_c(self):
        '''Get the detector fast direction as a cctbx vector.'''
        
        return self._fast

    def get_slow(self):
        '''Get the detector slow direction.'''
        
        return self._slow.elems

    def get_slow_c(self):
        '''Get the detector slow direction as a cctbx vector.'''
        
        return self._slow

    def get_pixel_size(self):
        '''Get the pixel size in mm, fast direction then slow.'''

        return self._pixel_size

    def get_image_size(self):
        '''Get the image size in pixels, fast direction then slow.'''

        return self._image_size

    def get_overload(self):
        '''Get the number of counts identified as an overloaded pixel.'''

        return self._overload

    def get_mask(self):
        '''Return a list of rectangular regions on the image in pixels which
        should be excluded from measurements.'''

        return self._mask

class XDetectorFactory:
    '''A factory class for XDetector objects, which will encapsulate standard
    detector designs to make it a little easier to get started with these. In
    cases where a CBF image is provided a full description can be used, in
    other cases assumptions will be made about the experiment configuration.
    In all cases information is provided in the CBF coordinate frame.'''

    def __init__(self):
        pass

    @staticmethod
    def SimpleDetector(distance, beam_centre, fast_direction, slow_direction,
                       pixel_size, image_size, overload, mask):
        '''Construct a simple detector at a given distance from the sample
        along the direct beam presumed to be aligned with -z, offset by the
        beam centre - the directions of which are given by the fast and slow
        directions, which are themselves given as +x, +y, -x, -y. The pixel
        size is given in mm in the fast and slow directions and the image size
        is given in pixels in the same order. Everything else is the same as
        for the main reference frame.'''

        assert(fast_direction in ['-x', '+y', '+x', '-y'])
        assert(slow_direction in ['-x', '+y', '+x', '-y'])

        assert(fast_direction[1] != slow_direction[1])

        direction_map = {
            '+x':(1.0, 0.0, 0.0),
            '-x':(-1.0, 0.0, 0.0),
            '+y':(0.0, 1.0, 0.0),
            '-y':(0.0, -1.0, 0.0)
            }

        fast = matrix.col(direction_map[fast_direction])
        slow = matrix.col(direction_map[slow_direction])

        origin = matrix.col((0, 0, -1)) * distance - \
                 fast * beam_centre[0] - slow * beam_centre[1]

        return XDetector(origin.elems, fast.elems, slow.elems, pixel_size,
                         image_size, overload, mask)


    
        
