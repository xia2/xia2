#!/usr/bin/env python
# Xtriage.py
#   Copyright (C) 2017 Diamond Light Source, Richard Gildea
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.

from __future__ import absolute_import, division

from xia2.Driver.DriverFactory import DriverFactory

def Xtriage(DriverType = None):
  '''A factory for the Xtriage wrappers.'''

  DriverInstance = DriverFactory.Driver('simple')

  class XtriageWrapper(DriverInstance.__class__):
    '''A wrapper class for phenix.xtriage.'''

    def __init__(self):
      DriverInstance.__class__.__init__(self)

      self.set_executable('mmtbx.xtriage')

      self._mtz = None

      return

    def set_mtz(self, mtz):
      self._mtz = mtz
      return

    def run(self):
      import os
      assert self._mtz is not None
      assert os.path.isfile(self._mtz)

      self.add_command_line(self._mtz)

      self.start()
      self.close_wait()
      self.check_for_errors()

  return XtriageWrapper()

if __name__ == '__main__':
  import sys
  assert len(sys.argv[1:]) == 1
  xtriage = Xtriage()
  xtriage.set_mtz(sys.argv[1])
  xtriage.run()
  print ''.join(xtriage.get_all_output())
