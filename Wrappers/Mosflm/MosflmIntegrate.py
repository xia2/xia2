#!/usr/bin/env python
# MosflmIntegrate.py
#   Copyright (C) 2014 Diamond Light Source, Graeme Winter & Richard Gildea
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# A wrapper for Mosflm indexing - this will provide functionality to:
#
# Index the lattce.
#

from __future__ import absolute_import, division

import copy
import math
import os

from xia2.Decorators.DecoratorFactory import DecoratorFactory
from xia2.Driver.DriverFactory import DriverFactory
from xia2.Wrappers.CCP4.MosflmHelpers import (_parse_mosflm_integration_output,
                                              _parse_summary_file)

def MosflmIntegrate(DriverType = None, indxr_print = True):
  '''Factory for MosflmIntegrate wrapper classes, with the specified
  Driver type.'''

  DriverInstance = DriverFactory.Driver(DriverType)
  CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, 'ccp4')

  class MosflmIntegrateWrapper(CCP4DriverInstance.__class__):
    '''A wrapper for Mosflm indexing - which will provide
    functionality for deciding the beam centre and indexing the
    diffraction pattern.'''

    def __init__(self):

      # generic things
      CCP4DriverInstance.__class__.__init__(self)

      self.set_executable(os.path.join(
          os.environ['CCP4'], 'bin', 'ipmosflm'))

      # local parameters used in autoindexing
      self._mosflm_autoindex_sol = 0
      self._mosflm_autoindex_thresh = None
      self._mosflm_spot_file = None
      self._mosflm_hklout = None

      self._images = []

      self._reverse_phi = False
      self._template = None
      self._directory = None
      self._beam_centre = None
      self._wavelength = None
      self._distance = None
      self._unit_cell = None
      self._space_group_number = None
      self._refine_profiles = True
      self._threshold = 20.0
      self._pname = None
      self._xname = None
      self._dname = None
      self._exclude_ice = False
      self._exclude_regions = None
      self._instructions = []
      self._input_mat_file = None
      self._output_mat_file = None
      self._mosaic = None
      self._gain = None
      self._d_min = None
      self._d_max = None
      self._mask = None
      self._lim_x = None
      self._lim_y = None
      self._fix_mosaic = False
      self._pre_refinement = False

      self._parameters = { }

      self._bgsig_too_large = False
      self._getprof_error = False
      self._batches_out = None
      self._mosaic_spreads = None
      self._spot_status = None
      self._residuals = None
      self._postref_result = {}
      self._nref = None
      self._detector_gain_error = False
      self._suggested_gain = None

    def set_image_range(self, image_range):
      self._image_range = image_range

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
      self._unit_cell = unit_cell

    def set_space_group_number(self, space_group_number):
      self._space_group_number = space_group_number

    def set_threshold(self, threshold):
      self._threshold = threshold

    def set_refine_profiles(self, refine_profiles):
      self._refine_profiles = refine_profiles

    def set_exclude_ice(self, exclude_ice):
      self._exclude_ice = exclude_ice

    def set_exclude_regions(self, exclude_regions):
      self._exclude_regions = exclude_regions

    def add_instruction(self, instruction):
      self._instructions.append(instruction)

    def set_pname_xname_dname(self, pname, xname, dname):
      self._pname = pname
      self._xname = xname
      self._dname = dname

    def set_input_mat_file(self, mat_file):
      self._input_mat_file = mat_file

    def set_output_mat_file(self, mat_file):
      self._output_mat_file = mat_file

    def set_mosaic(self, mosaic):
      self._mosaic = mosaic

    def set_gain(self, gain):
      self._gain = gain

    def set_d_min(self, d_min):
      self._d_min = d_min

    def set_d_max(self, d_max):
      self._d_max = d_max

    def set_mask(self, mask):
      self._mask = mask

    def set_limits(self, lim_x, lim_y):
      self._lim_x = lim_x
      self._lim_y = lim_y

    def set_fix_mosaic(self, fix_mosaic):
      self._fix_mosaic = fix_mosaic

    def set_pre_refinement(self, pre_refinement):
      self._pre_refinement = pre_refinement

    def update_parameters(self, parameters):
      self._parameters.update(parameters)

    def get_per_image_statistics(self):
      return self._per_image_statistics

    def run(self):
      '''Run mosflm integration'''

      assert self._space_group_number is not None

      summary_file = 'summary_%s.log' %self._space_group_number
      self.add_command_line('SUMMARY')
      self.add_command_line(summary_file)

      self.start()

      if not self._refine_profiles:
        self.input('profile nooptimise')

      if [self._pname, self._xname, self._dname].count(None) == 0:
        self.input('harvest on')
        self.input('pname %s' %self._pname)
        self.input('xname %s' %self._xname)
        self.input('dname %s' %self._dname)

      if self._reverse_phi:
        self.input('detector reversephi')

      assert self._template is not None and self._directory is not None
      self.input('template "%s"' %self._template)
      self.input('directory "%s"' %self._directory)

      if self._exclude_ice:
        for record in open(os.path.abspath(os.path.join(
            os.path.dirname(__file__), '..', '..',
            'Data', 'ice-rings.dat'))).readlines():
          resol = tuple(map(float, record.split()[:2]))
          self.input('resolution exclude %.2f %.2f' % (resol))

      if self._exclude_regions is not None:
        for upper, lower in self._exclude_regions:
          self.input('resolution exclude %.2f %.2f' % (upper, lower))

      for instruction in self._instructions:
        self.input(instruction)

      self.input('matrix %s' %self._input_mat_file)

      assert self._beam_centre is not None
      assert self._distance is not None
      assert self._mosaic is not None
      self.input('beam %f %f' %tuple(self._beam_centre))
      self.input('distance %f' %self._distance)
      self.input('mosaic %f' %self._mosaic)
      if self._unit_cell is not None:
        self.input('cell %f %f %f %f %f %f' %self._unit_cell)

      self.input('refinement include partials')

      if self._wavelength is not None:
        self.input('wavelength %f' %self._wavelength)

      if self._parameters:
        for p, v in self._parameters.items():
          self.input('%s %s' % (p, str(v)))

      self.input('symmetry %d' %self._space_group_number)

      if self._gain is not None:
        self.input('gain %5.2f' %self._gain)

      # check for resolution limits
      if self._d_min is not None:
        if self._d_max is not None:
          self.input('resolution %f %f' %(self._d_min, self._d_max))
        else:
          self.input('resolution %f' %self._d_min)

      if self._mask is not None:
        record = 'limits quad'
        for m in self._mask:
          record += ' %.1f %.1f' % m
        self.input(record)

      # set up the integration
      self.input('postref fix all')
      self.input('postref maxresidual 5.0')

      if self._lim_x is not None and self._lim_y is not None:
        self.input('limits xscan %f yscan %f' % (self._lim_x, self._lim_y))

      if self._fix_mosaic:
        self.input('postref fix mosaic')

      #self.input('separation close')

      ## XXX FIXME this is a horrible hack - I at least need to
      ## sand box this ...
      #if self.get_header_item('detector') == 'raxis':
        #self.input('adcoffset 0')

      genfile = os.path.join(os.environ['CCP4_SCR'],
                             '%d_mosflm.gen' % self.get_xpid())

      self.input('genfile %s' % genfile)

      # add an extra chunk of orientation refinement

      # XXX FIXME
      if self._pre_refinement:
        a, b = self._image_range
        if b - a > 3:
          b = a + 3

        self.input('postref multi segments 1')
        self.input('process %d %d' % (a, b))
        self.input('go')

        self.input('postref nosegment')

        if self._fix_mosaic:
          self.input('postref fix mosaic')

      self.input('separation close')
      self.input(
          'process %d %d' %(self._image_range[0], self._image_range[1]))

      self.input('go')

      # that should be everything
      self.close_wait()

      # get the log file
      output = self.get_all_output()

      integrated_images_first = 1.0e6
      integrated_images_last = -1.0e6

      # look for major errors

      for i in range(len(output)):
        o = output[i]
        if 'LWBAT: error in ccp4_lwbat' in o:
          raise RuntimeError('serious mosflm error - inspect %s' % \
                self.get_log_file())

      mosaics = []

      for i in range(len(output)):
        o = output[i]

        if 'Integrating Image' in o:
          batch = int(o.split()[2])
          if batch < integrated_images_first:
            integrated_images_first = batch
          if batch > integrated_images_last:
            integrated_images_last = batch

        if 'Smoothed value for refined mosaic' in o:
          mosaics.append(float(o.split()[-1]))

        if 'ERROR IN DETECTOR GAIN' in o:

          self._detector_gain_error = True

          # look for the correct gain
          for j in range(i, i + 10):
            if output[j].split()[:2] == ['set', 'to']:
              gain = float(output[j].split()[-1][:-1])

              # check that this is not the input
              # value... Bug # 3374

              if self._gain:

                if math.fabs(gain - self._gain) > 0.02:
                  self._suggested_gain = gain

              else:
                self._suggested_gain = gain

        # FIXME if mosaic spread refines to a negative value
        # once the lattice has passed the triclinic postrefinement
        # test then fix this by setting "POSTREF FIX MOSAIC" and
        # restarting.

        if 'Smoothed value for refined mosaic spread' in o:
          mosaic = float(o.split()[-1])
          if mosaic < 0.0:
            raise IntegrationError('negative mosaic spread')

        if 'WRITTEN OUTPUT MTZ FILE' in o:
          self._mosflm_hklout = os.path.join(
              self.get_working_directory(),
              output[i + 1].split()[-1])

        if 'Number of Reflections' in o:
          self._nref = int(o.split()[-1])

        # if a BGSIG error happened try not refining the
        # profile and running again...

        if 'BGSIG too large' in o:
          self._bgsig_too_large = True

        if 'An unrecoverable error has occurred in GETPROF' in o:
          self._getprof_error = True

        if 'MOSFLM HAS TERMINATED EARLY' in o:
          raise RuntimeError(
                'integration failed: reason unknown (log %s)' % \
                self.get_log_file())

      if not self._mosflm_hklout:
        raise RuntimeError('processing abandoned')

      self._batches_out = (integrated_images_first, integrated_images_last)

      self._mosaic_spreads = mosaics

      self._per_image_statistics = _parse_mosflm_integration_output(output)

      # inspect the output for e.g. very high weighted residuals

      images = sorted(self._per_image_statistics.keys())

      # FIXME bug 2175 this should probably look at the distribution
      # of values rather than the peak, since this is probably a better
      # diagnostic of a poor lattice.

      residuals = []
      for i in images:
        if 'weighted_residual' in self._per_image_statistics[i]:
          residuals.append(self._per_image_statistics[i]['weighted_residual'])

      self._residuals = residuals

      try:
        self._postref_result = _parse_summary_file(
          os.path.join(self.get_working_directory(), summary_file))
      except AssertionError:
        self._postref_result = { }

      return self._mosflm_hklout

    def get_hklout(self):
      return self._mosflm_hklout

    def get_nref(self):
      return self._nref

    def get_bgsig_too_large(self):
      return self._bgsig_too_large

    def get_getprof_error(self):
      return self._getprof_error

    def get_batches_out(self):
      return self._batches_out

    def get_mosaic_spreads(self):
      return self._mosaic_spreads

    def get_spot_status(self):
      return self._spot_status

    def get_residuals(self):
      return self._residuals

    def get_postref_result(self):
      return self._postref_result

    def get_detector_gain_error(self):
      return self._detector_gain_error

    def get_suggested_gain(self):
      return self._suggested_gain

  return MosflmIntegrateWrapper()
