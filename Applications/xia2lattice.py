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

def xia2lattice(cell):
    '''Taking the primitive triclinic unit cell, calculate a list of
    possible lattices and their associated unit cell and distortion
    indices.'''

    ls = LatticeSymmetry()

    ls.set_cell(cell)
    ls.set_spacegroup('P1')

    ls.generate()

    lattices = ls.get_lattices()

    for lattice in lattices:
        distortion = ls.get_distortion(lattice)
        cell = ls.get_cell(lattice)

        cellstr = '%7.2f %7.2f %7.2f %7.2f %7.2f %7.2f' % tuple(cell)

        print '%s %.4f %s' % (lattice, distortion, cellstr)

    return

if __name__ == '__main__':

    if len(sys.argv) != 7:
        raise RuntimeError, '%s a b c alpha beta gamma' % sys.argv[0]

    cell = tuple(map(float, sys.argv[1:7]))

    xia2lattice(cell)

    
