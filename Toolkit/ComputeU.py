#!/usr/bin/env python
#
# Some calculations for generating U matrices &c. for I16 multiple scattering
# calculations. Then computing the full list of reflections, the psi angles
# where they will be in reflecting position and the double-bounces which add
# up to the absent reflection.

from cctbx.sgtbx import space_group
from cctbx.sgtbx import space_group_symbols
from cctbx.uctbx import unit_cell 
from scitbx import matrix
from rstbx.diffraction import rotation_angles
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

    E = matrix.sqr((e1.elems + e2.elems + e3.elems)).transpose()
    R = matrix.sqr((r1.elems + r2.elems + r3.elems)).transpose()

    U = R * (E.inverse())

    return U

def compute_UB_matrix(unit_cell_constants, energy_kev, roi, azi):
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

def generate_indices(unit_cell_constants, dmin):
    '''For this unit cell, compute all possible Miller indices up to the
    limit dmin.'''

    uc = unit_cell(unit_cell_constants)

    maxh, maxk, maxl = uc.max_miller_indices(dmin)

    indices = []
    
    for h in range(-maxh, maxh + 1):
        for k in range(-maxk, maxk + 1):
            for l in range(-maxl, maxl + 1):

                # ignore reflection (0, 0, 0)
                if h == 0 and k == 0 and l == 0:
                    continue
                
                if uc.d((h, k, l)) < dmin:
                    continue

                # ok, then store
                indices.append((h, k, l))

    return indices

def remove_absences(indices, space_group_name):
    '''Return a list of reflections which will not be absent in the
    given spacegroup.'''

    present_indices = []

    sg = space_group(space_group_symbols(space_group_name).hall())

    for hkl in indices:
        if not sg.is_sys_absent(hkl):
            present_indices.append(hkl)

    return present_indices

def compute_psi(indices, rotation_axis, UB_matrix, wavelength, dmin):
    '''For each reflection, return the psi-angle of rotation about the
    given axis where it will be in reflecting position. N.B. in each
    case there will be 0, 1 or 2, in which case there will be a corresponding
    number of copies.'''

    ra = rotation_angles(dmin, UB_matrix, wavelength, rotation_axis)

    psi_indices = { }

    for hkl in indices:
        if ra(hkl):
            psi_indices[hkl] = ra.get_intersection_angles()

    return psi_indices

def test_psi_angles(roi, psi_indices):
    '''Test when two reflections are in reflecting position whos indices
    add to the reflection of interest. In first pass, allow for being within
    one degree of each other.'''
    
    for hkl in psi_indices:
        second = (roi[0] - hkl[0], roi[1] - hkl[1], roi[2] - hkl[2])
        
        if not second in psi_indices:
            continue

        for psi_test in psi_indices[hkl]:
            for psi_second in psi_indices[second]:
                if math.fabs(r2d * psi_second - r2d * psi_test) < 1.0:
                    print hkl, second, r2d * psi_test, r2d * psi_second
                
if __name__ == '__main__':

    unit_cell_constants = (3.573, 3.573, 5.643, 90, 90, 120)
    energy_kev = 5.993 

    roi = (0, 0, 4)
    azi = (0, 1, 0)

    A = compute_UB_matrix(unit_cell_constants, energy_kev, roi, azi)

    wavelength = a2kev / energy_kev
    dmin = 0.5 * wavelength

    indices = generate_indices(unit_cell_constants, dmin)

    psi_indices = compute_psi(indices, A * roi, A, wavelength, dmin)

    test_psi_angles(roi, psi_indices)
