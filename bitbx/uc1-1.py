#!/usr/bin/env cctbx.python
# 
# Biostruct-X Data Reduction Use Case 1.1:
# 
# Given UB matrix, centring operation, generate a list of predictions as 
# H K L x y phi. Also requires (clearly) a model for the detector positions
# and the crystal lattice type. Alternatively (and simpler) assume lattice
# is P1 and ignore centring.
#
# Requires:
#
# Determine maximum resolution limit.
# Generate full list of reflections to given resolution limit.
# Compute intersection angles for all reflections given UB matrix etc.
# Determine which of those will be recorded on the detector.

import os
import sys
import math

sys.path.append(os.environ['XIA2_ROOT'])

from cftbx.coordinate_frame_converter import coordinate_frame_converter
from rstbx.diffraction import rotation_angles
from cctbx.sgtbx import space_group
from cctbx.uctbx import unit_cell 

def generate_indices(unit_cell_constants, resolution_limit):
    '''Generate all possible reflection indices out to a given resolution
    limit, ignoring symmetry and centring.'''

    uc = unit_cell(unit_cell_constants)

    maxh, maxk, maxl = uc.max_miller_indices(resolution_limit)

    indices = []
    
    for h in range(-maxh, maxh + 1):
        for k in range(-maxk, maxk + 1):
            for l in range(-maxl, maxl + 1):

                if h == 0 and k == 0 and l == 0:
                    continue
                
                if uc.d((h, k, l)) < resolution_limit:
                    continue

                indices.append((h, k, l))

    return indices

def main(configuration_file):
    '''Perform the calculations needed for use case 1.1.'''

    cfc = coordinate_frame_converter(configuration_file)
    resolution = cfc.derive_detector_highest_resolution()

    A = cfc.get_c('real_space_a')
    B = cfc.get_c('real_space_b')
    C = cfc.get_c('real_space_c')

    a = A.length()
    b = B.length()
    c = C.length()
    alpha = B.angle(C, deg = True)
    beta = C.angle(A, deg = True)
    gamma = A.angle(B, deg = True)

    indices = generate_indices((a, b, c, alpha, beta, gamma), resolution)

    u, b = cfc.get_u_b(convention = cfc.ROSSMANN)
    axis = cfc.get('rotation_axis', convention = cfc.ROSSMANN)
    ub = u * b

    wavelength = cfc.get('wavelength')

    # work out which reflections should be observed (i.e. pass through the
    # Ewald sphere)

    ra = rotation_angles(resolution, ub, wavelength, axis)

    observed_reflections = []

    for hkl in indices:
        if ra(hkl):
            for angle in ra.get_intersection_angles():
                observed_reflections.append((hkl, angle))

    for hkl, angle in observed_reflections:
        print '%d %d %d' % hkl, '%.1f' % (180.0  * angle / math.pi)

    # now work out which of these will intersect with the detector, and where

    
    
if __name__ == '__main__':
    main(sys.argv[1])
