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

from XDetectorHelpers import read_xds_xparm
from XDetectorHelpers import compute_frame_rotation

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

    def __repr__(self):
        '''Generate a useful-to-print representation.'''

        f_3 = '%6.3f %6.3f %6.3f\n'

        return f_3 % self._origin.elems + f_3 % self._fast.elems + \
               f_3 % self._slow.elems

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
    def Simple(distance, beam_centre, fast_direction, slow_direction,
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

    @staticmethod
    def TwoTheta(distance, beam_centre, fast_direction, slow_direction,
                 two_theta_direction, two_theta_angle,
                 pixel_size, image_size, overload, mask):
        '''Construct a simple detector at a given distance from the sample
        along the direct beam presumed to be aligned with -z, offset by the
        beam centre - the directions of which are given by the fast and slow
        directions, which are themselves given as +x, +y, -x, -y. The pixel
        size is given in mm in the fast and slow directions and the image size
        is given in pixels in the same order. Everything else is the same as
        for the main reference frame. Also given are the direction of the
        two-theta axis and the angle in degrees by which the detector is
        moved.'''

        assert(fast_direction in ['-x', '+y', '+x', '-y'])
        assert(slow_direction in ['-x', '+y', '+x', '-y'])
        assert(two_theta_direction in ['-x', '+y', '+x', '-y'])

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

        two_theta = matrix.col(direction_map[two_theta_direction])

        R = two_theta.axis_and_angle_as_r3_rotation_matrix(two_theta_angle,
                                                           deg = True)

        return XDetector((R * origin).elems, (R * fast).elems,
                         (R * slow).elems, pixel_size, image_size,
                         overload, mask)

    @staticmethod
    def Complex(origin, fast, slow, pixel, size, overload):
        '''A complex detector model, where you know exactly where everything
        is. This is useful for implementation of the Rigaku Saturn header
        format, as that is exactly what is in there. Origin, fast and slow are
        vectors in the CBF reference frame, pixel is the dimensions as a tuple
        as is size.'''

        assert(len(origin) == 3)
        assert(len(fast) == 3)
        assert(len(slow) == 3)
        assert(len(pixel) == 2)
        assert(len(size) == 2)

        return XDetector(origin, fast, slow, pixel,
                         size, overload, [])

    @staticmethod
    def XDS(xds_xparm_file):
        '''Initialize a detector model from an XDS XPARM file, containing
        a refined description from either indexing or postrefinement of a
        single crystal diffraction data set. This method is largely for
        testing and feedback.'''

        xparm_data = read_xds_xparm(xds_xparm_file)

        # fetch out the interesting things that we need

        distance = xparm_data['distance']
        axis = matrix.col(xparm_data['axis'])
        beam = matrix.col(xparm_data['beam'])
        detector_normal = matrix.col(xparm_data['normal'])
        image_size = (xparm_data['nx'], xparm_data['ny'])
        pixel_size = (xparm_data['px'], xparm_data['py'])
        detector_centre = (xparm_data['px'] * xparm_data['ox'],
                           xparm_data['py'] * xparm_data['oy'])
        detector_fast = matrix.col(xparm_data['x'])
        detector_slow = matrix.col(xparm_data['y'])

        # compute the detector origin

        origin_xds = distance * detector_normal
        origin = origin_xds - (detector_centre[0] * detector_fast +
                               detector_centre[1] * detector_slow)

        # then convert directions to unit vectors

        axis = axis / math.sqrt(axis.dot())
        beam = beam / math.sqrt(beam.dot())

        # want to now calculate a rotation which will align the axis with
        # the (1, 0, 0) vector, and the component of the beam vector
        # perpendicular to this with (0, 0, 1) - for convenience then start
        # by defining our current reference frame

        x = axis
        z = beam - (beam.dot(axis) * axis)
        z = z / math.sqrt(z.dot())
        y = z.cross(x)
        
        # and the target reference frame
        
        _x = matrix.col([1, 0, 0])
        _y = matrix.col([0, 1, 0])
        _z = matrix.col([0, 0, 1])

        # now compute the rotations which need to be applied to move from

        _m = compute_frame_rotation((x, y, z), (_x, _y, _z))

        # rotate all of the parameters from the XDS to CBF coordinate frame

        c_origin = _m * origin
        c_axis = _m * axis
        c_beam = _m * beam
        c_fast = _m * detector_fast
        c_slow = _m * detector_slow

        return XDetector(c_origin, c_fast, c_slow, pixel_size,
                         image_size, 0, [])

    @staticmethod
    def imgCIF(cif_file):
        '''Initialize a detector model from an imgCIF file.'''

        cbf_handle = pycbf.cbf_handle_struct()
        cbf_handle.read_file(cif_file, pycbf.MSG_DIGEST)

        detector = cbf_handle.construct_detector(0)
        
        pixel = (detector.get_inferred_pixel_size(1),
                 detector.get_inferred_pixel_size(2))

        # FIXME can probably simplify the code which follows below by
        # making proper use of cctbx vector calls - should not be as
        # complex as it appears to be...

        origin = detector.get_pixel_coordinates(0, 0)
        fast = detector.get_pixel_coordinates(0, 1)
        slow = detector.get_pixel_coordinates(1, 0)
        
        dfast = [fast[j] - origin[j] for j in range(3)]
        dslow = [slow[j] - origin[j] for j in range(3)]
        
        lfast = math.sqrt(sum([dfast[j] * dfast[j] for j in range(3)]))
        lslow = math.sqrt(sum([dslow[j] * dslow[j] for j in range(3)]))
        
        fast = tuple([dfast[j] / lfast for j in range(3)])
        slow = tuple([dslow[j] / lslow for j in range(3)])

        size = tuple(reversed(cbf_handle.get_image_size(0)))
        overload = cbf_handle.get_overload(0)

        detector.__swig_destroy__(detector)
        del(detector)

        return XDetector(origin, fast, slow, pixel,
                         size, overload, [])


    @staticmethod
    def imgCIF_H(cbf_handle):
        '''Initialize a detector model from an imgCIF file handle, where it
        is assumed that the file has already been read.'''

        detector = cbf_handle.construct_detector(0)
        
        pixel = (detector.get_inferred_pixel_size(1),
                 detector.get_inferred_pixel_size(2))

        # FIXME can probably simplify the code which follows below by
        # making proper use of cctbx vector calls - should not be as
        # complex as it appears to be...

        origin = detector.get_pixel_coordinates(0, 0)
        fast = detector.get_pixel_coordinates(0, 1)
        slow = detector.get_pixel_coordinates(1, 0)
        
        dfast = [fast[j] - origin[j] for j in range(3)]
        dslow = [slow[j] - origin[j] for j in range(3)]
        
        lfast = math.sqrt(sum([dfast[j] * dfast[j] for j in range(3)]))
        lslow = math.sqrt(sum([dslow[j] * dslow[j] for j in range(3)]))
        
        fast = tuple([dfast[j] / lfast for j in range(3)])
        slow = tuple([dslow[j] / lslow for j in range(3)])

        size = tuple(reversed(cbf_handle.get_image_size(0)))
        overload = cbf_handle.get_overload(0)

        detector.__swig_destroy__(detector)
        del(detector)

        return XDetector(origin, fast, slow, pixel,
                         size, overload, [])


        
    
        
