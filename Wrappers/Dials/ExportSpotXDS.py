#!/usr/bin/env python
# ExportSpotXDS.py
#   Copyright (C) 2013 Diamond Light Source, Richard Gildea
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# A wrapper to handle the dials.spotfinder program.
#

from __future__ import absolute_import, division
import os
import sys

from xia2.Driver.DriverFactory import DriverFactory

# interfaces that this inherits from ...
from xia2.Schema.Interfaces.FrameProcessor import FrameProcessor

from libtbx import phil
import libtbx

master_params = phil.parse("""
""")

def ExportSpotXDS(DriverType=None, params=None):

  DriverInstance = DriverFactory.Driver(DriverType)

  class ExportSpotXDSWrapper(DriverInstance.__class__,
                             FrameProcessor):
    '''A wrapper for wrapping dials.export_spot_xds.'''

    def __init__(self, params=None):

      super(ExportSpotXDSWrapper, self).__init__()

      # phil parameters

      if not params:
        params = master_params.extract()
      self._params = params

      # now set myself up...

      self.set_executable('dials.export_spot_xds')

      self._input_data_files = { }
      self._output_data_files = { }

      self._input_data_files_list = []
      self._output_data_files_list = []

    # getter and setter for input / output data

    def set_input_data_file(self, name, data):
      self._input_data_files[name] = data

    def get_output_data_file(self, name):
      return self._output_data_files[name]

    def run(self):
      '''Run dials.spotfinder.'''

      self.add_command_line(self._input_data_files.keys())
      self.start()
      self.close_wait()
      self.check_for_errors()

      self._output_data_files.setdefault(
          'SPOT.XDS', open(os.path.join(
              self.get_working_directory(), 'SPOT.XDS'), 'rb').read())

      output = self.get_all_output()
      print "".join(output)

  return ExportSpotXDSWrapper(params=params)

if __name__ == '__main__':
  import sys
  from libtbx.phil import command_line

  args = sys.argv[1:]
  cmd_line = command_line.argument_interpreter(master_params=master_params)
  working_phil, files = cmd_line.process_and_fetch(
      args=args, custom_processor="collect_remaining")
  working_phil.show()
  assert len(files) > 0
  params = working_phil.extract()
  export = ExportSpotXDS(params=params)
  for f in files:
    export.set_input_data_file(f, open(f, 'rb'))
  export.run()
