#!/usr/bin/env python
# Othercell.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# A program wrapper for Phil Evan's program othercell (a part of
# pointless) for providing other reasonable lattice solutions
# given a unit cell and lattice type (pcif)
#
# FIXME 24/AUG/06 this needs to be tied into the indexing possibilities...
#
# FIXME 08/SEP/06 this also needs to parse the xml coming from othercell.
#                 - after some tinkering ot does, and also needed to mod
#                   the xml output from othercell - hence the -gw suffix.
#                 Done - but I need to decide what I want from this next.
#
# FIXME 08/SEP/06 would be nice to also apply the latice constraints on
#                 the output unit cells, based on the standard numbers
#                 in IUCR Tables A. For instance, if tP set alpha =
#                 beta = gamma = 90.0 degrees.
#
#                 This will be spacegroup -> lattice: new_cell =
#                 apply_lattice('tP', old_cell) [say] return new_cell.
#
# FIXME 08/SEP/06 want to feed the unit cell from autoindexing into this,
#                 then write out the possibles with penalties to the
#                 "chatter" stream. This should go into Indexer interface,
#                 perhaps?
#
# FIXME 12/SEP/06 perhaps I should clean up, that is, delete the othercell.xml
#                 file. Perhaps further, I should call it something random not
#                 othercell.xml, in case I have two jobs running in one
#                 directory.

import os
import sys

from xia2.Driver.DriverFactory import DriverFactory
from xia2.Experts.LatticeExpert import ApplyLattice
from xia2.Handlers.Syminfo import Syminfo
from xia2.Handlers.Streams import Chatter
from xia2.Handlers.Flags import Flags

from xia2.lib.SymmetryLib import lauegroup_to_lattice

def Othercell(DriverType = None):
  '''Factory for Othercell wrapper classes, with the specified
  Driver type.'''

  DriverInstance = DriverFactory.Driver(DriverType)

  class OthercellWrapper(DriverInstance.__class__):
    '''A wrapper for the program othercell - which will provide
    functionality for presenting other indexing possibilities...'''

    def __init__(self):
      DriverInstance.__class__.__init__(self)

      self.set_executable(os.path.join(
          os.environ.get('CBIN', ''), 'othercell'))

      self._initial_cell = []
      self._initial_lattice_type = None

      # results storage

      self._lattices = []
      self._distortions = { }
      self._cells = { }
      self._reindex_ops = { }

      return

    def set_cell(self, cell):
      self._initial_cell = cell

      return

    def set_lattice(self, lattice):
      '''Set the full lattice - not just the centering operator!.'''

      self._initial_lattice_type = lattice[1].lower()

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

      # parse the output of the program...

      for o in self.get_all_output():

        if not '[' in o:
          continue
        if 'Reindex op' in o:
          continue
        if 'Same cell' in o:
          continue
        if 'Other cell' in o:
          continue
        if 'within angular tolerance' in o:
          continue

        lauegroup = o[:11].strip()
        if not lauegroup:
          continue

        if lauegroup[0] == '[':
          continue

        modded_lauegroup = ''
        for token in lauegroup.split():
          if token == '1':
            continue
          modded_lauegroup += token

        try:
          lattice = lauegroup_to_lattice(modded_lauegroup)
        except KeyError, e:
          # there was some kind of mess made of the othercell
          # output - this happens!
          continue

        cell = tuple(map(float, o[11:45].split()))
        distortion = float(o.split()[-2])
        operator = o.split()[-1][1:-1]

        if not lattice in self._lattices:
          self._lattices.append(lattice)
          self._distortions[lattice] = distortion
          self._cells[lattice] = cell
          self._reindex_ops[lattice] = operator
        else:
          if distortion > self._distortions[lattice]:
            continue
          self._distortions[lattice] = distortion
          self._cells[lattice] = cell
          self._reindex_ops[lattice] = operator

    def get_lattices(self):
      return self._lattices

    def get_cell(self, lattice):
      return self._cells[lattice]

    def get_reindex_op(self, lattice):
      return self._reindex_ops[lattice]


  return OthercellWrapper()

if __name__ == '__main__':

  o = Othercell()

  # o.set_cell([43.62, 52.27, 116.4, 103, 100.7, 90.03])
  # o.set_lattice('p')

  o.set_cell([198.61, 198.61, 243.45, 90.00, 90.00, 120.00])
  o.set_lattice('r')

  o.generate()

  # need to add some checks in here that everything went fine...
  # for line in o.get_all_output():
  # print line[:-1]

  o.get_cell('aP')
  o.get_reindex_op('aP')
