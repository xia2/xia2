#!/usr/bin/env python
# LabelitMosflmMatrix.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 18th July 2006
#
# An interface to the labelit program labelit.mosflm_matrix, used for
# generating an integration script for Mosflm. In this case this is used
# for generating the matrix file to make mosflm work. This will be added
# to the Indexer payload in LabelitIndex.py.
#
#
#

import os
import sys

from xia2.Driver.DriverFactory import DriverFactory

def LabelitMosflmMatrix(DriverType = None):
  '''Factory for LabelitMosflmMatrix wrapper classes, with the specified
  Driver type.'''

  DriverInstance = DriverFactory.Driver(DriverType)

  class LabelitMosflmMatrixWrapper(DriverInstance.__class__):
    '''A wrapper for the program labelit.mosflm_matrix - which will
    calculate the matrix for mosflm integration.'''

    def __init__(self):

      DriverInstance.__class__.__init__(self)
      self.set_executable('labelit.mosflm_matrix')

      self._solution = None
      self._mosflm_beam = None

      return

    def set_solution(self, solution):
      self._solution = solution

      return

    def calculate(self):
      '''Compute matrix for solution #.'''

      if self._solution is None:
        raise RuntimeError, 'solution not selected'

      task = 'Compute matrix for solution %02d' % self._solution

      self.add_command_line('%d' % self._solution)

      self.start()
      self.close_wait()

      output = open(os.path.join(self.get_working_directory(),
                                 'integration%02d.csh' % self._solution)
                   ).readlines()
      matrix = output[2:11]

      # also check for the beam centre in mosflm land! - ignoring
      # SWUNG OUT though I should probably check the two-theta
      # value too...

      for o in output:
        if 'BEAM' in o[:4]:
          self._mosflm_beam = map(float, o.split()[-2:])

      return matrix

    def get_mosflm_beam(self):
      return self._mosflm_beam

  return LabelitMosflmMatrixWrapper()

if __name__ == '__main__':

  lms = LabelitMosflmMatrix()
  lms.set_solution(9)
  for m in lms.calculate():
    print m[:-1]
