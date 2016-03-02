#!/usr/bin/env python
# MosflmIndex.py
#   Copyright (C) 2014 Diamond Light Source, Graeme Winter & Richard Gildea
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# A wrapper for Mosflm indexing - this will provide functionality to:
#
# Index the lattce.
#

import os
import sys
import copy
import shutil
import math

if not os.environ.has_key('XIA2_ROOT'):
  raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
  sys.path.append(os.environ['XIA2_ROOT'])

from Driver.DriverFactory import DriverFactory
from Decorators.DecoratorFactory import DecoratorFactory

from Handlers.Streams import Chatter
from Handlers.Executables import Executables
#from Handlers.Files import FileHandler


from Wrappers.CCP4.MosflmHelpers import _parse_mosflm_index_output

def MosflmIndex(DriverType = None, indxr_print = True):
  '''Factory for MosflmIndex wrapper classes, with the specified
  Driver type.'''

  DriverInstance = DriverFactory.Driver(DriverType)
  CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, 'ccp4')

  class MosflmIndexWrapper(CCP4DriverInstance.__class__):
    '''A wrapper for Mosflm indexing - which will provide
    functionality for deciding the beam centre and indexing the
    diffraction pattern.'''

    def __init__(self):

      # generic things
      CCP4DriverInstance.__class__.__init__(self)

      if Executables.get('ipmosflm'):
        self.set_executable(Executables.get('ipmosflm'))
      else:
        self.set_executable(os.path.join(
            os.environ['CCP4'], 'bin', 'ipmosflm'))

      # local parameters used in autoindexing
      self._mosflm_autoindex_sol = 0
      self._mosflm_autoindex_thresh = None
      self._mosflm_spot_file = None

      self._images = []

      self._reverse_phi = False
      self._template = None
      self._directory = None
      self._beam_centre = None
      self._wavelength = None
      self._distance = None
      self._unit_cell = None
      self._space_group_number = None
      self._solution_number = 0
      self._threshold = 20.0

      self._solutions = { }

      return

    def set_images(self, images):
      self._images = list(images)

    def set_reverse_phi(self, reverse_phi):
      self._reverse_phi = reverse_phi

    def set_directory(self, directory):
      self._directory = directory

    def set_template(self, template):
      self._template = template

    def set_beam_centre(self, beam_centre):
      self._beam_centre = beam_centre

    def set_wavelength(self, wavelength):
      self._wavelength = wavelength

    def set_distance(self, distance):
      self._distance = abs(distance)

    def set_unit_cell(self, unit_cell):
      self._unit_cell

    def set_space_group_number(self, space_group_number):
      self._space_group_number = space_group_number

    def set_threshold(self, threshold):
      self._threshold = threshold

    def set_solution_number(self, solution_number):
      self._solution_number = solution_number

    def run(self):
      '''Run mosflm indexing'''

      assert len(self._images) > 0
      self._images.sort()

      self.start()

      if self._reverse_phi:
        self.input('detector reversephi')

      assert self._template is not None and self._directory is not None
      self.input('template "%s"' %self._template)
      self.input('directory "%s"' %self._directory)
      self.input('newmat xiaindex.mat')

      if self._beam_centre is not None:
        self.input('beam %f %f' %tuple(self._beam_centre))
      if self._wavelength is not None:
        self.input('wavelength %f' %self._wavelength)
      if self._distance is not None:
        self.input('distance %f' %self._distance)
      if self._unit_cell is not None:
        self.input('cell %f %f %f %f %f %f' %self._unit_cell)
      if self._space_group_number is not None:
        self.input('symmetry %d' %self._space_group_number)

      for i in self._images:
        if self._solution_number > 0:
          self.input(
              'autoindex dps refine image %d thresh %d solu %d' % \
              (i, self._threshold, self._solution_number))
        else:
          self.input(
              'autoindex dps refine image %d thresh %d' % \
              (i, self._threshold))

      for i in self._images:
        self.input('mosaic estimate %d' % i)
        self.input('go')

      self.close_wait()

      #sweep = self.get_indexer_sweep_name()
      #FileHandler.record_log_file(
          #'%s INDEX' % (sweep), self.get_log_file())

      # check for errors
      self.check_for_errors()

      # ok now we're done, let's look through for some useful stuff
      output = self.get_all_output()

      self._solutions = _parse_mosflm_index_output(output)

      self._refined_cell = None
      self._refined_beam_centre = None
      self._lattice = None
      self._mosaic_spreads = []
      self._refined_detector_distance = None
      for o in output:
        if 'Final cell (after refinement)' in o:
          self._refined_cell = tuple(map(float, o.split()[-6:]))
        if 'Beam coordinates of' in o:
          self._refined_beam_centre = tuple(map(float, o.split()[-2:]))
        # FIXED this may not be there if this is a repeat indexing!
        if 'Symmetry:' in o:
          self._lattice = o.split(':')[1].split()[0]

        # so we have to resort to this instead...
        if 'Refining solution #' in o:
          from cctbx.sgtbx.bravais_types import bravais_lattice
          self._indexed_space_group_number = int(o.split(')')[0].split()[-1])
          self._lattice = str(bravais_lattice(number=self._indexed_space_group_number))

        if 'The mosaicity has been estimated' in o:
          ms = float(o.split('>')[1].split()[0])
          self._mosaic_spreads.append(ms)

        if 'The mosaicity estimation has not worked for some' in o:
          # this is a problem... in particular with the
          # mosflm built on linux in CCP4 6.0.1...
          # FIXME this should be a specific kind of
          # exception e.g. an IndexError
          # if microcrystal mode, just assume for the moment mosaic
          # spread is 0.5 degrees...
          raise IndexingError, 'mosaicity estimation failed'

        # mosflm doesn't refine this in autoindexing...
        if 'Crystal to detector distance of' in o:
          self._refined_detector_distance = float(o.split()[5].replace('mm', ''))

        # but it does complain if it is different to the header
        # value - so just use the input value in this case...
        if 'Input crystal to detector distance' in o \
           and 'does NOT agree with' in o:
          self._refined_detector_distance = self._distance

        if 'parameters have been set to' in o:
          self._raster = map(int, o.split()[-5:])

        if '(currently SEPARATION' in o:
          self._separation = map(float, o.replace(')', '').split()[-2:])

        # get the resolution estimate out...
        if '99% have resolution' in o:
          self._resolution_estimate = float(o.split()[-2])

    def get_solutions(self):
      return self._solutions

    def get_refined_unit_cell(self):
      return self._refined_cell

    def get_refined_beam_centre(self):
      return self._refined_beam_centre

    def get_lattice(self):
      return self._lattice

    def get_indexed_space_group_number(self):
      return self._indexed_space_group_number

    def get_mosaic_spreads(self):
      return self._mosaic_spreads

    def get_refined_distance(self):
      return self._refined_detector_distance

    def get_raster(self):
      return self._raster

    def get_separation(self):
      return self._separation

    def get_resolution_estimate(self):
      return self._resolution_estimate

  return MosflmIndexWrapper()
