#!/usr/bin/env python
# Integrate.py
#
#   Copyright (C) 2014 Diamond Light Source, Richard Gildea, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Integration using DIALS.

from __future__ import division

from __init__ import _setup_xia2_environ
_setup_xia2_environ()

from Handlers.Flags import Flags

def Integrate(DriverType = None):
  '''A factory for IntegrateWrapper classes.'''

  from Driver.DriverFactory import DriverFactory
  DriverInstance = DriverFactory.Driver(DriverType)

  class IntegrateWrapper(DriverInstance.__class__):

    def __init__(self):
      DriverInstance.__class__.__init__(self)
      self.set_executable('dials.integrate')

      self._experiments_filename = None
      self._reflections_filename = None
      self._integration_algorithm = "fitrs"
      self._outlier_algorithm = None
      self._phil_file = None
      self._mosaic = None
      self._dmax = None

      return

    def set_experiments_filename(self, experiments_filename):
      self._experiments_filename = experiments_filename
      return

    def get_experiments_filename(self):
      return self._experiments_filename

    def set_reflections_filename(self, reflections_filename):
      self._reflections_filename = reflections_filename
      return

    def get_reflections_filename(self):
      return self._reflections_filename

    def set_intensity_algorithm(self, algorithm):
      self._integration_algorithm = algorithm
      return

    def get_intensity_algorithm(self):
      return self._integration_algorithm

    def set_background_outlier_algorithm(self, algorithm):
      self._outlier_algorithm = algorithm
      return

    def get_background_outlier_algorithm(self):
      return self._outlier_algorithm

    def set_phil_file(self, phil_file):
      self._phil_file = phil_file
      return

    def set_dmax(self, dmax):
      self._dmax = dmax
      return

    def get_integrated_filename(self):
      import os
      return os.path.join(self.get_working_directory(), 'integrated.pickle')

    def get_mosaic(self):
      return self._mosaic

    def run(self):
      from Handlers.Streams import Debug
      Debug.write('Running dials.integrate')

      self.clear_command_line()
      self.add_command_line('input.experiments=%s' % self._experiments_filename)
      nproc = Flags.get_parallel()
      self.set_cpu_threads(nproc)

      self.add_command_line('nproc=%i' % nproc)
      self.add_command_line(('input.reflections=%s' % self._reflections_filename))
      self.add_command_line(
        'intensity.algorithm=%s' % self._integration_algorithm)
      if self._outlier_algorithm is not None:
        self.add_command_line(
          'outlier.algorithm=%s' % self._outlier_algorithm)
      if self._phil_file is not None:
        self.add_command_line('%s' % self._phil_file)
      if self._dmax is not None:
        self.add_command_line('prediction.dmax=%f' % self._dmax)

      self.start()
      self.close_wait()
      self.check_for_errors()

      for record in self.get_all_output():
        if 'Sigma_m' in record:
          self._mosaic = float(record.split()[-2])

      return

  return IntegrateWrapper()
