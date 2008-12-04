#!/usr/bin/env python
# xia2lattice.py
# 
#   Copyright (C) 2008 STFC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# A wrapper program to reproduce the results of autoindexing given a
# refined triclinic unit cell. This makes use of iotbx.lattice_symmetry
# to do this.

import sys
import os

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'
if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

from Wrappers.Phenix.LatticeSymmetry import LatticeSymmetry
from lib.SymmetryLib import lattice_to_spacegroup

def xia2lattice(cell, input_lattice = None, do_print = True):
    '''Taking the primitive triclinic unit cell, calculate a list of
    possible lattices and their associated unit cell and distortion
    indices.'''

    ls = LatticeSymmetry()

    ls.set_cell(cell)
    ls.set_spacegroup('P1')

    ls.generate()

    lattices = ls.get_lattices()

    if input_lattice:
        if not input_lattice in lattices:
            raise RuntimeError, 'no solution found for lattice %s' % \
                  input_lattice
        
        distortion = ls.get_distortion(input_lattice)
        cell = ls.get_cell(input_lattice)

        cellstr = '%7.2f %7.2f %7.2f %7.2f %7.2f %7.2f' % tuple(cell)

        if do_print:
            print '%s %.4f %s' % (input_lattice, distortion, cellstr)

        return distortion

    for lattice in lattices:
        distortion = ls.get_distortion(lattice)
        cell = ls.get_cell(lattice)
        reindex = ls.get_reindex_op_basis(lattice).replace('x', 'H').replace(
            'y', 'K').replace('z', 'L').replace('*', '')

        cellstr = '%7.2f %7.2f %7.2f %7.2f %7.2f %7.2f' % tuple(cell)

        if do_print:
            spacegroup = lattice_to_spacegroup(lattice)
            print '%s %.4f %s %3d %s' % \
                  (lattice, distortion, cellstr, spacegroup, reindex)

    return

if __name__ == '__main__':

    # change 10/JUL/08 also allow for the unit cell to be passed in on
    # the standard input and the chosen lattice given on the command line

    if len(sys.argv) == 2:
        lattice = sys.argv[1]
        for record in sys.stdin.readlines():
            cell = tuple(map(float, record.split()))
            xia2lattice(cell, input_lattice = lattice, dp_print = True)

    elif len(sys.argv) == 7:

        cell = tuple(map(float, sys.argv[1:7]))
        xia2lattice(cell, do_print = True)

    else:
        raise RuntimeError, '%s (lattice|a b c alpha beta gamma)' % \
              sys.argv[0]
    
