#!/usr/bin/env python
# Report.py
#
#   Copyright (C) 2015 Diamond Light Source, Richard Gildea
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Assign indices to reflection centroids given a crystal model

from __future__ import absolute_import, division, print_function

def Report(DriverType = None):
  '''A factory for ReportWrapper classes.'''

  from xia2.Driver.DriverFactory import DriverFactory
  DriverInstance = DriverFactory.Driver(DriverType)

  class ReportWrapper(DriverInstance.__class__):

    def __init__(self):
      DriverInstance.__class__.__init__(self)

      self.set_executable('dials.report')

      self._experiments_filename = None
      self._reflections_filename = None
      self._html_filename = None

    def set_experiments_filename(self, experiments_filename):
      self._experiments_filename = experiments_filename

    def set_reflections_filename(self, reflections_filename):
      self._reflections_filename = reflections_filename

    def set_html_filename(self, html_filename):
      self._html_filename = html_filename

    def run(self):
      from xia2.Handlers.Streams import Debug
      Debug.write('Running dials.report')

      self.clear_command_line()
      assert (self._experiments_filename is not None or
              self._reflections_filename is not None)
      if self._experiments_filename is not None:
        self.add_command_line(self._experiments_filename)
      if self._reflections_filename is not None:
        self.add_command_line(self._reflections_filename)
      if self._html_filename is not None:
        self.add_command_line('output.html=%s' %self._html_filename)
      self.start()
      self.close()
      self.check_for_errors()

  return ReportWrapper()
