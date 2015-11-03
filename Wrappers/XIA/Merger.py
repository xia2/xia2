#!/usr/bin/env cctbx.python
# Merger.py
#
#   Copyright (C) 2013 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# A wrapper for the new Resolutionizer module, using the PythonDriver to get a
# nice subprocess...

import sys
import math
import os

if not os.environ.has_key('XIA2CORE_ROOT'):
  raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
  sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))

if not os.environ.has_key('XIA2_ROOT'):
  raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
  sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

from Handlers.Flags import Flags
from Driver.DriverFactory import DriverFactory
from Handlers.Streams import Debug

def Merger(DriverType=None):
  '''A factory for MergerWrapper classes.'''

  DriverInstance = DriverFactory.Driver(DriverType)

  class MergerWrapper(DriverInstance.__class__):

    def __init__(self):
      DriverInstance.__class__.__init__(self)
      self.set_executable('xia2.resolutionizer')

      # inputs
      self._hklin = None
      self._limit_rmerge = None
      self._limit_completeness = None
      self._limit_cc_half = None
      self._limit_isigma = None
      self._limit_misigma = None
      self._nbins = 100
      self._batch_range = None

      # outputs
      self._resolution_rmerge = None
      self._resolution_completeness = None
      self._resolution_cc_half = None
      self._resolution_isigma = None
      self._resolution_misigma = None

      return

    def set_hklin(self, hklin):
      self._hklin = hklin
      return

    def set_nbins(self, nbins):
      self._nbins = nbins
      return

    def set_limit_rmerge(self, limit_rmerge):
      self._limit_rmerge = limit_rmerge
      return

    def set_limit_completeness(self, limit_completeness):
      self._limit_completeness = limit_completeness
      return

    def set_limit_cc_half(self, limit_cc_half):
      self._limit_cc_half = limit_cc_half
      return

    def set_limit_isigma(self, limit_isigma):
      self._limit_isigma = limit_isigma
      return

    def set_limit_misigma(self, limit_misigma):
      self._limit_misigma = limit_misigma
      return

    def set_batch_range(self, start, end):
      self._batch_range = (start, end)
      return

    def get_resolution_rmerge(self):
      return self._resolution_rmerge

    def get_resolution_completeness(self):
      return self._resolution_completeness

    def get_resolution_cc_half(self):
      return self._resolution_cc_half

    def get_resolution_isigma(self):
      return self._resolution_isigma

    def get_resolution_misigma(self):
      return self._resolution_misigma

    def run(self):
      assert(self._hklin)
      cl = [self._hklin]
      cl.append('nbins=%d' % self._nbins)
      if self._limit_rmerge:
        cl.append('rmerge=%f' % self._limit_rmerge)
      if self._limit_completeness:
        cl.append('completeness=%f' % self._limit_completeness)
      if self._limit_cc_half:
        cl.append('cc_half=%f' % self._limit_cc_half)
      if self._limit_isigma:
        cl.append('isigma=%f' % self._limit_isigma)
      if self._limit_misigma:
        cl.append('misigma=%f' % self._limit_misigma)
      if self._batch_range is not None:
        cl.append('batch_range=%i,%i' % self._batch_range)
      for c in cl:
        self.add_command_line(c)
      Debug.write('Resolution analysis: %s' % (' '.join(cl)))
      self.start()
      self.close_wait()
      for record in self.get_all_output():
        if 'Resolution rmerge' in record:
          self._resolution_rmerge = float(record.split()[-1])
        if 'Resolution completeness' in record:
          self._resolution_completeness = float(record.split()[-1])
        if 'Resolution cc_half' in record:
          self._resolution_cc_half = float(record.split()[-1])
        if 'Resolution I/sig' in record:
          self._resolution_isigma = float(record.split()[-1])
        if 'Resolution Mn(I/sig)' in record:
          self._resolution_misigma = float(record.split()[-1])

      return

  return MergerWrapper()

if __name__ == '__main__':

  m = Merger()
  m.set_hklin(sys.argv[1])
  m.run()
  print 'Resolutions:'
  print 'I/sig:      %.2f' % m.get_resolution_isigma()
  print 'Mn(I/sig):  %.2f' % m.get_resolution_misigma()
