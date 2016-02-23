#!/usr/bin/env python
# EstimateGain.py
#
#   Copyright (C) 2016 Diamond Light Source, Richard Gildea
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Estimation of gain

from __future__ import division

import os
from __init__ import _setup_xia2_environ
_setup_xia2_environ()

from Schema.Interfaces.FrameProcessor import FrameProcessor

def EstimateGain(DriverType = None):
  '''A factory for EstimateGainWrapper classes.'''

  from Driver.DriverFactory import DriverFactory
  DriverInstance = DriverFactory.Driver(DriverType)

  class EstimateGainWrapper(DriverInstance.__class__,
                            FrameProcessor):

    def __init__(self):
      super(EstimateGainWrapper, self).__init__()

      self.set_executable('dials.estimate_gain')

      self._sweep_filename = None
      self._kernel_size = None
      self._gain = None

      return

    def set_sweep_filename(self, sweep_filename):
      self._sweep_filename = sweep_filename
      return

    def set_kernel_size(self, kernel_size):
      self._kernel_size = kernel_size
      return

    def get_gain(self):
      return self._gain

    def run(self):

      self.clear_command_line()

      assert self._sweep_filename is not None
      self.add_command_line('%s'%self._sweep_filename)
      if self._kernel_size is not None:
        self.add_command_line('kernel_size=%i,%i' %self._kernel_size)
      self.start()
      self.close_wait()
      self.check_for_errors()

      for line in self.get_all_output():
        if 'Estimated gain:' in line:
          self._gain = float(line.split(':')[-1].strip())

      return

  return EstimateGainWrapper()
