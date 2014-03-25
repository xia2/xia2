#!/usr/bin/env python
# Import.py
#
#   Copyright (C) 2013 Diamond Light Source, Richard Gildea, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Import data into the DIALS models for subsequent analysis

from __future__ import division

from __init__ import _setup_xia2_environ
_setup_xia2_environ()

from Schema.Interfaces.FrameProcessor import FrameProcessor

def Import(DriverType = None):
  '''A factory for ImportWrapper classes.'''

  from Driver.DriverFactory import DriverFactory
  DriverInstance = DriverFactory.Driver(DriverType)

  class ImportWrapper(DriverInstance.__class__,
                      FrameProcessor):

    def __init__(self):
      DriverInstance.__class__.__init__(self)
      FrameProcessor.__init__(self)

      self.set_executable('dials.import')

      self._images = []
      self._image_range = []

      self._sweep_filename = 'datablock_import.json'

      return

    def setup_from_image(self, image):
      FrameProcessor.setup_from_image(self, image)
      for i in self.get_matching_images():
        self._images.append(self.get_image_name(i))
      return

    def set_sweep_filename(self, sweep_filename):
      self._sweep_filename = sweep_filename
      return

    def get_sweep_filename(self):
      import os
      if os.path.abspath(self._sweep_filename):
        return self._sweep_filename
      else:
        return os.path.join(self.get_working_directory(), self._sweep_filename)

    def run(self):
      from Handlers.Streams import Debug
      Debug.write('Running dials.import')

      self.clear_command_line()
      for image in self._images:
        self.add_command_line(image)
      self.add_command_line('--output')
      self.add_command_line(self._sweep_filename)
      self.start()
      self.close_wait()
      self.check_for_errors()

      import os
      assert(os.path.exists(os.path.join(self.get_working_directory(),
                                         self._sweep_filename)))
      return

    def load_sweep_model(self):
      from dxtbx.serialize import load
      import os
      return load.imageset_from_string(
        open(os.path.join(self.get_working_directory(),
                          self._sweep_filename), 'r').read())

  return ImportWrapper()

if __name__ == '__main__':
  import sys
  image_files = sys.argv[1:]
  assert len(image_files) > 0
  first_image = image_files[0]
  importer = Import()
  importer.setup_from_image(first_image)
  importer.run()
  sweep = importer.load_sweep_model()
  print sweep.get_detector()
  print sweep.get_beam()
  print sweep.get_goniometer()
  print sweep.get_scan()
