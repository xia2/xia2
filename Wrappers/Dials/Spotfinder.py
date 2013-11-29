#!/usr/bin/env python
# Spotfinder.py
#
#   Copyright (C) 2013 Diamond Light Source, Richard Gildea, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Find spots for autoindexing using the DIALS code; this will probably be
# renamed to Spotfinder at some point.

from __future__ import division

from __init__ import _setup_xia2_environ
_setup_xia2_environ()

# interfaces that this inherits from ...
from Schema.Interfaces.FrameProcessor import FrameProcessor

from Handlers.Flags import Flags

def Spotfinder(DriverType = None):
  '''A factory for SpotfinderWrapper classes.'''

  from Driver.DriverFactory import DriverFactory
  DriverInstance = DriverFactory.Driver(DriverType)

  class SpotfinderWrapper(DriverInstance.__class__,
                          FrameProcessor):
    
    def __init__(self):
      DriverInstance.__class__.__init__(self)
      FrameProcessor.__init__(self)

      self._images = []
      self._spot_range = []

      self.set_executable('dials.spotfinder')

      self._input_data_files = { }
      self._output_data_files = { }

      self._input_data_files_list = []
      self._output_data_files_list = []

      return

    def setup_from_image(self, image):
      FrameProcessor.setup_from_image(self, image)
      for i in self.get_matching_images():
        self._images.append(self.get_image_name(i))

    def setup_from_sweep(self, sweep):
      self._images.extend(sweep.paths())

    def set_input_data_file(self, name, data):
      self._input_data_files[name] = data
      return

    def get_output_data_file(self, name):
      return self._output_data_files[name]

    def run(self):
      from Handlers.Streams import Debug
      Debug.write('Running dials.spotfinder')

      self.clear_command_line()
      for image in self._images:
        self.add_command_line(image)
      for file_name in self._input_data_files.keys():
        self.add_command_line(file_name)

      self.add_command_line('-o')
      self.add_command_line('spots.pickle')
      nproc = Flags.get_parallel()
      self.add_command_line('--nproc=%i' %nproc)
      self.start()
      self.close_wait()

      # XXX probably too large to store in memory?
      #self._output_data_files.setdefault(
        #'spots.pickle',
        #open(os.path.join(self.get_working_directory(), 'spots.pickle'), 'rb')
        #.read())

      # XXX this won't work as yet if DIALS is not built into cctbx.python
      # that was used to launch xia2 but eventually the reflection list object
      # should be moved to cctbx anyway
      import cPickle as pickle
      import os
      self.reflections = pickle.load(open(
        os.path.join(self.get_working_directory(), 'spots.pickle'), 'rb'))

  return SpotfinderWrapper()

if __name__ == '__main__':
  import sys, os
  image_files = sys.argv[1:]
  assert len(image_files) > 0
  first_image = image_files[0]
  from Wrappers.Dials.Import import Import
  importer = Import()
  importer.setup_from_image(first_image)
  importer.run()
  print importer.sweep.get_detector()
  print importer.sweep.get_beam()
  print importer.sweep.get_goniometer()
  print importer.sweep.get_scan()
  spotfinder = Spotfinder()
  spotfinder.setup_from_sweep(importer.sweep)
  # or this way:
  #spotfinder.set_input_data_file(
    #'sweep.json', importer.get_output_data_file('sweep.json'))
  # or this way:
  #spotfinder.setup_from_image(first_image)
  spotfinder.run()
  assert os.path.exists('spots.pickle')
  print "dials.spotfinder found %s spots" %len(spotfinder.reflections)
