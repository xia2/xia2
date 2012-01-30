from scitbx import matrix
import math
import sys
import os
import pycbf
from rstbx.diffraction import rotation_angles
from scitbx.math import r3_rotation_axis_and_angle_from_matrix

UB = matrix.sqr([0.014487300, -0.012881300, -0.000298800,
                 -0.011781711, -0.013425563,  0.007539493,
                 -0.005216078, -0.005452243, -0.017859584])


hkl = (-17, -10, 9)

def get_R(gonio):

    x = gonio.rotate_vector(0.0, 1, 0, 0)
    y = gonio.rotate_vector(0.0, 0, 1, 0)
    z = gonio.rotate_vector(0.0, 0, 0, 1)

    return matrix.rec(x + y + z, (3, 3)).transpose()

def nint(a):
    return int(round(a) - 0.5) + (a > 0)

def small(cbf_image):

    cbf_handle = pycbf.cbf_handle_struct()
    cbf_handle.read_file(cbf_image, pycbf.MSG_DIGEST)

    # get the beam direction
    cbf_handle.find_category('axis')
    cbf_handle.find_column('equipment')
    cbf_handle.find_row('source')

    beam_direction = []

    for j in range(3):
        cbf_handle.find_column('vector[%d]' % (j + 1))
        beam_direction.append(cbf_handle.get_doublevalue())

    B = - matrix.col(beam_direction).normalize()

    detector = cbf_handle.construct_detector(0)

    # this returns slow fast slow fast pixels pixels mm mm

    detector_normal = tuple(detector.get_detector_normal())
    distance = detector.get_detector_distance()
    pixel = (detector.get_inferred_pixel_size(1),
             detector.get_inferred_pixel_size(2))

    gonio = cbf_handle.construct_goniometer()

    R = get_R(gonio)

    size = tuple(reversed(cbf_handle.get_image_size(0)))
    wavelength = cbf_handle.get_wavelength()

    O = matrix.col(detector.get_pixel_coordinates(0, 0))
    fast = matrix.col(detector.get_pixel_coordinates(0, 1))
    slow = matrix.col(detector.get_pixel_coordinates(1, 0))

    X = fast - O
    Y = slow - O

    X = X.normalize()
    Y = Y.normalize()
    N = X.cross(Y)

    S0 = (1.0 / wavelength) * B

    i = 193
    j = 267

    # RUBI is (R * UB).inverse()

    RUBI = (R * UB).inverse()

    p = matrix.col(detector.get_pixel_coordinates(j, i)).normalize()

    q = (1.0 / wavelength) * p - S0

    h, k, l = map(nint, (RUBI * q).elems)

    assert(h == -17)
    assert(k == -10)
    assert(l == 9)

    print h, k, l

    detector.__swig_destroy__(detector)
    del(detector)

    gonio.__swig_destroy__(gonio)
    del(gonio)

if __name__ == '__main__':

    small(sys.argv[1])
