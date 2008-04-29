#!/usr/bin/env python
# amatrix.py
# 
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
# 
# This is a little jiffy application to compute the dot products of the
# real space (primitive) unit cell edges as a function of phi rotation - 
# I guess from a certain point of view this is a little like a simple
# strategy...
# 
# amatrix file.mat lattice wavelength phi_start phi_width first last
# 

import math
import os
import sys

sys.path.append(os.environ['XIA2_ROOT'])

from Experts.MatrixExpert import mosflm_a_matrix_to_real_space
from Experts.MatrixExpert import dot, rot_x, matvecmul

def compute(matrix, lattice, wavelength, phi_start, phi_width, start, end):
    '''Compute the relative dot products (e.g. cos(p)) between the direct
    beam in the xia2 frame (0, 0, 1) and the primative unit cell axes in
    real space.'''

    a, b, c = mosflm_a_matrix_to_real_space(wavelength, lattice, matrix)

    _a = math.sqrt(dot(a, a))
    _b = math.sqrt(dot(b, b))
    _c = math.sqrt(dot(c, c))

    for j in range(start, end + 1):
        phi = phi_start + (j - start + 0.5) * phi_width
        rot = rot_x(phi)

        aX = matvecmul(rot, a)[2] / _a
        bX = matvecmul(rot, b)[2] / _b
        cX = matvecmul(rot, c)[2] / _c

        print '%.2f %d %.3f %.3f %.3f' % (phi, j, aX, bX, cX)

if __name__ == '__main__':
    if len(sys.argv) == 19:
        
        matrix = ''' -0.00417059 -0.00089426 -0.01139821
 -0.00084328 -0.01388561  0.01379631
 -0.00121258  0.01273236  0.01424531
      -0.099       0.451      -0.013
 -0.94263428 -0.04741397 -0.33044314
 -0.19059871 -0.73622239  0.64934635
 -0.27406719  0.67507666  0.68495023
    228.0796     52.5895     44.1177     90.0000    100.6078     90.0000
     -0.0985      0.4512     -0.0134'''

        compute(matrix, 'mC', 1.0, 0.0, 1.0, 1, 180)

    elif len(sys.argv) == 8:

        # parse command line of:
        # matrix phi_start phi_width start end lattice

        matrix = open(sys.argv[1], 'r').read()
        wavelength = float(sys.argv[2])
        phi_start = float(sys.argv[3])
        phi_width = float(sys.argv[4])
        start = int(sys.argv[5])
        end = int(sys.argv[6])
        lattice = sys.argv[7]

        compute(matrix, lattice, wavelength, phi_start, phi_width, start, end)

    else:

        raise RuntimeError, \
              '%s matrix phi_start phi_width start end lattice' % \
              sys.argv[0]


                 
        
        
        
