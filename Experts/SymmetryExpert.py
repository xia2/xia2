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
from scitbx import matrix
from cctbx import sgtbx

if not os.environ.has_key('XIA2_ROOT'):
  raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
  sys.path.append(os.environ['XIA2_ROOT'])

# from Wrappers.XIA.Mat2symop import Mat2symop
# from Wrappers.XIA.Symop2mat import Symop2mat
from Handlers.Syminfo import Syminfo

def gen_rot_mat_euler(alpha, beta, gamma):
  '''Compute a rotation matrix (stored as e11 e12 e13 e22 e23...)
  as product R(x, gamma).R(y, beta).R(z, alpha).'''

  from MatrixExpert import rot_x, rot_y, rot_z

  rz = rot_z(alpha)
  ry = rot_y(beta)
  rx = rot_x(gamma)

  r = _multiply_symmetry_matrix(ry, rz)

  return _multiply_symmetry_matrix(rx, r)

def _multiply_symmetry_matrix(a, b):
  '''compute a * b, for e.g. h_ = a * b * h, e.g. apply b before a.'''

  return (matrix.sqr(a) * matrix.sqr(b)).elems

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

  return (sgtbx.change_of_basis_op(b) * sgtbx.change_of_basis_op(a)).as_hkl()

  #return mat_to_symop(
      #_multiply_symmetry_matrix(symop_to_mat(a), symop_to_mat(b))).strip()

def symop_to_mat(symop):
  #symop = symop.replace('h', 'x').replace('k', 'y').replace('l', 'z')
  return matrix.sqr(sgtbx.change_of_basis_op(
      symop).c().as_double_array()[:9]).elems

def mat_to_symop(mat):
  return sgtbx.change_of_basis_op(sgtbx.rt_mx(
      matrix.sqr(mat), (0, 0, 0),
      r_den = 12, t_den = 144)).as_hkl()

def lattice_to_spacegroup_number(lattice):
  '''Return the spacegroup number corresponding to the lowest symmetry
  possible for a given Bravais lattice.'''

  _lattice_to_spacegroup_number = {'aP':1, 'mP':3, 'mC':5, 'oP':16, 'oC':20,
                                   'oF':22, 'oI':23, 'tP':75, 'tI':79,
                                   'hP':143, 'hR':146, 'cP':195, 'cF':196,
                                   'cI':197}

  if not lattice in _lattice_to_spacegroup_number.keys():
    raise RuntimeError, 'lattice %s unknown' % lattice

  return _lattice_to_spacegroup_number[lattice]

if __name__ == '__main__':

  s = compose_symops('-y,x+y,z', 'h,k,l')
  m = symop_to_mat(s)

  assert(s == mat_to_symop(m))

  s = '-h,-k,h+l'

  m = symop_to_mat(s)

  for i in map(int, m):
    print i,
