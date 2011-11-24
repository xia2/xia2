import math
import os
import sys
from scitbx import matrix

class coordinate_frame_information:
    '''A bucket class to store coordinate frame information.'''

    def __init__(self, detector_origin, detector_fast, detector_slow,
                 detector_size_fast_slow, detector_pixel_size_fast_slow,
                 rotation_axis, sample_to_source, wavelength, 
                 real_space_a = None, real_space_b = None,
                 real_space_c = None):
        self._detector_origin = detector_origin
        self._detector_fast = detector_fast
        self._detector_slow = detector_slow
        self._detector_size_fast_slow = detector_size_fast_slow
        self._detector_pixel_size_fast_slow = detector_pixel_size_fast_slow
        self._rotation_axis = rotation_axis
        self._sample_to_source = sample_to_source
        self._wavelength = wavelength
        self._real_space_a = real_space_a
        self._real_space_b = real_space_b
        self._real_space_c = real_space_c
        return

    def get_detector_origin(self):
        return self._detector_origin

    def get_detector_fast(self):
        return self._detector_fast

    def get_detector_slow(self):
        return self._detector_slow

    def get_rotation_axis(self):
        return self._rotation_axis

    def get_sample_to_source(self):
        return self._sample_to_source

    def get_wavelength(self):
        return self._wavelength

    def get_real_space_a(self):
        return self._real_space_a

    def get_real_space_b(self):
        return self._real_space_c

    def get_real_space_c(self):
        return self._real_space_c

    def get(self, parameter_name):
        if not hasattr(self, '_%s' % parameter_name):
            raise RuntimeError, 'no parameter %s' % parameter_name
        return getattr(self, '_%s' % parameter_name)

def align_reference_frame(primary_axis, primary_target,
                          secondary_axis, secondary_target):
    '''Compute a rotation matrix R: R x primary_axis = primary_target and
    R x secondary_axis places the secondary_axis in the plane perpendicular
    to the primary_target, as close as possible to the secondary_target.
    Require: primary_target orthogonal to secondary_target, primary axis
    not colinear with secondary axis.'''

    if type(primary_axis) == type(()) or type(primary_axis) == type([]):
        primary_axis = matrix.col(primary_axis).normalize()
    else:
        primary_axis = primary_axis.normalize()

    if type(primary_target) == type(()) or type(primary_target) == type([]):
        primary_target = matrix.col(primary_target).normalize()
    else:
        primary_target = primary_target.normalize()

    if type(secondary_axis) == type(()) or type(secondary_axis) == type([]):
        secondary_axis = matrix.col(secondary_axis).normalize()
    else:
        secondary_axis = secondary_axis.normalize()

    if type(secondary_target) == type(()) or \
           type(secondary_target) == type([]):
        secondary_target = matrix.col(secondary_target).normalize()
    else:
        secondary_target = secondary_target.normalize()

    # check properties of input axes

    assert(math.fabs(primary_axis.angle(secondary_axis) % math.pi) > 0.001)
    assert(primary_target.dot(secondary_target) < 0.001)

    if primary_target.angle(primary_axis) % math.pi:
        axis_p = primary_target.cross(primary_axis)
        angle_p = - primary_target.angle(primary_axis)
        Rprimary = axis_p.axis_and_angle_as_r3_rotation_matrix(angle_p)
    elif primary_target.angle(primary_axis) < 0:
        axis_p = primary_axis.ortho().normalize()
        angle_p = math.pi
        Rprimary = axis_p.axis_and_angle_as_r3_rotation_matrix(angle_p)
    else:
        Rprimary = matrix.identity(3)

    axis_s = primary_target
    angle_s = - secondary_target.angle(secondary_axis)
    Rsecondary = axis_s.axis_and_angle_as_r3_rotation_matrix(angle_s)

    return Rsecondary * Rprimary
        
def is_xds_xparm(putative_xds_xparm_file):
    '''See if this file looks like an XDS XPARM file i.e. it consists of 42
    floating point values and nothing else.'''
    
    tokens = open(putative_xds_xparm_file).read().split()
    if len(tokens) != 42:
        return False
    try:
        values = map(float, tokens)
    except ValueError, e:
        return False

    return True

def import_xds_xparm(xparm_file):
    '''Read an XDS XPARM file, transform the parameters contained therein
    into the standard coordinate frame, record this as a dictionary.'''

    values = map(float, open(xparm_file).read().split())
    
    assert(len(values) == 42)

    # first determine the rotation R from the XDS coordinate frame used in
    # the processing to the central (i.e. imgCIF) coordinate frame. N.B.
    # if the scan was e.g. a PHI scan the resulting frame could well come out
    # a little odd...

    axis = values[3:6]
    beam = values[7:10]
    x, y = values[17:20], values[20:23]

    # XDS defines the beam vector as s0 rather than from sample -> source.

    B = - matrix.col(beam).normalize()
    A = matrix.col(axis).normalize()
    
    X = matrix.col(x).normalize()
    Y = matrix.col(y).normalize()
    N = X.cross(Y)

    _X = matrix.col([1, 0, 0])
    _Y = matrix.col([0, 1, 0])
    _Z = matrix.col([0, 0, 1])

    R = align_reference_frame(A, _X, B, _Z)

    # now transform contents of the XPARM file to the form which we want to
    # return...

    nx, ny = map(int, values[10:12])
    px, py = values[12:14]

    distance = values[14]
    ox, oy = values[15:17]
    
    a, b, c = values[33:36], values[36:39], values[39:42]

    detector_origin = R * (distance * N - ox * px * X - oy * py * Y)
    detector_fast = R * X
    detector_slow = R * Y
    rotation_axis = R * A
    sample_to_source = R * B
    wavelength = values[6]
    real_space_a = R * matrix.col(a)
    real_space_b = R * matrix.col(b)
    real_space_c = R * matrix.col(c)
    
    return coordinate_frame_information(
        detector_origin, detector_fast, detector_slow, (nx, ny), (px, py),
        rotation_axis, sample_to_source, wavelength,
        real_space_a, real_space_b, real_space_c)
    
def test_align_reference_frame():
    
    _i = (1, 0, 0)
    _j = (0, 1, 0)
    _k = (0, 0, 1)
    
    primary_axis = _i
    primary_target = _i
    secondary_axis = _k
    secondary_target = _k

    m = align_reference_frame(primary_axis, primary_target,
                              secondary_axis, secondary_target)

    i = matrix.identity(3)

    for j in range(9):
        assert(math.fabs(m.elems[j] - i.elems[j]) < 0.001)

    primary_axis = _j
    primary_target = _i
    secondary_axis = _k
    secondary_target = _k

    m = align_reference_frame(primary_axis, primary_target,
                              secondary_axis, secondary_target)

    for j in range(3):
        assert(math.fabs((m * primary_axis).elems[j] - 
                         matrix.col(primary_target).elems[j]) < 0.001)

if __name__ == '__main__':
    test_align_reference_frame()
