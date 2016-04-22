#!/usr/bin/env python
# XDSXycorr.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# A wrapper to handle the JOB=XYCORR module in XDS.
#

import os
import sys
import shutil

from xia2.Driver.DriverFactory import DriverFactory

# interfaces that this inherits from ...
from xia2.Schema.Interfaces.FrameProcessor import FrameProcessor

# generic helper stuff
from XDS import imageset_to_xds, xds_check_version_supported, xds_check_error
from XDS import template_to_xds

def XDSXycorr(DriverType = None):

  DriverInstance = DriverFactory.Driver(DriverType)

  class XDSXycorrWrapper(DriverInstance.__class__,
                         FrameProcessor):
    '''A wrapper for wrapping XDS in xycorr mode.'''

    def __init__(self):
      super(XDSXycorrWrapper, self).__init__()

      # now set myself up...

      self.set_executable('xds')

      # generic bits

      self._data_range = (0, 0)
      self._spot_range = []
      self._background_range = (0, 0)
      self._resolution_range = (0, 0)

      self._org = [0.0, 0.0]

      self._input_data_files = { }
      self._output_data_files = { }

      self._input_data_files_list = []

      self._output_data_files_list = ['X-CORRECTIONS.cbf',
                                      'Y-CORRECTIONS.cbf']

      return

    # getter and setter for input / output data

    def set_input_data_file(self, name, data):
      self._input_data_files[name] = data
      return

    def get_output_data_file(self, name):
      return self._output_data_files[name]

    # this needs setting up from setup_from_image in FrameProcessor

    def set_data_range(self, start, end):
      self._data_range = (start, end)

    def add_spot_range(self, start, end):
      self._spot_range.append((start, end))

    def set_background_range(self, start, end):
      self._background_range = (start, end)

    def set_beam_centre(self, x, y):
      self._org = float(x), float(y)

    def run(self):
      '''Run xycorr.'''

      #image_header = self.get_header()

      # crank through the header dictionary and replace incorrect
      # information with updated values through the indexer
      # interface if available...

      # need to add distance, wavelength - that should be enough...

      #if self.get_distance():
        #image_header['distance'] = self.get_distance()

      #if self.get_wavelength():
        #image_header['wavelength'] = self.get_wavelength()

      #if self.get_two_theta():
        #image_header['two_theta'] = self.get_two_theta()

      header = imageset_to_xds(self.get_imageset())

      from xia2.Handlers.Phil import PhilIndex
      xds_params = PhilIndex.params.xia2.settings.xds

      xds_inp = open(os.path.join(self.get_working_directory(),
                                  'XDS.INP'), 'w')

      # what are we doing?
      xds_inp.write('JOB=XYCORR\n')

      for record in header:
        xds_inp.write('%s\n' % record)

      if xds_params.geometry_x and xds_params.geometry_y:
        xds_inp.write('X-GEO_CORR=%s\n' % xds_params.geometry_x)
        xds_inp.write('Y-GEO_CORR=%s\n' % xds_params.geometry_y)

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

      xds_inp.write('ORGX=%f ORGY=%f\n' % \
                    tuple(self._org))
      xds_inp.close()

      # copy the input file...
      shutil.copyfile(os.path.join(self.get_working_directory(),
                                   'XDS.INP'),
                      os.path.join(self.get_working_directory(),
                                   '%d_XYCORR.INP' % self.get_xpid()))

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

      # check the status
      xds_check_error(self.get_all_output())

      # copy the LP file
      shutil.copyfile(os.path.join(self.get_working_directory(),
                                   'XYCORR.LP'),
                      os.path.join(self.get_working_directory(),
                                   '%d_XYCORR.LP' % self.get_xpid()))

      # gather the output files

      for file in self._output_data_files_list:
        self._output_data_files[file] = os.path.join(
          self.get_working_directory(), file)

      return

  return XDSXycorrWrapper()

if __name__ == '__main__':

  xycorr = XDSXycorr()
  directory = os.path.join(os.environ['XIA2_ROOT'],
                           'Data', 'Test', 'Images')


  xycorr.setup_from_image(os.path.join(directory, '12287_1_E1_001.img'))

  xycorr.set_data_range(1, 1)
  xycorr.set_background_range(1, 1)
  xycorr.add_spot_range(1, 1)

  xycorr.run()
