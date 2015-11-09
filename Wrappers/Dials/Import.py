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
      super(ImportWrapper, self).__init__()

      self.set_executable('dials.import')

      self._images = []
      self._image_range = []

      self._sweep_filename = 'datablock_import.json'
      self._image_to_epoch = None
      self._reference_geometry = None
      self._mosflm_beam_centre = None
      self._wavelength_tolerance = None

      return

    def set_image_range(self, image_range):
      self._image_range = image_range

    def set_sweep_filename(self, sweep_filename):
      self._sweep_filename = sweep_filename
      return

    def set_wavelength_tolerance(self, tolerance):
      self._wavelength_tolerance = tolerance

    def get_sweep_filename(self):
      import os
      if os.path.abspath(self._sweep_filename):
        return self._sweep_filename
      else:
        return os.path.join(self.get_working_directory(), self._sweep_filename)

    def set_image_to_epoch(self, image_to_epoch):
      self._image_to_epoch = image_to_epoch
      return

    def set_reference_geometry(self, reference_geometry):
      self._reference_geometry = reference_geometry

    def set_mosflm_beam_centre(self, mosflm_beam_centre):
      self._mosflm_beam_centre = mosflm_beam_centre

    def fix_datablock_import(self):
      import json
      import os

      datablock_json = self.get_sweep_filename()

      datablock = json.load(open(datablock_json))
      scan = datablock[0]['scan'][0]

      # fix image_range, exposure_time, epochs

      first, last = self._image_range
      offset = self.get_frame_offset()

      exposure_time = scan[u'exposure_time'][0]
      scan[u'image_range'] = [first+offset, last+offset]
      scan[u'epochs'] = []
      scan[u'exposure_time'] = []
      scan[u'epochs'] = []
      for image in range(first, last + 1):
        scan[u'exposure_time'].append(exposure_time)
        scan[u'epochs'].append(self._image_to_epoch[image+offset])
      datablock[0]['scan'] = [scan]
      json.dump(datablock, open(datablock_json, 'w'))

      return

    def run(self, fast_mode=False):

      # fast_mode: read first two image headers then extrapolate the rest
      # from what xia2 read from the image headers...

      from Handlers.Streams import Debug
      if fast_mode:
        if not self._image_to_epoch:
          raise RuntimeError, 'fast mode needs image_to_epoch map'
        Debug.write('Running dials.import in fast mode')
      else:
        Debug.write('Running dials.import in slow mode')

      self.clear_command_line()

      for i in range(self._image_range[0], self._image_range[1] + 1):
        self._images.append(self.get_image_name(i))

      if self._wavelength_tolerance is not None:
        self.add_command_line(
          'input.tolerance.beam.wavelength=%s' %self._wavelength_tolerance)

      if self._reference_geometry is not None:
        self.add_command_line(
          'input.reference_geometry=%s' % self._reference_geometry)

      elif self._mosflm_beam_centre is not None:
        assert len(self._mosflm_beam_centre) == 2
        self.add_command_line(
          'mosflm_beam_centre=%s,%s' % (self._mosflm_beam_centre))

      if fast_mode:
        for image in self._images[:2]:
          self.add_command_line(image)
      else:
        for image in self._images:
          self.add_command_line(image)

      self.add_command_line('output=%s' % self._sweep_filename)
      self.start()
      self.close_wait()
      self.check_for_errors()

      if fast_mode:
        self.fix_datablock_import()

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
