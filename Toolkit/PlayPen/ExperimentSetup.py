#!/usr/bin/env cctbx.python
# ExperimentSetup.py
#
#   Copyright (C) 2011 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# A class to wrap a refined model of the experimental geometry, i.e. the
# location and attidude of the rotation axis, detector, any fixed rotation
# axis components (i.e. in addition to the [U][B] matrix, the direction
# of the beam and so forth.

import sys
import pycbf
import math
from scitbx import matrix
from scitbx.math import r3_rotation_axis_and_angle_from_matrix

class ExperimentSetup:
    '''A class to represent the experimental setup for a diffraction experiment
    involving a goniometer, crystal, area detector and so forth. The input
    will allow for refined values for the input of such from either an imgCIF
    image or from previous processing results i.e. an XPARM file.'''

    def __init__(self, cbf_file = None):

        if cbf_file:
            return self._init_cbf(cbf_file)

        # N.B. internally everything will adopt the imgCIF / CBF coordinate
        # frame. That is important - transformations in and out of this
        # should be handled by wrapping classes.

        self._rotation_axis = None
        self._beam = None
        self._detector_origin = None
        self._detector_fast = None
        self._detector_slow = None
        self._wavelength = None
        self._size_fast = None
        self._size_slow = None

        return

    # unit vector defining the rotation axis, in a right handed reference
    # frame

    def set_rotation_axis(self, rotation_axis):
        self._rotation_axis = rotation_axis
        return

    def get_rotation_axis(self):
        return self._rotation_axis

    # unit vector defining the direction of the direct beam

    def set_beam(self, beam):
        self._beam = beam
        return

    def get_beam(self):
        return self._beam

    # vectors in the laboratory frame defining the outer corner of the
    # first pixel on the image, and the fast and slow pixel directions
    # which are vectors of length pixel size in mm.

    def set_detector_origin(self, detector_origin):
        self._detector_origin = detector_origin
        return

    def get_detector_origin(self):
        return self._detector_origin

    def set_detector_fast(self, detector_fast):
        self._detector_fast = detector_fast
        return

    def get_detector_fast(self):
        return self._detector_fast

    def set_detector_slow(self, detector_slow):
        self._detector_slow = detector_slow
        return

    def get_detector_slow(self):
        return self._detector_slow

    # wavelength in Angstroms

    def set_wavelength(self, wavelength):
        self._wavelength = wavelength
        return

    def get_wavelength(self):
        return self._wavelength

    # array dimensions in pixels

    def set_size_fast(self, size_fast):
        self._size_fast = size_fast
        return

    def get_size_fast(self):
        return self._size_fast

    def set_size_slow(self, size_slow):
        self._size_slow = size_slow
        return

    def get_size_slow(self):
        return self._size_slow

    def _init_cbf(self, cbf_file):
        '''Set up the ExperimentSetup using information from the imgCIF header
        of a CBF image.'''

        cbf_handle = pycbf.cbf_handle_struct()
        cbf_handle.read_file(cbf_file, pycbf.MSG_DIGEST)

        # find the true rotation axis
        gonio = cbf_handle.construct_goniometer()
        self.set_rotation_axis(self.determine_effective_scan_axis(gonio))

        # find the direct beam vector - takes a few steps
        cbf_handle.find_category('axis')

        # find record with equipment = source
        cbf_handle.find_column('equipment')
        cbf_handle.find_row('source')

        # then get the vector and offset from this

        beam = []

        for j in range(3):
            cbf_handle.find_column('vector[%d]' % (j + 1))
            beam.append(cbf_handle.get_doublevalue())

        self.set_beam(beam)

        detector = cbf_handle.construct_detector(0)

        # get the vector to the detector origin

        pixel = (detector.get_inferred_pixel_size(1),
                 detector.get_inferred_pixel_size(2))

        origin = detector.get_pixel_coordinates(0, 0)
        fast = detector.get_pixel_coordinates(0, 1)
        slow = detector.get_pixel_coordinates(1, 0)

        dfast = [fast[j] - origin[j] for j in range(3)]
        dslow = [slow[j] - origin[j] for j in range(3)]

        self.set_detector_origin(origin)
        self.set_detector_fast(dfast)
        self.set_detector_slow(dslow)

        self.set_wavelength(cbf_handle.get_wavelength())

        size = tuple(reversed(cbf_handle.get_image_size(0)))

        self.set_size_fast(size[0])
        self.set_size_slow(size[1])

        detector.__swig_destroy__(detector)
        del(detector)

        gonio.__swig_destroy__(gonio)
        del(gonio)

        return

    # helper functions

    def determine_effective_scan_axis(self, gonio):
        '''Determine the effective rotation axis for the goniometer
        by the difference in the rotation matrix from the end of the scan
        and the start. This is then transformed to a rotation.'''

        x = gonio.rotate_vector(0.0, 1, 0, 0)
        y = gonio.rotate_vector(0.0, 0, 1, 0)
        z = gonio.rotate_vector(0.0, 0, 0, 1)

        R = matrix.rec(x + y + z, (3, 3)).transpose()

        x1 = gonio.rotate_vector(1.0, 1, 0, 0)
        y1 = gonio.rotate_vector(1.0, 0, 1, 0)
        z1 = gonio.rotate_vector(1.0, 0, 0, 1)

        R1 = matrix.rec(x1 + y1 + z1, (3, 3)).transpose()

        RA = R1 * R.inverse()

        rot = r3_rotation_axis_and_angle_from_matrix(RA)

        return rot.axis

    def derive_beam_centre_mm_fast_slow(self):
        '''Compute the position on the detector where the beam will actually
        strike the detector - this will be the intersection of the source
        vector with the plane defined by fast and slow passing through the
        detector origin. Then return this position on the detector in mm.

        unit vectors -
         _b - beam
         _n - detector normal
         _f, _s - fast and slow directions on the detector

         full vectors -
         _O - displacement of origin
         _D - displacement to intersection of beam with detector plane
         _B - displacement from origin to said intersection.'''

        beam = matrix.col(self.get_beam())
        fast = matrix.col(self.get_detector_fast())
        slow = matrix.col(self.get_detector_slow())
        origin = matrix.col(self.get_detector_origin())
        normal = fast.cross(slow)

        _b = beam / math.sqrt(beam.dot())

        _n = normal / math.sqrt(normal.dot())
        _f = fast / math.sqrt(fast.dot())
        _s = slow / math.sqrt(slow.dot())

        _O = origin
        _D = _b * (_O.dot(_n) / _b.dot(_n))

        _B = _D - _O

        x = _B.dot(_f)
        y = _B.dot(_s)

        return x, y

if __name__ == '__main__':

    es = ExperimentSetup(cbf_file = sys.argv[1])
    print '%.2f %.2f' % es.derive_beam_centre_mm_fast_slow()
