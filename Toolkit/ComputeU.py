#!/usr/bin/env python
#
# Some calculations for generating U matrices &c. for I16 multiple scattering
# calculations.
# 

from cctbx.uctbx import unit_cell 
from scitbx import matrix
import math
import sys

# some handy constants

a2kev = 12.39854
r2d = 180.0 / math.pi

def busing_levy(x1, x2, rx1, rx2):
    '''Compute an orientation matrix U which will rotate x1 to rx1 and
    x2 into rx2 (approximately) according to the method in Busing & Levy
    1967.'''

    # first compute orthonormal basis, from x1, component of x2 normal to x1
    # and the cross product of these...

    e1 = x1.normalize()
    e2 = (x2 - (e1 * x2.dot(e1))).normalize()
    e3 = e1.cross(e2)

    # now compute the rotated basis

    r1 = rx1.normalize()
    r2 = (rx2 - (r1 * rx2.dot(e1))).normalize()
    r3 = r1.cross(r2)

    # now compose a matrix from these

    E = matrix.sqr((e1.elems + e2.elems + e3.elems))
    R = matrix.sqr((r1.elems + r2.elems + r3.elems))

    U = R * (E.inverse())

    return U

def compute_reciprocal_positions(unit_cell_constants, energy_kev,
                                 roi, azi):
    '''Given a set of unit cell constants, an energy, a reflection-of-interest
    which we know to be in reflecting position and an azimuthal reflection,
    compute a [A] = [U][B] matrix.'''

    # initial conversions
    wavelength = a2kev / energy_kev    

    uc = unit_cell(unit_cell_constants)

    ruc = uc.reciprocal()

    B = matrix.sqr(ruc.orthogonalization_matrix())

    _roi = B * roi
    _azi = B * azi

    _roi_l = math.sqrt(_roi.dot())
    _azi_l = math.sqrt(_azi.dot())

    theta = math.asin(wavelength * _roi_l / 2)

    d_theta = _roi.angle(_azi)

    # compute known positions of rotated reciprocal space positions

    r_roi = matrix.col([- _roi_l * math.sin(theta), 0,
                        _roi_l * math.cos(theta)])

    r_azi = matrix.col([_azi_l * math.sin(d_theta - theta), 0,
                        _azi_l * math.cos(d_theta - theta)])

    U = busing_levy(_roi, _azi, r_roi, r_azi)

    return U * B

if __name__ == '__main__':

    unit_cell_constants = (3.573, 3.573, 5.643, 90, 90, 120)
    energy_kev = 5.993

    roi = (0, 0, 4)
    azi = (0, 1, 0)

    A = compute_reciprocal_positions(unit_cell_constants, energy_kev,
                                     roi, azi)

    print A
