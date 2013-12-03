#!/usr/bin/env python
# Refine.py
#
#   Copyright (C) 2013 Diamond Light Source, Richard Gildea
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Assign indices to reflection centroids given a crystal model

from __future__ import division

from __init__ import _setup_xia2_environ
_setup_xia2_environ()

# interfaces that this inherits from ...
from Schema.Interfaces.FrameProcessor import FrameProcessor

def Refine(DriverType = None):
  '''A factory for RefineWrapper classes.'''

  from Driver.DriverFactory import DriverFactory
  DriverInstance = DriverFactory.Driver(DriverType)

  class RefineWrapper(DriverInstance.__class__,
                      FrameProcessor):

    def __init__(self):
      DriverInstance.__class__.__init__(self)
      FrameProcessor.__init__(self)

      self._images = []
      self._spot_range = []

      self.set_executable('dials.refine')

      self._input_data_files = { }
      self._output_data_files = { }

      self._input_data_files_list = []
      self._output_data_files_list = []

      return

    def set_sweep(self, sweep):
      self._sweep = sweep

    def set_crystal_models(self, crystal_models):
      assert len(crystal_models) == 1 # currently only one crystal at a time
      self._crystal_models = crystal_models

    def setup_from_image(self, image):
      FrameProcessor.setup_from_image(self, image)
      for i in self.get_matching_images():
        self._images.append(self.get_image_name(i))

    def set_input_data_file(self, name, data):
      self._input_data_files[name] = data
      return

    def set_reflection_file(self, name):
      self._reflection_file = name

    def get_output_data_file(self, name):
      return self._output_data_files[name]

    def run(self):
      from Handlers.Streams import Debug
      Debug.write('Running dials.refine')

      self.clear_command_line()
      from dxtbx.serialize import dump
      dump.imageset(self._sweep, 'sweep.json')
      self.add_command_line('sweep.json')

      from cctbx.crystal.crystal_model.serialize import dump_crystal
      for i, crystal_model in enumerate(self._crystal_models):
        dump_crystal(crystal_model, 'crystal%i.json' %(i+1))
        self.add_command_line('crystal%i.json' %(i+1))

      self.add_command_line(self._reflection_file)

      self.start()
      self.close_wait()
      self.check_for_errors()

      import os
      for output_file in ('refined_sweep.json', 'refined_crystal.json'):
        self._output_data_files.setdefault(
          output_file, open(os.path.join(
            self.get_working_directory(), output_file), 'rb').read())

      from dxtbx.serialize import load
      self.refined_sweep = load.imageset_from_string(
        self.get_output_data_file('refined_sweep.json'))

      from cctbx.crystal.crystal_model.serialize import crystal_from_string
      self.refined_crystal = crystal_from_string(
        self.get_output_data_file('refined_crystal.json'))

  return RefineWrapper()

if __name__ == '__main__':
  import sys
  args = sys.argv[1:]
  assert len(args) >= 3
  reflections_file = args[0]
  sweep_file = args[1]
  crystal_files = args[2:]
  from dxtbx.serialize import load
  from cctbx.crystal.crystal_model.serialize import load_crystal
  sweep = load.imageset(sweep_file)
  crystal_models = [load_crystal(f) for f in crystal_files]

  refiner = Refine()
  refiner.set_sweep(sweep)
  refiner.set_crystal_models(crystal_models)
  refiner.set_reflection_file(reflections_file)
  refiner.run()
  print "Starting crystal model:"
  print crystal_models[0]
  print
  print "Refined crystal model:"
  print refiner.refined_crystal
