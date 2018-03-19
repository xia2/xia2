#!/usr/bin/env python
# DetectBlanks.py
#
#   Copyright (C) 2016 Diamond Light Source, Richard Gildea
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Analyse DIALS reflections for blank images

from __future__ import absolute_import, division, print_function

import os

def DetectBlanks(DriverType = None):
  '''A factory for DetectBlanksWrapper classes.'''

  from xia2.Driver.DriverFactory import DriverFactory
  DriverInstance = DriverFactory.Driver(DriverType)

  class DetectBlanksWrapper(DriverInstance.__class__):

    def __init__(self):
      super(DetectBlanksWrapper, self).__init__()

      self.set_executable('dials.detect_blanks')

      self._sweep_filename = None
      self._experiments_filename = None
      self._reflections_filename = None
      self._json_filename = None
      self._phi_step = None
      self._counts_fractional_loss = None
      self._misigma_fractional_loss = None
      self._results = None

    def set_sweep_filename(self, sweep_filename):
      self._sweep_filename = sweep_filename

    def set_experiments_filename(self, experiments_filename):
      self._experiments_filename = experiments_filename

    def set_reflections_filename(self, reflections_filename):
      self._reflections_filename = reflections_filename

    def set_json_filename(self, json_filename):
      self._json_filename = json_filename

    def get_json_filename(self):
      return self._json_filename

    def set_phi_step(self, phi_step):
      self._phi_step = phi_step

    def set_counts_fractional_loss(self, counts_fractional_loss):
      self._counts_fractional_loss = counts_fractional_loss

    def set_misigma_fractional_loss(self, misigma_fractional_loss):
      self._misigma_fractional_loss = misigma_fractional_loss

    def get_results(self):
      return self._results

    def run(self):
      self.clear_command_line()

      if self._sweep_filename is not None:
        self.add_command_line('%s'%self._sweep_filename)
      if self._experiments_filename is not None:
        self.add_command_line('%s'%self._experiments_filename)
      assert self._reflections_filename is not None
      self.add_command_line('%s'%self._reflections_filename)
      if self._json_filename is None:
        self._json_filename = os.path.join(self.get_working_directory(),
                                           '%s_blanks.json' %self.get_xpid())
      self.add_command_line('json=%s'%self._json_filename)
      if self._phi_step is not None:
        self.add_command_line('phi_step=%s' %self._phi_step)
      if self._counts_fractional_loss is not None:
        self.add_command_line(
          'counts_fractional_loss=%s' %self._counts_fractional_loss)
      if self._misigma_fractional_loss is not None:
        self.add_command_line(
          'misigma_fractional_loss=%s' %self._misigma_fractional_loss)
      self.start()
      self.close_wait()
      self.check_for_errors()

      assert os.path.exists(self._json_filename), self._json_filename
      import json
      with open(self._json_filename, 'rb') as f:
        self._results= json.load(f)

  return DetectBlanksWrapper()

if __name__ == '__main__':
  import sys
  image_files = sys.argv[1:]
  assert len(image_files) > 0
  first_image = image_files[0]
  importer = Import()
  importer.setup_from_image(first_image)
  importer.run()
  sweep = importer.load_sweep_model()
  print(sweep.get_detector())
  print(sweep.get_beam())
  print(sweep.get_goniometer())
  print(sweep.get_scan())
