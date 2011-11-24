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

from cftbx.coordinate_frame_converter import coordinate_frame_converter
from rstbx.diffraction import rotation_angles
from cctbx.sgtbx import space_group
from cctbx.uctbx import unit_cell 

def generate_indices(unit_cell_constants, resolution_limit):
    '''Generate all possible reflection indices out to a given resolution
    limit, ignoring symmetry and centring.'''

    uc = unit_cell(unit_cell_constants)

    maxh, maxk, maxl = uc.max_miller_indices(dmin)

    indices = []
    
    for h in range(-maxh, maxh + 1):
        for k in range(-maxk, maxk + 1):
            for l in range(-maxl, maxl + 1):

                if h == 0 and k == 0 and l == 0:
                    continue
                
                if uc.d((h, k, l)) < dmin:
                    continue

                indices.append((h, k, l))

    return indices


    
