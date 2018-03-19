#!/usr/bin/env python
# Autoindex.py
#
#   Copyright (C) 2013 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Autoindex from a prepared spot list, from a previous run of Findspots. This
# needs to handle the cases where:
#
# - unit cell / symmetry are unknown
# - unit cell / symmetry are known (or at least asserted)
#
# third case (symmetry known but unit cell not) will be handled at the higher
# level.

from __future__ import absolute_import, division, print_function

def Autoindex(DriverType = None):
  '''A factory for AutoindexWrapper(ipmosflm) classes.'''

  from xia2.Driver.DriverFactory import DriverFactory
  DriverInstance = DriverFactory.Driver(DriverType)

  class AutoindexWrapper(DriverInstance.__class__):

    def __init__(self):
      DriverInstance.__class__.__init__(self)

      import os
      self.set_executable(os.path.join(
          os.environ['CCP4'], 'bin', 'ipmosflm'))

      self._input_cell = None
      self._input_symmetry = None
      self._spot_file = None

      return

    def set_input_cell(self, input_cell):
      self._input_cell = input_cell
      return

    def set_input_symmetry(self, input_symmetry):
      self._input_symmetry = input_symmetry
      return

    def set_spot_file(self, spot_file):
      self._spot_file = spot_file
      return

    def select_images(self, fp):
      from xia2.Handlers.Streams import Debug
      from xia2.Modules.Indexer.IndexerSelectImages import index_select_images_lone
      phi_width = fp.get_header_item('phi_width')
      images = fp.get_matching_images()
      return index_select_images_lone(phi_width, images)

    def __call__(self, fp, images = None):
      from xia2.Handlers.Streams import Debug

      if images is None:
        images = self.select_images(fp)

      images_str = ' '.join(map(str, images))

      if self._spot_file:
        Debug.write('Running mosflm to autoindex from %s' %
                    self._spot_file)
      else:
        Debug.write('Running mosflm to autoindex from images %s' %
                    images_str)

      self.start()
      self.input('template "%s"' % fp.get_template())
      self.input('directory "%s"' % fp.get_directory())
      self.input('beam %f %f' % fp.get_beam_centre())
      self.input('distance %f' % fp.get_distance())
      self.input('wavelength %f' % fp.get_wavelength())

      if self._spot_file:
        self.input('autoindex dps refine image %s file %s' %
                   (images_str, self._spot_file))
      else:
        self.input('autoindex dps refine image %s' % images_str)

      self.input('go')
      self.close_wait()

      from xia2.Wrappers.Mosflm.AutoindexHelpers import parse_index_log
      return parse_index_log(self.get_all_output())

  return AutoindexWrapper()
