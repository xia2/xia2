#!/usr/bin/env python
# SymmetryExpert.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
# 
# 21st May 2007
# 
# A small expert to handle symmetry calculations.
# 

import os
import sys
import math

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Wrappers.XIA.Mat2symop import Mat2symop
from Wrappers.XIA.Symop2mat import Symop2mat

def _gen_rot_mat_x(theta_deg):
    '''Compute a matrix (stored as e11 e12 e13 e22 e23...) for a rotation
    of theta about x. Theta in degrees.'''

    pi = 4.0 * math.atan(1.0)

    d_to_r = pi / 180.0

    theta = theta_deg * d_to_r

    c_t = math.cos(theta)
    s_t = math.sin(theta)

    return [1.0, 0.0, 0.0,
            0.0, c_t, -s_t,
            0.0, s_t, c_t]

def _gen_rot_mat_y(theta_deg):
    '''Compute a matrix (stored as e11 e12 e13 e22 e23...) for a rotation
    of theta about y. Theta in degrees.'''

    pi = 4.0 * math.atan(1.0)

    d_to_r = pi / 180.0

    theta = theta_deg * d_to_r

    c_t = math.cos(theta)
    s_t = math.sin(theta)

    return [c_t, 0.0, s_t,
            0.0, 1.0, 0.0,
            -s_t, 0.0, c_t]

def _gen_rot_mat_z(theta_deg):
    '''Compute a matrix (stored as e11 e12 e13 e22 e23...) for a rotation
    of theta about z. Theta in degrees.'''

    pi = 4.0 * math.atan(1.0)

    d_to_r = pi / 180.0

    theta = theta_deg * d_to_r

    c_t = math.cos(theta)
    s_t = math.sin(theta)

    return [c_t, -s_t, 0.0,
            s_t, c_t, 0.0,
            0.0, 0.0, 1.0]

def gen_rot_mat_euler(alpha, beta, gamma):
    '''Compute a rotation matrix (stored as e11 e12 e13 e22 e23...)
    as product R(x, gamma).R(y, beta).R(z, alpha).'''

    rz = _gen_rot_mat_z(alpha)
    ry = _gen_rot_mat_y(beta)
    rx = _gen_rot_mat_x(gamma)

    r = _multiply_symmetry_matrix(ry, rz)
    return _multiply_symmetry_matrix(rx, r)

def _multiply_symmetry_matrix(a, b):
    '''compute a * b, for e.g. h_ = a * b * h, e.g. apply b before a.'''

    result = []

    result.append(a[0] * b[0] +
                  a[1] * b[3] +
                  a[2] * b[6])

    result.append(a[0] * b[1] +
                  a[1] * b[4] +
                  a[2] * b[7])

    result.append(a[0] * b[2] +
                  a[1] * b[5] +
                  a[2] * b[8])


    result.append(a[3] * b[0] +
                  a[4] * b[3] +
                  a[5] * b[6])

    result.append(a[3] * b[1] +
                  a[4] * b[4] +
                  a[5] * b[7])

    result.append(a[3] * b[2] +
                  a[4] * b[5] +
                  a[5] * b[8])


    result.append(a[6] * b[0] +
                  a[7] * b[3] +
                  a[8] * b[6])

    result.append(a[6] * b[1] +
                  a[7] * b[4] +
                  a[8] * b[7])

    result.append(a[6] * b[2] +
                  a[7] * b[5] +
                  a[8] * b[8])

    return result

def r_to_rt(r):
    '''Convert R matrix to RT, assuming T=0.'''

    result = []
    
    for i in range(3):
        for j in range(3):
            result.append(r[i * 3 + j])
        result.append(0)

    return result

def rt_to_r(rt):
    '''Convert RT matrix to R, removing T.'''

    result = []
    for i in range(3):
        for j in range(3):
            result.append(rt[4 * i + j])

    return result

def compose_matrices_rt(mat_a, mat_b):
    '''Compose symmetry matrix files for XDS. These are 12 element
    matrices...'''
            
    mat_c = _multiply_symmetry_matrix(rt_to_r(mat_a),
                                      rt_to_r(mat_b))

    return r_to_rt(mat_c)

def compose_matrices_r(mat_a, mat_b):
    '''Compose symmetry matrix applying b then a.'''
            
    mat_c = _multiply_symmetry_matrix(mat_a,
                                      mat_b)

    return mat_c

def compose_symops(a, b):
    '''Compose operation c, which is applying b then a.'''

    symop2mat = Symop2mat()
    mat_a = symop2mat.convert(a)
    mat_b = symop2mat.convert(b)

    mat_c = _multiply_symmetry_matrix(mat_a, mat_b)
    mat2symop = Mat2symop()
    return mat2symop.convert(mat_c).strip()

def symop_to_mat(symop):
    symop2mat = Symop2mat()
    return symop2mat.convert(symop)

def lattice_to_spacegroup_number(lattice):
    '''Return the spacegroup number corresponding to the lowest symmetry
    possible for a given Bravais lattice.'''

    _lattice_to_spacegroup_number = {'aP':1,
                                     'mP':3,
                                     'mC':5,
                                     'oP':16,
                                     'oC':20,
                                     'oF':22,
                                     'oI':23,
                                     'tP':75,
                                     'tI':79,
                                     'hP':143,
                                     'hR':146,
                                     'cP':195,
                                     'cF':196,
                                     'cI':197}
    
    if not lattice in _lattice_to_spacegroup_number.keys():
        raise RuntimeError, 'lattice %s unknown' % lattice

    return _lattice_to_spacegroup_number[lattice]
    

if __name__ == '__main__':

    a = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    i = [1, 0, 0, 0, 1, 0, 0, 0, 1]
    j = [0, 1, 0, 0, 0, 1, 1, 0, 0]
    k = [0, 0, 1, 1, 0, 0, 0, 1, 0]

    print compose_symops('h,k,l', 'h,k,l')
    print compose_symops('k,l,h', 'l,h,k')
    print compose_symops('k,l,h', '2h,k,l')

    
