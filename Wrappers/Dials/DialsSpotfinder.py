#!/usr/bin/env python
# DialsSpotfinder.py
#
#   Copyright (C) 2013 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Find spots for autoindexing using the DIALS code; this will probably be 
# renamed to Spotfinder at some point.

from __future__ import division

def DialsSpotfinder(DriverType = None):
  '''A factory for DialsSpotfinderWrapper classes.'''

  from Driver.DriverFactory import DriverFactory
  DriverInstance = DriverFactory.Driver(DriverType)

  class DialsSpotfinderWrapper(DriverInstance.__class__):

    def __init__(self):
      DriverInstance.__class__.__init__(self)

      self.set_executable('dials.spotfinder')
      
      return

    def __call__(self, fp, images):
      from Handlers.Streams import Debug
      Debug.write('Running dials.spotfinder to find spots')

      spotfinder_images = [fp.get_image_name(i) for i in images]
      self.add_command_line(spotfinder_images)
      self.add_command_line('-o')
      self.add_command_line('spots.pickle')
      
      self.start()
      self.close_wait()

      # FIXME I should really gather some interesting information about
      import os
      return os.path.join(self.get_working_directory(), 'spots.pickle')

  return DialsSpotfinderWrapper()
