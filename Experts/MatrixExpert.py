#!/usr/bin/env python
# MatrixExpert.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
# 
# 24th July 2007
# 
# A small expert to handle orientation matrix calculations.
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

from Experts.SymmetryExpert import symop_to_mat
from Wrappers.CCP4.Othercell import Othercell

# jiffies to convert matrix format (messy)

def mat2vec(mat):
    return [[mat[0], mat[3], mat[6]],
            [mat[1], mat[4], mat[7]],
            [mat[2], mat[5], mat[8]]]

def vec2mat(vectors):
    return [vectors[0][0], vectors[1][0], vectors[2][0],
            vectors[0][1], vectors[1][1], vectors[2][1],
            vectors[0][2], vectors[1][2], vectors[2][2]]

# generic mathematical calculations for 3-vectors

def rot_y(theta):
    '''Rotation matrix about Y of theta degrees.'''

    dtor = 180.0 / (4.0 * math.atan(1.0))

    c = math.cos(theta / dtor)
    s = math.sin(theta / dtor)

    return [c, 0.0, s, 0.0, 1.0, 0.0, -s, 0.0, c]

def dot(a, b):
    return sum([a[j] * b[j] for j in range(3)])

def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0]]

def vecscl(vector, scale):
    return [vector[j] * scale for j in range(len(vector))]

def invert(matrix):
    vecs = mat2vec(matrix)
    scl = 1.0 / dot(vecs[0], cross(vecs[1], vecs[2]))

    return transpose(
        vec2mat([vecscl(cross(vecs[1], vecs[2]), scl),
                 vecscl(cross(vecs[2], vecs[0]), scl),
                 vecscl(cross(vecs[0], vecs[1]), scl)]))

def transpose(matrix):
    return [matrix[0], matrix[3], matrix[6],
            matrix[1], matrix[4], matrix[7],
            matrix[2], matrix[5], matrix[8]]
            
def det(matrix):
    vecs = mat2vec(matrix)
    return dot(vecs[0], cross(vecs[1], vecs[2]))
    

def matmul(b, a):
    avec = mat2vec(transpose(a))
    bvec = mat2vec(b)

    result = []
    for i in range(3):
        for j in range(3):
            result.append(dot(avec[i], bvec[j]))

    return result

# things specific to mosflm matrix files...

def parse_matrix(matrix_text):
    '''Parse a matrix returning cell, a and u matrix.'''

    # this will need to be able to cope with the times
    # when the matrix includes columns merging together
    # (which sucks)

    # therefore parse this manually... or just add
    # a space before all '-'

    tokens = map(float, matrix_text.replace('-', ' -').split())

    cell = tokens[21:27]
    a = tokens[0:9]
    u = tokens[12:21]

    return cell, a, u

def format_matrix(cell, a, u):
    matrix_format = ' %11.8f %11.8f %11.8f\n' + \
                    ' %11.8f %11.8f %11.8f\n' + \
                    ' %11.8f %11.8f %11.8f\n'
    
    cell_format = ' %11.4f %11.4f %11.4f %11.4f %11.4f %11.4f\n'
    
    misset = '       0.000       0.000       0.000\n'

    return matrix_format % tuple(a) + misset + matrix_format % tuple(u) + \
           cell_format % tuple(cell) + misset

def transmogrify_matrix(lattice, matrix, target_lattice):
    '''Transmogrify a matrix for lattice X into a matrix for lattice
    Y. This should work find for Mosflm... Will also return the new
    unit cell.'''

    cell, a, u = parse_matrix(matrix)

    o = Othercell()
    o.set_cell(cell)
    o.set_lattice(lattice[1].lower())
    o.generate()

    new_cell = o.get_cell(target_lattice)
    op = symop_to_mat(o.get_reindex_op(target_lattice))

    a = matmul(invert(op), a)
    u = matmul(op, u)

    return format_matrix(new_cell, a, u)
    
def get_real_space_primitive_matrix(lattice, matrix):
    '''Get the primitive real space vectors for the unit cell and
    lattice type. Note that the resulting matrix will need to be
    scaled by a factor equal to the wavelength in Angstroms.'''

    # parse the orientation matrix 
    
    cell, a, u = parse_matrix(matrix)

    # generate other possibilities

    o = Othercell()
    o.set_cell(cell)
    o.set_lattice(lattice[1].lower())
    o.generate()

    # transform the possibly centred cell to the primitive setting

    new_cell = o.get_cell('aP')
    op = symop_to_mat(o.get_reindex_op('aP'))

    primitive_a = matmul(invert(op), a)

    # then convert to real space

    real_a = invert(primitive_a)

    return real_a[0:3], real_a[3:6], real_a[6:9]

def get_reciprocal_space_primitive_matrix(lattice, matrix):
    '''Get the primitive reciprocal space vectors for this matrix.'''

    # parse the orientation matrix 
    
    cell, a, u = parse_matrix(matrix)

    # generate other possibilities

    o = Othercell()
    o.set_cell(cell)
    o.set_lattice(lattice[1].lower())
    o.generate()

    # transform the possibly centred cell to the primitive setting

    new_cell = o.get_cell('aP')
    op = symop_to_mat(o.get_reindex_op('aP'))

    primitive_a = matmul(invert(op), a)

    return mat2vec(primitive_a)

def find_primitive_axes(lattice, matrix):
    '''From an orientation matrix file, calculate the angles (phi) where
    the primitive cell axes a, b, c are in the plane of the detector
    (that is, orthogonal to the direct beam vector.'''

    a, b, c = get_real_space_primitive_matrix(lattice, matrix)

    dtor = 180.0 / (4.0 * math.atan(1.0))

    return (dtor * math.atan( - a[2] / a[0]), \
            dtor * math.atan( - b[2] / b[0]), \
            dtor * math.atan( - c[2] / c[0]))

def find_primitive_reciprocal_axes(lattice, matrix):
    '''From an orientation matrix file, calculate the angles (phi) where
    the primitive reciprical space cell axes a, b, c are in the plane of
    the detector (that is, orthogonal to the direct beam vector.'''

    a, b, c = get_reciprocal_space_primitive_matrix(lattice, matrix)

    dtor = 180.0 / (4.0 * math.atan(1.0))

    return (dtor * math.atan( - a[2] / a[0]), \
            dtor * math.atan( - b[2] / b[0]), \
            dtor * math.atan( - c[2] / c[0]))

if __name__ == '__main_old__':

    matrix = ''' -0.00417059 -0.00089426 -0.01139821
 -0.00084328 -0.01388561  0.01379631
 -0.00121258  0.01273236  0.01424531
      -0.099       0.451      -0.013
 -0.94263428 -0.04741397 -0.33044314
 -0.19059871 -0.73622239  0.64934635
 -0.27406719  0.67507666  0.68495023
    228.0796     52.5895     44.1177     90.0000    100.6078     90.0000
     -0.0985      0.4512     -0.0134'''

    print transmogrify_matrix('mC', matrix, 'aP')
    
    a, b, c = get_real_space_primitive_matrix('mC', matrix)

    print math.sqrt(dot(a, a)), math.sqrt(dot(b, b)), math.sqrt(dot(c, c))

    # to get the phi values am most interested in Ra.Z, Rb.Z, Rc.Z.
    # this is trivial to calculate:
    # R(t)x.z = 0 => x_1 sin(t) = x_3 cos(t) => t = atan(x_3 / x_1)

    dtor = 180.0 / (4.0 * math.atan(1.0))

    print dtor * math.atan(a[2] / a[0]), dtor * math.atan(b[2] / b[0]), \
          dtor * math.atan(c[2] / c[0])

if __name__ == '__main__':
    if len(sys.argv) < 3:

        lattice = 'mC'

        matrix = ''' -0.00417059 -0.00089426 -0.01139821
 -0.00084328 -0.01388561  0.01379631
 -0.00121258  0.01273236  0.01424531
      -0.099       0.451      -0.013
 -0.94263428 -0.04741397 -0.33044314
 -0.19059871 -0.73622239  0.64934635
 -0.27406719  0.67507666  0.68495023
    228.0796     52.5895     44.1177     90.0000    100.6078     90.0000
     -0.0985      0.4512     -0.0134'''

    else:
        lattice = sys.argv[1]
        matrix = open(sys.argv[2], 'r').read()

    print '%.2f %.2f %.2f' % find_primitive_axes(
        lattice, matrix)

    print '%.2f %.2f %.2f' % find_primitive_reciprocal_axes(
        lattice, matrix)
    
