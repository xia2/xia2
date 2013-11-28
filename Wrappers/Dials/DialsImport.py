#!/usr/bin/env python
# DialsImport.py
#
#   Copyright (C) 2013 Diamond Light Source, Richard Gildea
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Import dxtbx-format experimental models

from __future__ import division

import os

# We should really put these variable checks, etc in one centralised place
def setup_xia2_environ():
  import sys
  if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

  if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

  if not os.path.join(os.environ['XIA2CORE_ROOT'],
                      'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                                 'Python'))

  if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

setup_xia2_environ()

# interfaces that this inherits from ...
from Schema.Interfaces.FrameProcessor import FrameProcessor


def DialsImport(DriverType = None):
  '''A factory for DialsImportWrapper classes.'''

  from Driver.DriverFactory import DriverFactory
  DriverInstance = DriverFactory.Driver(DriverType)

  class DialsImportWrapper(DriverInstance.__class__,
                           FrameProcessor):

    def __init__(self):
      DriverInstance.__class__.__init__(self)
      FrameProcessor.__init__(self)

      self._images = []
      self._spot_range = []

      self.set_executable('dials.import')

      self._input_data_files = { }
      self._output_data_files = { }

      self._input_data_files_list = []
      self._output_data_files_list = []

      return

    def setup_from_image(self, image):
      FrameProcessor.setup_from_image(self, image)
      for i in self.get_matching_images():
        self._images.append(self.get_image_name(i))

    def set_input_data_file(self, name, data):
      self._input_data_files[name] = data
      return

    def get_output_data_file(self, name):
      return self._output_data_files[name]

    def run(self):
      from Handlers.Streams import Debug
      Debug.write('Running dials.import')

      self.clear_command_line()
      for image in self._images:
        self.add_command_line(image)
      self.add_command_line('--sweep-filename')
      self.add_command_line('sweep.json')
      self.start()
      self.close_wait()

      self._output_data_files.setdefault(
        'sweep.json',
        open(os.path.join(self.get_working_directory(), 'sweep.json'), 'rb')
        .read())

      from dxtbx.serialize import load
      self.sweep = load.imageset_from_string(
        self.get_output_data_file('sweep.json'))

  return DialsImportWrapper()

if __name__ == '__main__':
  import sys
  image_files = sys.argv[1:]
  assert len(image_files) > 0
  first_image = image_files[0]
  importer = DialsImport()
  importer.setup_from_image(first_image)
  importer.run()
  print importer.sweep.get_detector()
  print importer.sweep.get_beam()
  print importer.sweep.get_goniometer()
  print importer.sweep.get_scan()
