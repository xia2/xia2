#!/usr/bin/env python
# Spotfinder.py
#   Copyright (C) 2013 Diamond Light Source, Richard Gildea
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# A wrapper to handle the dials.spotfinder program.
#

import os
import sys
import shutil

from xia2.Driver.DriverFactory import DriverFactory

# interfaces that this inherits from ...
from xia2.Schema.Interfaces.FrameProcessor import FrameProcessor

# generic helper stuff
from xia2.Handlers.Streams import Debug

from libtbx import phil
import libtbx
import libtbx.load_env

# FIXME make all of this go away...
if libtbx.env.has_module('dials'):
  spotfinding_phil_path = libtbx.env.find_in_repositories(
    relative_path='dials/data/spotfinding.phil',
    test=os.path.isfile)
  master_phil = phil.parse(file_name=spotfinding_phil_path)
else:
  master_phil = phil.parse("""
""")

def Spotfinder(DriverType=None, params=None):

  DriverInstance = DriverFactory.Driver(DriverType)

  class SpotfinderWrapper(DriverInstance.__class__,
                          FrameProcessor):
    '''A wrapper for wrapping dials.spotfinder.'''

    def __init__(self, params=None):
      super(SpotfinderWrapper, self).__init__()

      # phil parameters - should get these from xia2.Handlers.Phil.dials.phil_file
      # perhaps as starting point then clobber those extra parameters we want...

      if not params:
        params = master_phil.extract()
      self._params = params

      # now set myself up...

      self._images = []
      self._spot_range = []

      self.set_executable('dials.spotfinder')

      self._input_data_files = { }
      self._output_data_files = { }

      self._input_data_files_list = []
      self._output_data_files_list = []

      return


    # getter and setter for input / output data

    def setup_from_image(self, image):
      FrameProcessor.setup_from_image(self, image)
      for i in self.get_matching_images():
        self._images.append(self.get_image_name(i))

    def set_input_data_file(self, name, data):
      self._input_data_files[name] = data
      return

    def get_output_data_file(self, name):
      return self._output_data_files[name]

    # this needs setting up from setup_from_image in FrameProcessor

    def add_spot_range(self, start, end):
      self._spot_range.append((start, end))

    def run(self):
      '''Run dials.spotfinder.'''

      # This is a bit of a phil hack in order to pass the phil
      # parameters on the comman line to dials.spotfinder
      master_scope = list(master_phil.active_objects())[0]
      working_phil = master_scope.format(self._params)
      for object_locator in master_scope.fetch_diff(
          working_phil).all_definitions():
        self.add_command_line(object_locator.object.as_str())

      for image in self._images:
        self.add_command_line(image)
      matching_images = self.get_matching_images()
      for spot_range in self._spot_range:
        self.add_command_line('scan_range=%i,%i' %(
            matching_images.index(spot_range[0]),
            matching_images.index(spot_range[1])+1))
      self.add_command_line(('-o', 'reflections.pickle'))
      self.start()
      self.close_wait()

      # check for errors
      self.check_for_errors()

      self._output_data_files.setdefault(
          'reflections.pickle',
          open(os.path.join(self.get_working_directory(),
                            'reflections.pickle'), 'rb').read())
      output = self.get_all_output()
      print "".join(output)

  return SpotfinderWrapper(params=params)

if __name__ == '__main__':
  import sys
  from libtbx.phil import command_line

  args = sys.argv[1:]
  cmd_line = command_line.argument_interpreter(master_params=master_params)
  working_phil, image_files = cmd_line.process_and_fetch(
      args=args, custom_processor="collect_remaining")
  working_phil.show()
  assert len(image_files) > 0
  first_image = image_files[0]
  params = working_phil.extract()
  spotfinder = Spotfinder(params=params)
  spotfinder.setup_from_image(first_image)
  spotfinder.run()
  #for image in image_files:
    #spotfinder.set_input_data_file(image)
  #m2c = Merge2cbf(params=params)
  #m2c.setup_from_image(first_image)
  #m2c.run()
