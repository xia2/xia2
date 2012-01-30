#!/usr/bin/env python
# SubstructureLib.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 16th November 2006
#
# A library of things pertaining to substructure manipulation:
#
# .pdb file -> fractional coordinates
# invert hand

import sys
import os
import copy
import math
import random

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from SymmetryLib import spacegroup_name_short_to_long, compute_enantiomorph

def _dot(a, b):
    '''Compute a.b. For converting with the aid of a SCALEN record in a
    pdb file...'''

    if not len(a) == len(b):
        raise RuntimeError, 'different length vectors'

    result = 0.0

    for i in range(len(a)):
        result += a[i] * b[i]

    return result

def _determinant_3x3_matrix(m):
    '''Compute the determinant of 3x3 matrix m.'''

    determinant = m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1]) + \
                  m[0][1] * (m[1][2] * m[2][0] - m[1][0] * m[2][2]) + \
                  m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0])

    return determinant

def _invert_3x3_matrix(m):
    '''Invert a 3x3 matrix m, based on the determinant formula.'''

    determinant = _determinant_3x3_matrix(m)

    if determinant == 0.0:
        raise RuntimeError, 'zero determinant'

    # prepare storage

    inverse_m = { }
    for i in range(3):
        inverse_m[i] = [0.0, 0.0, 0.0]

    # perform calculation
    inverse_m[0][0] = (m[1][1] * m[2][2] - m[1][2] * m[2][1]) / determinant
    inverse_m[0][1] = (m[0][2] * m[2][1] - m[0][1] * m[2][2]) / determinant
    inverse_m[0][2] = (m[0][1] * m[1][2] - m[0][2] * m[1][1]) / determinant

    inverse_m[1][0] = (m[1][2] * m[2][0] - m[1][0] * m[2][2]) / determinant
    inverse_m[1][1] = (m[0][0] * m[2][2] - m[0][2] * m[2][0]) / determinant
    inverse_m[1][2] = (m[0][2] * m[1][0] - m[0][0] * m[1][2]) / determinant

    inverse_m[2][0] = (m[1][0] * m[2][1] - m[1][1] * m[2][0]) / determinant
    inverse_m[2][1] = (m[0][1] * m[2][0] - m[0][0] * m[2][1]) / determinant
    inverse_m[2][2] = (m[0][0] * m[1][1] - m[0][1] * m[1][0]) / determinant

    # return inverse

    return inverse_m

def _transpose_3x3_matrix(m):
    '''Transpose 3x3 matrix m.'''

    transpose_m = {}
    for i in range(3):
        transpose_m[i] = [0.0, 0.0, 0.0]

    for i in range(3):
        for j in range(3):
            transpose_m[j][i] = m[i][j]

    return transpose_m

def _multiply_3x3_matrix(m, n):
    '''Multiply together 3x3 matrices m, n.'''

    transpose_n = _transpose_3x3_matrix(n)

    multiply_m = {}
    for i in range(3):
        multiply_m[i] = [0.0, 0.0, 0.0]

    for i in range(3):
        for j in range(3):
            multiply_m[i][j] = _dot(m[i], transpose_n[j])

    return multiply_m

def _generate_3x3_matrix():
    '''Generate a random 3x3 matrix.'''

    random_m = {}
    for i in range(3):
        random_m[i] = [0.0, 0.0, 0.0]

    for i in range(3):
        for j in range(3):
            random_m[i][j] = random.random()


    return random_m

def _test_3x3_matrix_inverse():
    '''Generate 100 random matrices, invert them, multiply them and
    check that the result looks like an identity to a "high resolution".'''

    for k in range(100):
        r = _generate_3x3_matrix()
        ri = _invert_3x3_matrix(r)
        i = _multiply_3x3_matrix(r, ri)

        _is_identity_3x3_matrix(i)

def _is_identity_3x3_matrix(m):
    '''Check if this looks like an identity matrix.'''

    for i in range(3):
        for j in range(3):
            if i == j:
                if math.fabs(m[i][j] - 1) > 1.0e-7:
                    raise RuntimeError, 'non identity'
            else:
                if math.fabs(m[i][j]) > 1.0e-7:
                    raise RuntimeError, 'non identity'

def write_pdb_sites_file(sites_info, out = sys.stdout):
    '''Write a PDB format output containing the sites information.'''

    # gather the information

    cell = sites_info['cell']
    symm = sites_info['spacegroup']
    scales = sites_info['scale']

    # header guff

    out.write('REMARK PDB FILE WRITTEN BY XIA2\n')
    if symm:
        out.write('CRYST1 %8.3f %8.3f %8.3f %6.2f %6.2f %6.2f %s\n' % \
                  (cell[0], cell[1], cell[2], cell[3], cell[4], cell[5],
                   symm))
    else:
        out.write('CRYST1 %8.3f %8.3f %8.3f %6.2f %6.2f %6.2f\n' % \
                  (cell[0], cell[1], cell[2], cell[3], cell[4], cell[5]))

    for j in range(3):
        out.write('SCALE%d     %9.6f %9.6f %9.6f        0.00000\n' % \
                  (j + 1, scales[j][0], scales[j][1], scales[j][2]))

    # atom sites

    j = 0
    for atom in sites_info['sites']:
        j += 1
        format = 'ATOM    %3d %s   SUB   %3d     ' + \
                 '%7.3f %7.3f %7.3f %5.2f  0.00\n'
        out.write(format % \
                  (j, atom['atom'].upper(), j,
                   atom['cartesian'][0], atom['cartesian'][1],
                   atom['cartesian'][2], atom['occupancy']))

    out.write('END\n')

    return

def parse_pdb_sites_file(pdb_file):
    '''Parse a pdb file full of heavy atoms and transmogrify this into
    a form suitable for input to e.g. bp3 (with fractional coordinates
    and occupancies.)'''

    data = open(pdb_file, 'r').readlines()

    scales = { }

    sites = []
    cell = ()
    symm = ''

    for d in data:
        if 'SCALE' in d[:5]:
            scale = map(float, d.split()[1:4])
            scales[int(d.split()[0].replace('SCALE', '')) - 1] = scale

        # need to store this to handle the inversion...

        if 'CRYST1' in d[:6]:
            cell = tuple(map(float, d.split()[1:7]))

            # need to ensure that this has a standard format name - so
            # zap the spaces then look it up in the CCP4 symop.lib.
            symm = spacegroup_name_short_to_long(
                d[55:].strip().replace(' ', ''))

    if not scales.has_key(0):
        raise RuntimeError, 'SCALE1 record missing'

    if not scales.has_key(1):
        raise RuntimeError, 'SCALE2 record missing'

    if not scales.has_key(2):
        raise RuntimeError, 'SCALE3 record missing'

    # for future reference, compute the inverse of the scales to convert
    # from fractional to cartesian coordinates

    scales_inverse = _invert_3x3_matrix(scales)

    for d in data:
        # have to be able to get the sites from shelx too...
        if 'ATOM' in d[:4] or 'HETATM' in d[:6]:
            cartesian = map(float, d.split()[5:8])
            occ = float(d.split()[8])
            atom = d.split()[2].lower()

            fractional = tuple([_dot(scales[i], cartesian) for i in range(3)])


            sites.append({'atom':atom,
                          'occupancy':occ,
                          'cartesian':cartesian,
                          'fractional':fractional})

    results = { }
    results['sites'] = sites
    results['cell'] = cell
    results['spacegroup'] = symm
    results['scale'] = scales
    results['scale_inverse'] = scales_inverse

    return results

def invert_hand(sites_info):
    '''Invert the hand (and perhaps the spacegroup) of substructure sites.'''

    new_sites_info = copy.deepcopy(sites_info)

    new_sites = []
    old_sites = sites_info['sites']

    # check first for special cases...

    if sites_info['spacegroup'] == 'I 41':
        for site in old_sites:
            fractional = site['fractional']
            new_fractional = (1 - fractional[0],
                              0.5 - fractional[1],
                              1 - fractional[2])
            new_cartesian = tuple([_dot(sites_info['scale_inverse'][j],
                                        new_fractional) for j in range(3)])

            new_sites.append({'atom':site['atom'],
                              'occupancy':site['occupancy'],
                              'cartesian':new_cartesian,
                              'fractional':new_fractional})

    elif sites_info['spacegroup'] == 'I 41 2 2':
        for site in old_sites:
            fractional = site['fractional']
            new_fractional = (1 - fractional[0],
                              0.5 - fractional[1],
                              0.25 - fractional[2])

            new_cartesian = tuple([_dot(sites_info['scale_inverse'][j],
                                        new_fractional) for j in range(3)])

            new_sites.append({'atom':site['atom'],
                              'occupancy':site['occupancy'],
                              'cartesian':new_cartesian,
                              'fractional':new_fractional})

    elif sites_info['spacegroup'] == 'F 41 3 2':
        for site in old_sites:
            fractional = site['fractional']
            new_fractional = (0.25 - fractional[0],
                              0.25 - fractional[1],
                              0.25 - fractional[2])

            new_cartesian = tuple([_dot(sites_info['scale_inverse'][j],
                                        new_fractional) for j in range(3)])

            new_sites.append({'atom':site['atom'],
                              'occupancy':site['occupancy'],
                              'cartesian':new_cartesian,
                              'fractional':new_fractional})

    else:
        # we have the general case
        for site in old_sites:
            fractional = site['fractional']
            new_fractional = (1.0 - fractional[0],
                              1.0 - fractional[1],
                              1.0 - fractional[2])

            new_cartesian = tuple([_dot(sites_info['scale_inverse'][j],
                                        new_fractional) for j in range(3)])

            new_sites.append({'atom':site['atom'],
                              'occupancy':site['occupancy'],
                              'cartesian':new_cartesian,
                              'fractional':new_fractional})

        # perhaps invert the spacegroup to it's enantiomorph -
        # if it is set at all!

        if sites_info['spacegroup']:
            new_sites_info['spacegroup'] = compute_enantiomorph(
                sites_info['spacegroup'])
        else:
            new_sites_info['spacegroup'] = sites_info['spacegroup']

    new_sites_info['sites'] = new_sites

    return new_sites_info

if __name__ == '__main__':
    if len(sys.argv) < 2:
        pdb = os.path.join(os.environ['XIA2_ROOT'],
                           'Data', 'Test', 'Sites', 'hyss-sites.pdb')
    else:
        pdb = sys.argv[1]

    sites = parse_pdb_sites_file(pdb)
    write_pdb_sites_file(sites)
    write_pdb_sites_file(invert_hand(sites))
