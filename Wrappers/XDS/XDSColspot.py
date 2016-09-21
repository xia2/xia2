#!/usr/bin/env python
# XDSColspot.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# A wrapper to handle the JOB=COLSPOT module in XDS.
#

import os
import sys
import shutil

from xia2.Driver.DriverFactory import DriverFactory

# interfaces that this inherits from ...
from xia2.Schema.Interfaces.FrameProcessor import FrameProcessor

# generic helper stuff
from XDS import imageset_to_xds, xds_check_version_supported, template_to_xds
from xia2.Handlers.Streams import Debug

from xia2.Handlers.Phil import PhilIndex

def XDSColspot(DriverType=None, params=None):

  DriverInstance = DriverFactory.Driver(DriverType)

  class XDSColspotWrapper(DriverInstance.__class__,
                          FrameProcessor):
    '''A wrapper for wrapping XDS in colspot mode.'''

    def __init__(self, params=None):
      super(XDSColspotWrapper, self).__init__()

      # phil parameters

      if not params:
        from xia2.Handlers.Phil import master_phil
        params = master_phil.extract().xds.colspot
      self._params = params

      # now set myself up...

      self._parallel = PhilIndex.params.xia2.settings.multiprocessing.nproc
      self.set_cpu_threads(self._parallel)

      if self._parallel <= 1:
        self.set_executable('xds')
      else:
        self.set_executable('xds_par')

      # generic bits

      self._data_range = (0, 0)
      self._spot_range = []
      self._background_range = (0, 0)
      self._resolution_range = (0, 0)

      self._input_data_files = { }
      self._output_data_files = { }

      self._input_data_files_list = ['X-CORRECTIONS.cbf',
                                     'Y-CORRECTIONS.cbf',
                                     'BLANK.cbf',
                                     'BKGINIT.cbf',
                                     'GAIN.cbf']

      self._output_data_files_list = ['SPOT.XDS']

      return

    # getter and setter for input / output data

    def set_input_data_file(self, name, data):
      self._input_data_files[name] = data
      return

    def get_output_data_file(self, name):
      return self._output_data_files[name]

    # this needs setting up from setup_from_image in FrameProcessor

    def set_data_range(self, start, end):
      offset = self.get_frame_offset()
      self._data_range = (start - offset, end - offset)

    def add_spot_range(self, start, end):
      offset = self.get_frame_offset()
      self._spot_range.append((start - offset, end - offset))

    def set_background_range(self, start, end):
      offset = self.get_frame_offset()
      self._background_range = (start - offset, end - offset)

    def run(self):
      '''Run colspot.'''

      #image_header = self.get_header()

      ## crank through the header dictionary and replace incorrect
      ## information with updated values through the indexer
      ## interface if available...

      ## need to add distance, wavelength - that should be enough...

      #if self.get_distance():
        #image_header['distance'] = self.get_distance()

      #if self.get_wavelength():
        #image_header['wavelength'] = self.get_wavelength()

      #if self.get_two_theta():
        #image_header['two_theta'] = self.get_two_theta()

      header = imageset_to_xds(self.get_imageset())

      xds_inp = open(os.path.join(self.get_working_directory(),
                                  'XDS.INP'), 'w')

      # what are we doing?
      xds_inp.write('JOB=COLSPOT\n')
      xds_inp.write('MAXIMUM_NUMBER_OF_PROCESSORS=%d\n' % \
                    self._parallel)

      #if image_header['detector'] in ('pilatus', 'dectris'):
      if self.get_imageset().get_detector()[0].get_type() == 'SENSOR_PAD':
        xds_inp.write('MINIMUM_NUMBER_OF_PIXELS_IN_A_SPOT=%d\n' %
                      self._params.minimum_pixels_per_spot)

      for record in header:
        xds_inp.write('%s\n' % record)

      name_template = template_to_xds(
        os.path.join(self.get_directory(), self.get_template()))

      record = 'NAME_TEMPLATE_OF_DATA_FRAMES=%s\n' % \
               name_template

      xds_inp.write(record)

      xds_inp.write('DATA_RANGE=%d %d\n' % self._data_range)
      for spot_range in self._spot_range:
        xds_inp.write('SPOT_RANGE=%d %d\n' % spot_range)
      xds_inp.write('BACKGROUND_RANGE=%d %d\n' % \
                    self._background_range)

      if PhilIndex.params.xia2.settings.small_molecule == True:
        xds_inp.write('STRONG_PIXEL=5\n')
        # FIXME should probably be moved to a phil parameter

      xds_inp.close()

      # copy the input file...
      shutil.copyfile(os.path.join(self.get_working_directory(),
                                   'XDS.INP'),
                      os.path.join(self.get_working_directory(),
                                   '%d_COLSPOT.INP' % self.get_xpid()))

      # write the input data files...

      for file_name in self._input_data_files_list:
        src = self._input_data_files[file_name]
        dst = os.path.join(
            self.get_working_directory(), file_name)
        if src != dst:
          shutil.copyfile(src, dst)

      self.start()
      self.close_wait()

      xds_check_version_supported(self.get_all_output())

      # copy the LP file
      shutil.copyfile(os.path.join(self.get_working_directory(),
                                   'COLSPOT.LP'),
                      os.path.join(self.get_working_directory(),
                                   '%d_COLSPOT.LP' % self.get_xpid()))

      # gather the output files

      for file in self._output_data_files_list:
        self._output_data_files[file] = os.path.join(
          self.get_working_directory(), file)

      return

  return XDSColspotWrapper(params)

if __name__ == '__main__':

  colspot = XDSColspot()
  directory = os.path.join(os.environ['XIA2_ROOT'],
                           'Data', 'Test', 'Images')


  colspot.setup_from_image(os.path.join(directory, '12287_1_E1_001.img'))

  for file in ['X-CORRECTIONS.cbf',
               'Y-CORRECTIONS.cbf',
               'BLANK.cbf',
               'BKGINIT.cbf',
               'GAIN.cbf']:
    colspot.set_input_data_file(file, open(file, 'rb').read())

  colspot.set_data_range(1, 1)
  colspot.set_background_range(1, 1)
  colspot.add_spot_range(1, 1)

  colspot.run()
