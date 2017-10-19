#!/usr/bin/env python
# MosflmRefineCell.py
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

import os
import copy

from xia2.Schema.Exceptions.BadLatticeError import BadLatticeError
from xia2.Schema.Exceptions.NegativeMosaicError import NegativeMosaicError

from xia2.Driver.DriverFactory import DriverFactory
from xia2.Decorators.DecoratorFactory import DecoratorFactory

from xia2.Handlers.Streams import Chatter, Debug

def MosflmRefineCell(DriverType = None, indxr_print = True):
  '''Factory for MosflmRefineCell wrapper classes, with the specified
  Driver type.'''

  DriverInstance = DriverFactory.Driver(DriverType)
  CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, 'ccp4')

  class MosflmRefineCellWrapper(CCP4DriverInstance.__class__):
    '''A wrapper for Mosflm cell refinement'''

    def __init__(self):

      # generic things
      CCP4DriverInstance.__class__.__init__(self)

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
      self._input_mat_file = None
      self._output_mat_file = None
      self._gain = None
      self._mosaic = None
      self._resolution = None
      self._fix_mosaic = False
      self._sdfac = None
      self._add_autoindex = False
      self._lim_x = None
      self._lim_y = None
      self._ignore_cell_refinement_failure = False
      self._parameters = {}

      self._refined_beam_centre = None
      self._refined_distance = None
      self._refined_distance2 = None
      self._refined_distortion_tilt = None
      self._refined_distortion_twist = None
      self._refined_mosaic = None
      self._refined_unit_cell = None
      self._raster = None
      self._cell_refinement_ok = False
      self._separation = None

    def set_images(self, images):
      self._images = list(images)

    def set_reverse_phi(self, reverse_phi):
      self._reverse_phi = reverse_phi

    def set_directory(self, directory):
      self._directory = directory

    def set_template(self, template):
      self._template = template

    def set_beam_centre(self, beam_centre):
      self._beam_centre = tuple(beam_centre)

    def set_wavelength(self, wavelength):
      self._wavelength = wavelength

    def set_distance(self, distance):
      self._distance = abs(distance)

    def set_unit_cell(self, unit_cell):
      self._unit_cell

    def set_space_group_number(self, space_group_number):
      self._space_group_number = space_group_number

    def set_input_mat_file(self, mat_file):
      self._input_mat_file = mat_file

    def set_output_mat_file(self, mat_file):
      self._output_mat_file = mat_file

    def set_gain(self, gain):
      self._gain = gain

    def set_mosaic(self, mosaic):
      self._mosaic = mosaic

    def set_resolution(self, resolution):
      self._resolution = resolution

    def set_fix_mosaic(self, fix_mosaic):
      self._fix_mosaic = fix_mosaic

    def set_sdfac(self, sdfac):
      self._sdfac = sdfac

    def set_limits(self, lim_x, lim_y):
      self._lim_x = lim_x
      self._lim_y = lim_y

    def set_add_autoindex(self, add_autoindex):
      self._add_autoindex = add_autoindex

    def set_ignore_cell_refinement_failure(self,
                                           ignore_cell_refinement_failure):
      self._ignore_cell_refinement_failure = ignore_cell_refinement_failure

    def update_parameters(self, parameters):
      self._parameters.update(parameters)

    def run(self):
      '''Run mosflm cell refinement'''

      assert len(self._images) > 0

      self.start()

      if self._gain is not None:
        self.input('gain %5.2f' % self._gain)

      if self._reverse_phi:
        self.input('detector reversephi')

      assert self._template is not None and self._directory is not None
      assert self._input_mat_file is not None and \
          self._output_mat_file is not None
      assert self._mosaic is not None
      self.input('template "%s"' %self._template)
      self.input('directory "%s"' %self._directory)
      self.input('matrix %s' %self._input_mat_file)
      self.input('newmat %s' %self._output_mat_file)

      if self._beam_centre is not None:
        self.input('beam %f %f' %self._beam_centre)
      if self._wavelength is not None:
        self.input('wavelength %f' %self._wavelength)
      if self._distance is not None:
        self.input('distance %f' %self._distance)
      if self._space_group_number is not None:
        self.input('symmetry %d' %self._space_group_number)

      self.input('mosaic %f' %self._mosaic)

      if self._resolution is not None:
        self.input('resolution %f' % self._resolution)

      if self._fix_mosaic:
        self.input('postref fix mosaic')

      if self._sdfac is not None:
        self.input('postref sdfac %f' %self._sdfac)

      # belt + braces mode - only to be used when considering failover,
      # will run an additional step of autoindexing prior to cell
      # refinement, to be used only after proving that not going it
      # will result in cell refinement failure - will use the first
      # wedge... N.B. this is only useful if the indexer is Labelit
      # not Mosflm...

      if self._add_autoindex:
        cri = self._images[0]
        for j in range(cri[0], 1 + cri[1]):
          self.input('autoindex dps refine image %d' % j)
        self.input('go')

      if self._parameters:
        self.input('!parameters from autoindex run')
        for p, v in self._parameters.items():
          self.input('%s %s' % (p, str(v)))

      if self._lim_x is not None and self._lim_y is not None:
        self.input('limits xscan %f yscan %f' % (self._lim_x, self._lim_y))

      self.input('separation close')
      self.input('refinement residual 15.0')
      self.input('refinement include partials')

      self._reorder_cell_refinement_images()

      self.input('postref multi segments %d repeat 10' % \
                 len(self._images))

      self.input('postref maxresidual 5.0')

      genfile = os.path.join(os.environ['CCP4_SCR'],
                             '%d_mosflm.gen' % self.get_xpid())

      self.input('genfile %s' % genfile)

      for cri in self._images:
        self.input('process %d %d' % cri)
        self.input('go')

      # that should be everything
      self.close_wait()

      # get the log file
      output = self.get_all_output()
      # then look to see if the cell refinement worked ok - if it
      # didn't then this may indicate that the lattice was wrongly
      # selected.

      self._cell_refinement_ok = False

      for o in output:

        if 'Cell refinement is complete' in o:
          self._cell_refinement_ok = True

      if not self._cell_refinement_ok:
        if not self._ignore_cell_refinement_failure:
          return [0.0], [0.0]

      rms_values_last = None
      rms_values = None

      new_cycle_number = 0
      new_rms_values = { }
      new_image_counter = None
      new_ignore_update = False

      parse_cycle = 1
      parse_image = 0

      background_residual = { }

      for i in range(len(output)):
        o = output[i]

        if 'Processing will be aborted' in o:
          raise BadLatticeError('cell refinement failed')

        if 'An unrecoverable error has occurred in MOSFLM' in o:
          raise BadLatticeError('cell refinement failed')

        if 'Processing Image' in o:
          new_image_counter = int(o.split()[2])

        if 'As this is near to the start' in o:
          new_ignore_update = True

        if 'Post-refinement will use partials' in o:
          if new_ignore_update:
            new_ignore_update = False
          else:
            new_cycle_number += 1
            new_rms_values[new_cycle_number] = { }

        if 'Final rms residual' in o:
          rv = float(o.replace('mm', ' ').split()[3])
          new_rms_values[new_cycle_number][new_image_counter] = rv

        if 'Rms positional error (mm) as a function of' in o and True:
          images = []
          cycles = []
          rms_values = { }

          j = i + 1

          while output[j].split():
            if 'Image' in output[j]:
              for image in map(int, output[j].replace(
                  'Image', '').split()):
                images.append(image)
            else:
              cycle = int(output[j].replace(
                  'Cycle', '').split()[0])

              if not cycle in cycles:
                cycles.append(cycle)
                rms_values[cycle] = []

              record = [output[j][k:k + 6] \
                        for k in range(
                  11, len(output[j]), 6)]

              data = []
              for r in record:
                if r.strip():
                  data.append(r.strip())
                record = data

              try:
                values = map(float, record)
                for v in values:
                  rms_values[cycle].append(v)
              except ValueError:
                Debug.write(
                    'Error parsing %s as floats' % \
                    output[j][12:])

            j += 1

          for cycle in new_rms_values.keys():
            images = new_rms_values[cycle].keys()
            images.sort()
            rms_values[cycle] = []
            for i in images:
              rms_values[cycle].append(
                  new_rms_values[cycle][i])

          if cycles:
            rms_values_last = rms_values[max(cycles)]
          else:
            rms_values_last = None

        # look for "error" type problems

        if 'is greater than the maximum allowed' in o and \
               'FINAL weighted residual' in o:

          Debug.write('Large weighted residual... ignoring')

        if 'INACCURATE CELL PARAMETERS' in o:

          # get the inaccurate cell parameters in question
          parameters = output[i + 3].lower().split()

          # and the standard deviations - so we can decide
          # if it really has failed

          sd_record = output[i + 5].replace(
              'A', ' ').replace(',', ' ').split()
          sds = map(float, [sd_record[j] for j in range(1, 12, 2)])

          Debug.write('Standard deviations:')
          Debug.write('A     %4.2f  B     %4.2f  C     %4.2f' % \
                      (tuple(sds[:3])))
          Debug.write('Alpha %4.2f  Beta  %4.2f  Gamma %4.2f' % \
                      (tuple(sds[3:6])))

          Debug.write(
              'In cell refinement, the following cell parameters')
          Debug.write(
              'have refined poorly:')
          for p in parameters:
            Debug.write('... %s' % p)

          Debug.write(
              'However, will continue to integration.')

        if 'One or more cell parameters has changed by more' in o:
          # this is a more severe example of the above problem...
          Debug.write(
              'Cell refinement is unstable...')

          raise BadLatticeError('Cell refinement failed')

        # other possible problems in the cell refinement - a
        # negative mosaic spread, for instance

        if 'Refined mosaic spread (excluding safety factor)' in o:
          mosaic = float(o.split()[-1])

          if mosaic < 0.00:
            Debug.write('Negative mosaic spread (%5.2f)' %
                        mosaic)

            raise NegativeMosaicError('refinement failed')

      parse_cycle = 1
      parse_image = 0

      background_residual = { }

      for i, o in enumerate(output):

        if 'Processing Image' in o:
          parse_image = int(o.split()[2])

        if 'Repeating the entire run' in o:
          parse_cycle += 1

        if 'Background residual' in o:

          res = float(o.replace('residual=', '').split()[8])

          if not parse_cycle in background_residual:
            background_residual[parse_cycle] = { }
          background_residual[parse_cycle][parse_image] = res

        if 'Cell refinement is complete' in o:
          j = i + 2
          refined_cell = map(float, output[j].split()[2:])
          error = map(float, output[j + 1].split()[1:])

          names = ['A', 'B', 'C', 'Alpha', 'Beta', 'Gamma']

          Debug.write('Errors in cell parameters (relative %)')

          for j in range(6):
            Debug.write('%s\t%7.3f %5.3f %.3f' % \
                        (names[j], refined_cell[j],
                         error[j],
                         100.0 * error[j] / refined_cell[j]))

        if 'Refined cell' in o:
          refined_cell = tuple(map(float, o.split()[-6:]))
          self._refined_unit_cell = refined_cell

        # FIXME with these are they really on one line?

        if 'Detector distance as a' in o:
          j = i + 1
          while output[j].strip() != '':
            j += 1
          distances = map(float, output[j - 1].split()[2:])
          distance = 0.0
          for d in distances:
            distance += d
          distance /= len(distances)
          # XXX FIXME not sure why there are two separate distances extracted
          # from the log file, and which one is the "correct" one
          self._refined_distance2 = distance

        if 'YSCALE as a function' in o:
          j = i + 1
          while output[j].strip() != '':
            j += 1
          yscales = map(float, output[j - 1].split()[2:])
          yscale = 0.0
          for y in yscales:
            yscale += y
          yscale /= len(yscales)
          self._refined_distortion_yscale = yscale

        if 'Final optimised raster parameters:' in o:
          self._raster = o.split(':')[1].strip()

        if 'Separation parameters updated to' in o:
          tokens = o.replace('mm', ' ').split()
          self._separation = (tokens[4], tokens[8])

        if 'XCEN    YCEN  XTOFRA' in o:
          numbers = output[i + 1].split()
          self._refined_beam_centre = (numbers[0], numbers[1])
          self._refined_distance = float(numbers[3]) # XXX duplicate of above?
          self._refined_distortion_tilt = numbers[5]
          self._refined_distortion_twist = numbers[6]

        if 'Refined mosaic spread' in o:
          self._refined_mosaic = float(o.split()[-1])

      self._rms_values = rms_values
      self._background_residual = background_residual

      return rms_values, background_residual

    def _reorder_cell_refinement_images(self):
      if not self._images:
        raise RuntimeError('no cell refinement images to reorder')

      hashmap = { }

      for m in self._images:
        hashmap[m[0]] = m[1]

      keys = hashmap.keys()
      keys.sort()

      cell_ref_images = [(k, hashmap[k]) for k in keys]
      self._images = cell_ref_images

    def get_rms_values(self):
      return self._rms_values

    def get_background_residual(self):
      return self._background_residual

    def get_refined_unit_cell(self):
      return self._refined_unit_cell

    def get_refined_beam_centre(self):
      return self._refined_beam_centre

    def get_refined_distance(self):
      return self._refined_distance

    def get_refined_distance2(self):
      return self._refined_distance2

    def get_raster(self):
      return self._raster

    def get_separation(self):
      return self._separation

    def get_refined_distortion_yscale(self):
      return self._refined_distortion_yscale

    def get_refined_distortion_tilt(self):
      return self._refined_distortion_tilt

    def get_refined_distortion_twist(self):
      return self._refined_distortion_twist

    def get_refined_mosaic(self):
      return self._refined_mosaic

    def cell_refinement_ok(self):
      return self._cell_refinement_ok

  return MosflmRefineCellWrapper()
