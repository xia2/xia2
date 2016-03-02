#!/usr/bin/env python
# Report.py
#
#   Copyright (C) 2015 Diamond Light Source, Richard Gildea
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# wrapper for xia2.report

from __future__ import division
import os

def Report(DriverType = None):
  '''A factory for ReportWrapper classes.'''

  from xia2.Driver.DriverFactory import DriverFactory
  DriverInstance = DriverFactory.Driver(DriverType)

  class ReportWrapper(DriverInstance.__class__):

    def __init__(self):
      DriverInstance.__class__.__init__(self)
      self.set_executable('xia2.report')
      self._mtz_filename = None
      self._html_filename = None
      self._chef_min_completeness = None
      return

    def set_mtz_filename(self, mtz_filename):
      self._mtz_filename = mtz_filename

    def set_html_filename(self, html_filename):
      self._html_filename = html_filename

    def get_html_filename(self, html_filename):
      return self._html_filename

    def set_chef_min_completeness(self, min_completeness):
      self._chef_min_completeness = min_completeness

    def run(self):
      from xia2.Handlers.Streams import Debug
      Debug.write('Running xia2.report')
      assert self._mtz_filename is not None

      self.clear_command_line()

      self.add_command_line(self._mtz_filename)
      if self._chef_min_completeness is not None:
        self.add_command_line(
          'chef_min_completeness=%s' %self._chef_min_completeness)
      self.start()
      self.close_wait()
      self.check_for_errors()

      html_filename = os.path.join(
        self.get_working_directory(), 'xia2-report.html')
      assert os.path.exists(html_filename)
      if self._html_filename is None:
        self._html_filename = html_filename
      else:
        import shutil
        shutil.move(html_filename, self._html_filename)

      return

  return ReportWrapper()
