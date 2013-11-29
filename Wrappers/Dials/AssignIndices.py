#!/usr/bin/env python
# AssignIndices.py
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

def AssignIndices(DriverType = None):
  '''A factory for AssignIndicesWrapper classes.'''

  from Driver.DriverFactory import DriverFactory
  DriverInstance = DriverFactory.Driver(DriverType)

  class AssignIndicesWrapper(DriverInstance.__class__,
                             FrameProcessor):

    def __init__(self):
      DriverInstance.__class__.__init__(self)
      FrameProcessor.__init__(self)

      self._images = []
      self._spot_range = []

      self.set_executable('dials.assign_indices')

      self._input_data_files = { }
      self._output_data_files = { }

      self._input_data_files_list = []
      self._output_data_files_list = []

      return

    def set_sweep(self, sweep):
      self._sweep = sweep
      #self._images.extend(sweep.paths())

    def set_crystal_models(self, crystal_models):
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
      Debug.write('Running dials.assign_indices')

      self.clear_command_line()
      #for image in self._images:
        #self.add_command_line(image)
      from cctbx.crystal.crystal_model.serialize import dump_crystal
      for i, crystal_model in enumerate(self._crystal_models):
        dump_crystal(crystal_model, 'crystal%i.json' %(i+1))
        self.add_command_line('crystal%i.json' %(i+1))

      from dxtbx.serialize import dump
      dump.imageset(self._sweep, 'sweep.json')
      self.add_command_line('sweep.json')

      self.add_command_line(self._reflection_file)

      self.start()
      self.close_wait()

      # XXX this won't work as yet if DIALS is not built into cctbx.python
      # that was used to launch xia2 but eventually the reflection list object
      # should be moved to cctbx anyway
      import cPickle as pickle
      import os
      self.indexed_reflections = pickle.load(open(
        os.path.join(self.get_working_directory(), 'indexed.pickle'), 'rb'))

  return AssignIndicesWrapper()

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

  assigner = AssignIndices()
  assigner.set_sweep(sweep)
  assigner.set_crystal_models(crystal_models)
  assigner.set_reflection_file(reflections_file)
  assigner.run()
  for i in range(len(crystal_models)):
    print "Crystal %i: %i reflections" %(
      (i+1),
      (assigner.indexed_reflections.crystal() == i).count(True))
  print "%i unindexed reflections" %(
    (assigner.indexed_reflections.crystal() == -1).count(True))
