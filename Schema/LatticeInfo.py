#!/usr/bin/env python
# LatticeInfo.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.


#
# 13th June 2006
# 
# Information about a crystal lattice derived from autoindexing results.
# This is likely to be the result of a class which implements the Indexer
# interface.
# 

import os
import sys
import copy

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'
if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

from Schema.Object import Object
from Handlers.Syminfo import Syminfo

class LatticeInfo(Object):
    '''A class to represent the results of auto indexing - including the
    lattice itself, the refined beam centre and the unit cell parameters.'''

    def __init__(self,
                 lattice,
                 cell,
                 mosaic = None,
                 beam = None):
        '''Initialise the object, with lattice a string like tP,
        cell a 6-tuple of (a, b, c, alpha, beta, gamma) with a-c
        in angstroms, alpha-gamma in degrees, and the refined
        beam coordinate in mm, if available.'''

        Object.__init__(self)

        self._parse_lattice(lattice)
        self._parse_cell(cell)
        self._parse_mosaic(mosaic)
        self._parse_beam(beam)
        
        return

    def _parse_lattice(self, lattice):
        '''Check the lattice is recognised. Possible input formats are
        spacegroups, spacegroup numbers, long strings like "tetragonal
        primitive" and short strings (which I actually want) like "tP".'''

        self._lattice = Syminfo.getLattice(lattice)
        return

    def _parse_cell(self, cell):
        '''Check the cell.'''

        if not len(cell) == 6:
            raise RuntimeError, 'cell should be a 6-tuple'

        self._cell = map(float, cell)
        return

    def _parse_beam(self, beam):
        '''Parse the [updated] beam centre.'''

        if beam is None:
            self._beam = (0.0, 0.0)
            return

        if not type(beam) is type((1, 2)):
            raise RuntimeError, 'beam should be a tuple'
        if not len(beam) is 2:
            raise RuntimeError, 'beam should be a 2-tuple'
        
        self._beam = map(float, beam)
        return
    
    def _parse_mosaic(self, mosaic):
        '''Parse the mosaic spread.'''

        if mosaic is None:
            self._mosaic = 0.0
            return

        self._mosaic = float(mosaic)

        return

    def get_lattice(self):
        return self._lattice

    def get_cell(self):
        return self._cell

    def get_mosaic(self):
        return self._mosaic

    def get_beam(self):
        return self._beam

if __name__ == '__main__':
    li = LatticeInfo('P422', (10, 20, 30, 90, 90, 90),
                     mosaic = 0.2, beam = (90.2, 90.8))

    print li.get_lattice()
