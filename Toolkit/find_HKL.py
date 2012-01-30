#!/usr/bin/env cctbx.python
# find_HKL.py
#
# An illustration of how to use cctbx code with imgCIF / cbf files, through
# the pycbf API now included in cctbx. N.B. this does require some coordinate
# frame changes (see below) and should work with the files from a Pilatus
# 300K instrument collected during commissioning on I19 as ximg2701_00001.cbf.

from scitbx import matrix
import math
import sys
import os
import pycbf
from rstbx.diffraction import rotation_angles
from scitbx.math import r3_rotation_axis_and_angle_from_matrix

# This was the known UB matrix, taken from XDS processing.

UB = matrix.sqr([0.0144873, -0.0128813, -0.0002988,
                 -0.0128113, -0.0143530, -0.0024004,
                 0.0013736, 0.0019910, -0.0192366])

# And this is a target reflection we are trying to find (which we know where
# it is) on this image.

hkl = (-17, -10, 9)

# This is a "bodge" i.e. additional code needed to establish what the rotation
# axis is from the setting matrix at the end and start of the image. N.B. this
# should be mended in the pycbf API. N.B. also that this is not I think used
# below...

def determine_effective_scan_axis(gonio):
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

    return rot.axis, rot.angle(deg = True)

# Why doesn't Python include a basic nearest integer?!

def nint(a):
    return int(round(a) - 0.5) + (a > 0)

def find_HKL(cbf_image):

    # construct and link a cbf_handle to the image itself.
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

    real_axis, real_angle = determine_effective_scan_axis(gonio)

    axis = tuple(gonio.get_rotation_axis())
    angles = tuple(gonio.get_rotation_range())

    # this method returns slow then fast dimensions i.e. (y, x)

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

    # Need to rotate into Rossmann reference frame for phi calculation, as
    # that's code from Labelit :o(

    RB = matrix.col([0, 0, 1])

    if B.angle(RB) % math.pi:
        RtoR = RB.cross(R).axis_and_angle_as_r3_rotation_matrix(
            RB.angle(R))
    elif B.angle(RB):
        RtoR = matrix.sqr((1, 0, 0, 0, -1, 0, 0, 0, -1))
    else:
        RtoR = matrix.sqr((1, 0, 0, 0, 1, 0, 0, 0, 1))

    Raxis = RtoR * axis
    RUB = RtoR * UB

    RA = rotation_angles(wavelength, RUB, wavelength, Raxis)

    assert(RA(hkl))

    omegas = [180.0 / math.pi * a for a in RA.get_intersection_angles()]

    print '%.2f %.2f' % tuple(omegas)

    for omega in omegas:

        R = matrix.col(axis).axis_and_angle_as_r3_rotation_matrix(
            math.pi * omega / 180.0)

        q = R * UB * hkl

        p = S0 + q

        p_ = p * (1.0 / math.sqrt(p.dot()))
        P = p_ * (O.dot(N) / (p_.dot(N)))

        R = P - O

        i = R.dot(X)
        j = R.dot(Y)
        k = R.dot(N)

        print '%d %d %d %.3f %.3f %.3f %.3f %.3f' % \
              (hkl[0], hkl[1], hkl[2], i, j, omega, i / pixel[0], j / pixel[1])

    # finally, the inverse calculation - given a position on the detector,
    # and omega setting, give the Miller index of the reflection

    i = 193
    j = 267
    w = 42

    # RUBI is (R * UB).inverse()

    RUBI = (matrix.col(axis).axis_and_angle_as_r3_rotation_matrix(
        math.pi * w / 180.0) * UB).inverse()

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
    find_HKL(sys.argv[1])
