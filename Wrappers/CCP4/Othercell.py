#!/usr/bin/env python
# Othercell.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
# 
# A program wrapper for Phil Evan's program othercell (a part of 
# pointless) for providing other reasonable lattice solutions
# given a unit cell and lattice type (pcif)
# 
# FIXME 24/AUG/06 this needs to be tied into the indexing possibilities...
# 

import os
import sys
import copy

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'
if not os.environ.has_key('DPA_ROOT'):
    raise RuntimeError, 'DPA_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'],
                    'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                                 'Python'))
    
if not os.environ['DPA_ROOT'] in sys.path:
    sys.path.append(os.environ['DPA_ROOT'])

from Driver.DriverFactory import DriverFactory

def Othercell(DriverType = None):
    '''Factory for Othercell wrapper classes, with the specified
    Driver type.'''

    DriverInstance = DriverFactory.Driver(DriverType)

    class OthercellWrapper(DriverInstance.__class__):
        '''A wrapper for the program othercell - which will provide
        functionality for presenting other indexing possibilities...'''

        def __init__(self):
            DriverInstance.__class__.__init__(self)

            self.set_executable('othercell')

            self._initial_cell = []
            self._initial_lattice_type = None

            # results storage

            # lattice point group stuff
            self._lpg = None
            self._lpg_rdx_op = None
            self._lpg_rdx_cell = None

            # possible spacegroups

            self._possible_spacegroups = []

            return

        def setCell(self, cell):
            self._initial_cell = cell

            return

        def setLattice(self, lattice):
            self._initial_lattice_type = lattice

            return

        def generate(self):
            if not self._initial_cell:
                raise RuntimeError, 'must set the cell'
            if not self._initial_lattice_type:
                raise RuntimeError, 'must set the lattice'

            self.start()

            self.input('%f %f %f %f %f %f' % tuple(self._initial_cell))
            self.input('%s' % self._initial_lattice_type)
            self.input('')

            self.close_wait()

            output = self.get_all_output()

            for i in range(len(output)):
                o = output[i]
                if 'Lattice point group' in o:
                    self._lpg = o.split(':')[1].strip()

                if 'Reindex operator from initial to lattice cell' in o:
                    self._lpg_rdx_op = o.split(':')[1].strip()

                if 'Lattice unit cell after reindexing:' in o:
                    self._lpg_rdx_cell = o.split(':')[1].split()

                # next to figure out how to get the remaining possible
                # indexing solutions from the output...
                # this is basically a list of spacegroups with the
                # reindexing solutions & unit cells following...

                if 'Possible spacegroups:' in o:
                    # I only care about the first one, from an indexing
                    # point of view...
                    self._possible_spacegroups.append(
                        output[i + 1].replace('<', ' ').split('>')[0].strip())

            # triclinic is always an option!
            if not 'P 1' in self._possible_spacegroups:
                self._possible_spacegroups.append('P 1')

            return

        def get_lattice_pg_info(self):
            return self._lpg, self._lpg_rdx_cell, self._lpg_rdx_op

        def get_lattices(self):
            return self._possible_spacegroups

    return OthercellWrapper()

if __name__ == '__main__':

    o = Othercell()

    o.setCell([43.62, 52.27, 116.4, 103, 100.7, 90.03])
    o.setLattice('p')

    o.generate()

    print o.get_lattices()
                
