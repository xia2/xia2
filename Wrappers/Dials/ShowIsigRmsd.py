#!/usr/bin/env python
# ShowIsigRmsd.py
#
#   Copyright (C) 2014 Diamond Light Source, Richard Gildea, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Export DIALS integration output in MTZ format.

from __future__ import division

from __init__ import _setup_xia2_environ
_setup_xia2_environ()

from Handlers.Flags import Flags

def ShowIsigRmsd(DriverType = None):
  '''A factory for ShowIsigRmsdWrapper classes.'''

  from Driver.DriverFactory import DriverFactory
  DriverInstance = DriverFactory.Driver(DriverType)

  class ShowIsigRmsdWrapper(DriverInstance.__class__):

    def __init__(self):
      DriverInstance.__class__.__init__(self)
      self.set_executable('dials.show_isig_rmsd')

      self._reflections_filename = None
      self._data = { }

      return

    def set_reflections_filename(self, reflections_filename):
      self._reflections_filename = reflections_filename
      return

    def data(self):
      return self._data

    def run(self):
      from Handlers.Streams import Debug
      self.clear_command_line()
      self.add_command_line(self._reflections_filename)
      self.start()
      self.close_wait()
      self.check_for_errors()

      self._data = { }

      for record in self.get_all_output():
        tokens = record.split()
        if not tokens:
          continue
        self._data[1 + int(tokens[0])] = (
          int(tokens[1]), float(tokens[2]), float(tokens[3]))

      return

  return ShowIsigRmsdWrapper()

if __name__ == '__main__':
  import sys

  integrate_file = sys.argv[1]

  show = ShowIsigRmsd()
  show.set_reflections_filename(integrate_file)
  show.run()
  print len(show.data())
