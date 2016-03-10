#!/usr/bin/env python
# Mosflm.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 23rd June 2006
#
# A wrapper for the data processing program Mosflm, with the following
# methods to provide functionality:

import os
import sys
import shutil
import math
import exceptions

from xia2.Background.Background import Background
from xia2.Driver.DriverFactory import DriverFactory
from xia2.Decorators.DecoratorFactory import DecoratorFactory

# interfaces that this will present
from xia2.Schema.Interfaces.Indexer import Indexer
from xia2.Schema.Interfaces.Integrater import Integrater

# output streams &c.
from xia2.Handlers.Streams import Chatter, Debug, Journal
from xia2.Handlers.Citations import Citations
from xia2.Handlers.Flags import Flags
from xia2.Handlers.Executables import Executables
from xia2.Handlers.Files import FileHandler

# helpers
from xia2.Wrappers.CCP4.MosflmHelpers import \
     _parse_mosflm_integration_output, decide_integration_resolution_limit, \
     _parse_mosflm_index_output, standard_mask, \
     _get_indexing_solution_number, detector_class_to_mosflm, \
     _parse_summary_file

# things we are moving towards...
from xia2.Modules.Indexer.IndexerSelectImages import index_select_images_lone, \
     index_select_images_user

from xia2.Modules.GainEstimater import gain

from xia2.lib.bits import auto_logfiler, mean_sd
from xia2.lib.SymmetryLib import lattice_to_spacegroup

from xia2.Experts.MatrixExpert import transmogrify_matrix, \
     get_reciprocal_space_primitive_matrix, reindex_sym_related
from xia2.Experts.ResolutionExperts import mosflm_mtz_to_list, \
     bin_o_tron, digest
from xia2.Experts.MissetExpert import MosflmMissetExpert

# exceptions
from xia2.Schema.Exceptions.BadLatticeError import BadLatticeError
from xia2.Schema.Exceptions.NegativeMosaicError import NegativeMosaicError
from xia2.Schema.Exceptions.IndexingError import IndexingError
from xia2.Schema.Exceptions.IntegrationError import IntegrationError

# other classes which are necessary to implement the integrater
# interface (e.g. new version, with reindexing as the finish...)
from xia2.Wrappers.CCP4.Reindex import Reindex
from xia2.Wrappers.CCP4.Sortmtz import Sortmtz
from xia2.Wrappers.XIA.Diffdump import Diffdump
from xia2.Wrappers.XIA.Printpeaks import Printpeaks

# cell refinement image helpers
from xia2.Modules.Indexer.MosflmCheckIndexerSolution import \
     mosflm_check_indexer_solution

# jiffy functions for means, standard deviations and outliers
from xia2.lib.bits import meansd, remove_outliers

def Mosflm(DriverType = None):
  '''A factory for MosflmWrapper classes.'''

  DriverInstance = DriverFactory.Driver(DriverType)
  CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, 'ccp4')

  class MosflmWrapper(CCP4DriverInstance.__class__,
                      Indexer,
                      Integrater):
    '''A wrapper for Mosflm, using the CCP4-ified Driver.'''

    def __init__(self):
      # generic things
      CCP4DriverInstance.__class__.__init__(self)

      if Executables.get('ipmosflm'):
        self.set_executable(Executables.get('ipmosflm'))
      else:
        self.set_executable(os.path.join(
            os.environ['CCP4'], 'bin', 'ipmosflm'))

      Indexer.__init__(self)
      Integrater.__init__(self)

      # store the Driver instance used for this for use when working
      # in parallel - use with DriverFactory.Driver(DriverType)
      self._mosflm_driver_type = DriverType

      # local parameters used in autoindexing
      self._mosflm_autoindex_sol = 0
      self._mosflm_autoindex_thresh = None
      self._mosflm_spot_file = None

      # local parameters used in cell refinement
      self._mosflm_cell_ref_images = None
      self._mosflm_cell_ref_resolution = None
      self._mosflm_cell_ref_double_mosaic = False

      # belt + braces for very troublesome cases - this will only
      # be used in failover / microcrystal mode
      self._mosflm_cell_ref_add_autoindex = False

      # and the calculation of the missetting angles
      self._mosflm_misset_expert = None

      # local parameters used in integration
      self._mosflm_refine_profiles = True
      self._mosflm_postref_fix_mosaic = False
      self._mosflm_rerun_integration = False
      self._mosflm_hklout = None

      self._mosflm_gain = None

      return

    def _index_prepare(self):

      if self._indxr_images == []:
        self._index_select_images()

      if self._mosflm_autoindex_thresh is None and \
             Flags.get_microcrystal():
        self._mosflm_autoindex_thresh = 5

      return

    def _index_select_images(self):
      '''Select correct images based on image headers.'''

      if Flags.get_small_molecule():
        return self._index_select_images_small_molecule()

      if Flags.get_microcrystal():
        return self._index_select_images_microcrystal()

      phi_width = self.get_phi_width()
      images = self.get_matching_images()

      if Flags.get_interactive():
        selected_images = index_select_images_user(phi_width, images,
                                                   Chatter)
      else:
        selected_images = index_select_images_lone(phi_width, images)

      for image in selected_images:
        Debug.write('Selected image %s' % image)
        self.add_indexer_image_wedge(image)

      return

    def _index_select_images_small_molecule(self):
      '''Select correct images based on image headers. This one is for
      when you have small molecule data so want more images.'''

      phi_width = self.get_phi_width()
      images = self.get_matching_images()

      Debug.write('Selected image %s' % images[0])

      self.add_indexer_image_wedge(images[0])

      offset = images[0] - 1

      # add an image every 15 degrees up to 90 degrees

      for j in range(6):

        image_number = offset + int(15 * (j + 1) / phi_width)

        if not image_number in images:
          break

        Debug.write('Selected image %s' % image_number)
        self.add_indexer_image_wedge(image_number)

      return

    def _index_select_images_microcrystal(self):
      '''Select images for more difficult cases e.g. microcrystal
      work. Will apply (up to) 20 images to the task.'''

      phi_width = self.get_phi_width()
      images = self.get_matching_images()

      spacing = max(1, int(len(images) / 20))

      selected = []

      for j in range(0, len(images), spacing):
        selected.append(images[j])

      for image in selected[:20]:
        self.add_indexer_image_wedge(image)

      return

    def _refine_select_images(self, mosaic):
      '''Select images for cell refinement based on image headers.'''

      cell_ref_images = []

      phi_width = self.get_phi_width()
      min_images = max(3, int(2 * mosaic / phi_width))

      if min_images > 9:
        min_images = 9

      images = self.get_matching_images()

      if len(images) < 3 * min_images:
        cell_ref_images.append((min(images), max(images)))
        return cell_ref_images

      cell_ref_images = []
      cell_ref_images.append((images[0], images[min_images - 1]))

      ideal_last = int(90.0 / phi_width) + min_images

      if ideal_last < len(images):
        ideal_middle = int(45.0 / phi_width) - min_images // 2
        cell_ref_images.append((images[ideal_middle - 1],
                                images[ideal_middle - 2 + min_images]))
        cell_ref_images.append((images[ideal_last - min_images],
                                images[ideal_last]))

      else:
        middle = int((max(images) + min(images) - min_images) // 2)
        cell_ref_images.append((middle - 1,
                                middle - 2 + min_images))
        cell_ref_images.append((images[-min_images],
                                images[-1]))

      return cell_ref_images

    def _refine_select_twenty(self, mosaic):
      '''Select images for cell refinement - first 20 in the sweep.'''

      cell_ref_images = []

      images = self.get_matching_images()

      cell_ref_images = []

      if len(images) > 20:
        cell_ref_images.append((images[0], images[19]))
      else:
        cell_ref_images.append((images[0], images[-1]))

      return cell_ref_images

    def _index(self):
      '''Implement the indexer interface.'''

      Citations.cite('mosflm')

      self.reset()
      auto_logfiler(self)

      from xia2.lib.bits import unique_elements
      _images = unique_elements(self._indxr_images)
      images_str = ', '.join(map(str, _images))

      cell_str = None
      if self._indxr_input_cell:
        cell_str = '%.2f %.2f %.2f %.2f %.2f %.2f' % \
                    self._indxr_input_cell

      if self._indxr_sweep_name:

        if len(self._fp_directory) <= 50:
          dirname = self._fp_directory
        else:
          dirname = '...%s' % self._fp_directory[-46:]

        Journal.block(
            'autoindexing', self._indxr_sweep_name, 'mosflm',
            {'images':images_str,
             'target cell':self._indxr_input_cell,
             'target lattice':self._indxr_input_lattice,
             'template':self._fp_template,
             'directory':dirname})

      task = 'Autoindex from images:'

      for i in _images:
        task += ' %s' % self.get_image_name(i)

      self.set_task(task)

      auto_logfiler(self)
      self.start()

      self.input('template "%s"' % self.get_template())
      self.input('directory "%s"' % self.get_directory())
      self.input('newmat xiaindex.mat')

      if self.get_beam_prov() == 'user':
        self.input('beam %f %f' % self.get_beam_centre())

      if self.get_wavelength_prov() == 'user':
        self.input('wavelength %f' % self.get_wavelength())

      if self.get_distance_prov() == 'user':
        self.input('distance %f' % self.get_distance())

      if self._indxr_input_cell:
        self.input('cell %f %f %f %f %f %f' % \
                   self._indxr_input_cell)

      if self._indxr_input_lattice != None:
        spacegroup_number = lattice_to_spacegroup(
            self._indxr_input_lattice)
        self.input('symmetry %d' % spacegroup_number)

      if not self._mosflm_autoindex_thresh:

        try:

          min_peaks = 200

          Debug.write('Aiming for at least %d spots...' % min_peaks)

          thresholds = []

          for i in _images:

            p = Printpeaks()
            p.set_working_directory(self.get_working_directory())
            auto_logfiler(p)
            p.set_image(self.get_image_name(i))
            thresh = p.threshold(min_peaks)

            Debug.write('Autoindex threshold for image %d: %d' % \
                        (i, thresh))

            thresholds.append(thresh)

          thresh = min(thresholds)
          self._mosflm_autoindex_thresh = thresh

        except exceptions.Exception, e:
          print str(e) #XXX this should disappear!
          Debug.write('Error computing threshold: %s' % str(e))
          Debug.write('Using default of 20.0')
          thresh = 20.0

      else:
        thresh = self._mosflm_autoindex_thresh

      Debug.write('Using autoindex threshold: %d' % thresh)

      for i in _images:

        if self._mosflm_autoindex_sol:
          self.input(
              'autoindex dps refine image %d thresh %d solu %d' % \
              (i, thresh, self._mosflm_autoindex_sol))
        else:
          self.input(
              'autoindex dps refine image %d thresh %d' % \
              (i, thresh))

      # now forget this to prevent weird things happening later on
      if self._mosflm_autoindex_sol:
        self._mosflm_autoindex_sol = 0

      # trac 1150 - want to estimate mosaic spread from all images then
      # calculate the average - though what happens if one of the chosen
      # images is BLANK?

      for i in _images:
        self.input('mosaic estimate %d' % i)
        self.input('go')

      self.close_wait()

      sweep = self.get_indexer_sweep_name()
      FileHandler.record_log_file(
          '%s INDEX' % (sweep), self.get_log_file())

      output = self.get_all_output()

      mosaic_spreads = []

      for o in output:
        if 'Final cell (after refinement)' in o:
          indxr_cell = tuple(map(float, o.split()[-6:]))

          if min(list(indxr_cell)) < 10.0 and \
             indxr_cell[2] / indxr_cell[0] > 6:

            Debug.write(
                'Unrealistic autoindexing solution: ' +
                '%.2f %.2f %.2f %.2f %.2f %.2f' % indxr_cell)

            # tweak some parameters and try again...
            self._mosflm_autoindex_thresh *= 1.5
            self.set_indexer_done(False)

            return

      intgr_params = { }

      # look up other possible indexing solutions (not well - in
      # standard settings only!) This is moved earlier as it could
      # result in returning if Mosflm has selected the wrong
      # solution!

      try:
        self._indxr_other_lattice_cell = _parse_mosflm_index_output(
            output)

        # Change 27/FEB/08 to support user assigned spacegroups
        if self._indxr_user_input_lattice:
          lattice_to_spacegroup_dict = {
              'aP':1, 'mP':3, 'mC':5, 'oP':16, 'oC':20, 'oF':22,
              'oI':23, 'tP':75, 'tI':79, 'hP':143, 'hR':146,
              'cP':195, 'cF':196, 'cI':197}
          for k in self._indxr_other_lattice_cell.keys():
            if lattice_to_spacegroup_dict[k] > \
                   lattice_to_spacegroup_dict[
                self._indxr_input_lattice]:
              del(self._indxr_other_lattice_cell[k])

        # check that the selected unit cell matches - and if
        # not raise a "horrible" exception

        # FIXME why are these and "False" commented out - see also in (e)

        if self._indxr_input_cell:

          for o in output:
            if 'Final cell (after refinement)' in o:
              indxr_cell = tuple(map(float, o.split()[-6:]))

          for j in range(6):
            if math.fabs(self._indxr_input_cell[j] -
                         indxr_cell[j]) > 2.0:
              Chatter.write(
                  'Mosflm autoindexing did not select ' +
                  'correct (target) unit cell')
              raise RuntimeError, \
                    'something horrible happened in indexing'

      except RuntimeError, e:
        # check if mosflm rejected a solution we have it
        if 'horribl' in str(e):
          # ok it did - time to break out the big guns...
          if not self._indxr_input_cell:
            raise RuntimeError, \
                  'error in solution selection when not preset'

          self._mosflm_autoindex_sol = _get_indexing_solution_number(
              output,
              self._indxr_input_cell,
              self._indxr_input_lattice)

          # set the fact that we are not done...
          self.set_indexer_done(False)

          # and return - hopefully this will restart everything
          return
        else:
          raise e

      space_group_number = None
      beam_centre = None
      detector_distance = None
      cell = None

      for o in output:
        if 'Final cell (after refinement)' in o:
          cell = tuple(map(float, o.split()[-6:]))
        if 'Beam coordinates of' in o:
          beam_centre = tuple(map(float, o.split()[-2:]))

        # FIXED this may not be there if this is a repeat indexing!
        if 'Symmetry:' in o:
          self._indxr_lattice = o.split(':')[1].split()[0]

        # so we have to resort to this instead...
        if 'Refining solution #' in o:
          space_group_number = int(o.split(')')[0].split()[-1])
          lattice_to_spacegroup_dict = {'aP':1, 'mP':3, 'mC':5,
                                        'oP':16, 'oC':20, 'oF':22,
                                        'oI':23, 'tP':75, 'tI':79,
                                        'hP':143, 'hR':146,
                                        'cP':195, 'cF':196,
                                        'cI':197}

          spacegroup_to_lattice = { }
          for k in lattice_to_spacegroup_dict.keys():
            spacegroup_to_lattice[
                lattice_to_spacegroup_dict[k]] = k
          self._indxr_lattice = spacegroup_to_lattice[space_group_number]

        # in here I need to check if the mosaic spread estimation
        # has failed. If it has it is likely that the selected
        # lattice has too high symmetry, and the "next one down"
        # is needed

        if 'The mosaicity has been estimated' in o:
          ms = float(o.split('>')[1].split()[0])
          mosaic_spreads.append(ms)

        # alternatively this could have failed - which happens
        # sometimes...

        if 'The mosaicity estimation has not worked for some' in o:
          # this is a problem... in particular with the
          # mosflm built on linux in CCP4 6.0.1...
          # FIXME this should be a specific kind of
          # exception e.g. an IndexError
          # if microcrystal mode, just assume for the moment mosaic
          # spread is 0.5 degrees...

          if Flags.get_microcrystal():
            self._indxr_mosaic = 0.5
          else:
            raise IndexingError, 'mosaicity estimation failed'

        # or it may alternatively look like this...

        if 'The mosaicity has NOT been estimated' in o:
          # then consider setting it do a default value...
          # equal to the oscillation width (a good guess)

          phi_width = self.get_phi_width()

          Chatter.write(
              'Mosaic estimation failed, so guessing at %4.2f' % \
              phi_width)

          # only consider this if we have thus far no idea on the
          # mosaic spread...

          if not mosaic_spreads:
            mosaic_spreads.append(phi_width)

        # mosflm doesn't refine this in autoindexing...
        if 'Crystal to detector distance of' in o:
          detector_distance = float(o.split()[5].replace('mm', ''))

        # but it does complain if it is different to the header
        # value - so just use the input value in this case...
        if 'Input crystal to detector distance' in o \
           and 'does NOT agree with' in o:
          detector_distance = self.get_distance()

        # record raster parameters and so on, useful for the
        # cell refinement etc - this will be added to a
        # payload dictionary of mosflm integration keywords
        # look for "measurement box parameters"

        if 'parameters have been set to' in o:
          intgr_params['raster'] = map(
              int, o.split()[-5:])

        if '(currently SEPARATION' in o:
          intgr_params['separation'] = map(
              float, o.replace(')', '').split()[-2:])

        # get the resolution estimate out...
        if '99% have resolution' in o:
          self._indxr_resolution_estimate = float(
              o.split()[-2])

      # compute mosaic as mean(mosaic_spreads)

      self._indxr_mosaic = sum(mosaic_spreads) / len(mosaic_spreads)

      self._indxr_payload['mosflm_integration_parameters'] = intgr_params

      self._indxr_payload['mosflm_orientation_matrix'] = open(
          os.path.join(self.get_working_directory(),
                       'xiaindex.mat'), 'r').readlines()

      import copy
      from dxtbx.model.detector_helpers import set_mosflm_beam_centre
      from xia2.Wrappers.Mosflm.AutoindexHelpers import set_distance
      from xia2.Wrappers.Mosflm.AutoindexHelpers import crystal_model_from_mosflm_mat
      from cctbx import sgtbx, uctbx
      from dxtbx.model.crystal import crystal_model_from_mosflm_matrix

      # update the beam centre (i.e. shift the origin of the detector)
      detector = copy.deepcopy(self.get_detector())
      beam = copy.deepcopy(self.get_beam_obj())
      set_mosflm_beam_centre(detector, beam, beam_centre)
      if detector_distance is not None:
        set_distance(detector, detector_distance)

      # make a dxtbx crystal_model object from the mosflm matrix
      space_group = sgtbx.space_group_info(number=space_group_number).group()
      crystal_model = crystal_model_from_mosflm_mat(
        self._indxr_payload['mosflm_orientation_matrix'],
        unit_cell=uctbx.unit_cell(tuple(cell)),
        space_group=space_group)

      # construct an experiment_list
      from dxtbx.model.experiment.experiment_list import Experiment, ExperimentList
      experiment = Experiment(beam=beam,
                              detector=detector,
                              goniometer=self.get_goniometer(),
                              scan=self.get_scan(),
                              crystal=crystal_model,
                              )

      experiment_list = ExperimentList([experiment])
      self.set_indexer_experiment_list(experiment_list)
      return

    def _index_finish(self):
      '''Check that the autoindexing gave a convincing result, and
      if not (i.e. it gave a centred lattice where a primitive one
      would be correct) pick up the correct solution.'''

      if self._indxr_input_lattice:
        return

      if self.get_indexer_sweep():
        if self.get_indexer_sweep().get_user_lattice():
          return

      try:
        status, lattice, matrix, cell = mosflm_check_indexer_solution(
            self)
      except:
        return

      if status is False or status is None:
        return

      # ok need to update internals...

      self._indxr_lattice = lattice
      self._indxr_cell = cell

      Debug.write('Inserting solution: %s ' % lattice +
                  '%6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % cell)

      self._indxr_replace(lattice, cell)

      self._indxr_payload['mosflm_orientation_matrix'] = matrix

      return

    def _mosflm_generate_raster(self, _images):
      from xia2.Wrappers.Mosflm.GenerateRaster import GenerateRaster
      gr = GenerateRaster()
      gr.set_working_directory(self.get_working_directory())
      return gr(self.get_integrater_indexer(), _images)

    def _integrate_prepare(self):
      '''Prepare for integration - note that if there is a reason
      why this is needed to be run again, set self._intgr_prepare_done
      as False.'''

      self.digest_template()

      if not self._mosflm_gain and self.get_gain():
        self._mosflm_gain = self.get_gain()

      # if pilatus override GAIN to 1.0

      if self.get_imageset().get_detector()[0].get_type() == 'SENSOR_PAD':
        self._mosflm_gain = 1.0

      indxr = self.get_integrater_indexer()

      if not self._mosflm_cell_ref_images:
        mosaic = indxr.get_indexer_mosaic()

        if Flags.get_microcrystal():
          self._mosflm_cell_ref_images = self._refine_select_twenty(
              mosaic)
        else:
          self._mosflm_cell_ref_images = self._refine_select_images(
              mosaic)

      # generate human readable output

      images_str = '%d to %d' % self._mosflm_cell_ref_images[0]
      for i in self._mosflm_cell_ref_images[1:]:
        images_str += ', %d to %d' % i

      cell_str = '%.2f %.2f %.2f %.2f %.2f %.2f' % \
                 indxr.get_indexer_cell()

      if len(self._fp_directory) <= 50:
        dirname = self._fp_directory
      else:
        dirname = '...%s' % self._fp_directory[-46:]

      Journal.block('cell refining', self._intgr_sweep_name, 'mosflm',
                    {'images':images_str,
                     'start cell':cell_str,
                     'target lattice':indxr.get_indexer_lattice(),
                     'template':self._fp_template,
                     'directory':dirname})

      # end generate human readable output

      # in here, check to see if we have the raster parameters and
      # separation from indexing - if we used a different indexer
      # we may not, so if this is the case call a function to generate
      # them...

      if not indxr.get_indexer_payload(
          'mosflm_integration_parameters'):

        # generate a list of first images

        images = []
        for cri in self._mosflm_cell_ref_images:
          images.append(cri[0])

        images.sort()

        integration_params = self._mosflm_generate_raster(images)

        # copy them over to where they are needed

        if integration_params.has_key('separation'):
          self.set_integrater_parameter(
              'mosflm', 'separation',
              '%f %f' % tuple(integration_params['separation']))
        if integration_params.has_key('raster'):
          self.set_integrater_parameter(
              'mosflm', 'raster',
              '%d %d %d %d %d' % tuple(integration_params['raster']))

      # next test the cell refinement with the correct lattice
      # and P1 and see how the numbers stack up...

      # copy the cell refinement resolution in...

      self._mosflm_cell_ref_resolution = indxr.get_indexer_resolution()

      Debug.write(
          'Using resolution limit of %.2f for cell refinement' % \
          self._mosflm_cell_ref_resolution)

      # now trap NegativeMosaicError exception - once!

      try:

        # now reading the background residual values as well - if these
        # are > 10 it would indicate that the images are blank (assert)
        # so ignore from the analyis / comparison

        if Flags.get_no_lattice_test() or \
               self.get_integrater_sweep().get_user_lattice():
          rms_deviations_p1 = []
          br_p1 = []
        else:
          self.reset()
          auto_logfiler(self)
          rms_deviations_p1, br_p1 = self._mosflm_test_refine_cell(
              'aP')

        self.reset()
        auto_logfiler(self)
        rms_deviations, br = self._mosflm_refine_cell()

      except NegativeMosaicError, nme:

        if self._mosflm_cell_ref_double_mosaic:

          # reset flag; half mosaic; raise BadLatticeError
          Debug.write('Mosaic negative even x2 -> BadLattice')
          self._mosflm_cell_ref_double_mosaic = False
          raise BadLatticeError, 'negative mosaic spread'

        else:

          # set flag, double mosaic, return to try again
          Debug.write('Mosaic negative -> try x2')
          self._mosflm_cell_ref_double_mosaic = True
          self.set_integrater_prepare_done(False)

          return

      if not self.get_integrater_prepare_done():
        return

      # compare cell refinement with lattice and in P1

      images = []
      for cri in self._mosflm_cell_ref_images:
        for j in range(cri[0], cri[1] + 1):
          images.append(j)

      if rms_deviations and rms_deviations_p1:
        cycles = []
        j = 1
        while rms_deviations.has_key(j) and \
              rms_deviations_p1.has_key(j):
          cycles.append(j)
          j += 1
        Debug.write('Cell refinement comparison:')
        Debug.write('Image   correct   triclinic')
        ratio = 0.0

        ratios = []

        for c in cycles:
          Debug.write('Cycle %d' % c)
          for j, image in enumerate(images):

            background_residual = max(br_p1[c][image],
                                      br[c][image])

            if background_residual > 10:
              Debug.write('. %4d   %.2f     %.2f (ignored)' % \
                          (images[j], rms_deviations[c][j],
                           rms_deviations_p1[c][j]))
              continue

            Debug.write('. %4d   %.2f     %.2f' % \
                        (images[j], rms_deviations[c][j],
                         rms_deviations_p1[c][j]))

            ratio += rms_deviations[c][j] / rms_deviations_p1[c][j]
            ratios.append(
                (rms_deviations[c][j] / rms_deviations_p1[c][j]))

        Debug.write('Average ratio: %.2f' % \
                    (ratio / len(ratios)))

        if (ratio / (max(cycles) * len(images))) > \
               Flags.get_rejection_threshold() and \
               not self.get_integrater_sweep().get_user_lattice():
          raise BadLatticeError, 'incorrect lattice constraints'

      else:
        Debug.write('Cell refinement in P1 failed... or was not run')

      cell_str = '%.2f %.2f %.2f %.2f %.2f %.2f' % \
                 self._intgr_cell

      Journal.entry({'refined cell':cell_str})

      if not self._intgr_wedge:
        images = self.get_matching_images()
        self.set_integrater_wedge(min(images),
                                  max(images))


      return

    def _integrate(self):
      '''Implement the integrater interface.'''

      # cite the program
      Citations.cite('mosflm')

      images_str = '%d to %d' % self._intgr_wedge
      cell_str = '%.2f %.2f %.2f %.2f %.2f %.2f' % self._intgr_cell

      if len(self._fp_directory) <= 50:
        dirname = self._fp_directory
      else:
        dirname = '...%s' % self._fp_directory[-46:]

      Journal.block(
          'integrating', self._intgr_sweep_name, 'mosflm',
          {'images':images_str,
           'cell':cell_str,
           'lattice':self.get_integrater_indexer().get_indexer_lattice(),
           'template':self._fp_template,
           'directory':dirname,
           'resolution':'%.2f' % self._intgr_reso_high})

      self._mosflm_rerun_integration = False

      wd = self.get_working_directory()

      try:

        self.reset()
        auto_logfiler(self)

        if self.get_integrater_sweep_name():
          pname, xname, dname = self.get_integrater_project_info()
          FileHandler.record_log_file(
              '%s %s %s %s mosflm integrate' % \
              (self.get_integrater_sweep_name(),
               pname, xname, dname),
              self.get_log_file())

        if Flags.get_parallel() > 1:
          Debug.write('Parallel integration: %d jobs' %
                      Flags.get_parallel())
          self._mosflm_hklout = self._mosflm_parallel_integrate()
        else:
          self._mosflm_hklout = self._mosflm_integrate()

        # record integration output for e.g. BLEND.

        sweep = self.get_integrater_sweep_name()
        if sweep:
          FileHandler.record_more_data_file(
              '%s %s %s %s INTEGRATE' % (pname, xname, dname, sweep),
              self._mosflm_hklout)

      except IntegrationError, e:
        if 'negative mosaic spread' in str(e):
          if self._mosflm_postref_fix_mosaic:
            Chatter.write(
                'Negative mosaic spread - stopping integration')
            raise BadLatticeError, 'negative mosaic spread'

          Chatter.write(
              'Negative mosaic spread - rerunning integration')
          self.set_integrater_done(False)
          self._mosflm_postref_fix_mosaic = True

      if self._mosflm_rerun_integration and not Flags.get_quick():
        # make sure that this is run again...
        Chatter.write('Need to rerun the integration...')
        self.set_integrater_done(False)

      return self._mosflm_hklout

    def _integrate_finish(self):
      '''Finish the integration - if necessary performing reindexing
      based on the pointgroup and the reindexing operator.'''

      if self._intgr_reindex_operator is None and \
         self._intgr_spacegroup_number == lattice_to_spacegroup(
          self.get_integrater_indexer().get_indexer_lattice()):
        return self._mosflm_hklout

      if self._intgr_reindex_operator is None and \
         self._intgr_spacegroup_number == 0:
        return self._mosflm_hklout

      Debug.write('Reindexing to spacegroup %d (%s)' % \
                  (self._intgr_spacegroup_number,
                   self._intgr_reindex_operator))

      hklin = self._mosflm_hklout
      reindex = Reindex()
      reindex.set_working_directory(self.get_working_directory())
      auto_logfiler(reindex)

      reindex.set_operator(self._intgr_reindex_operator)

      if self._intgr_spacegroup_number:
        reindex.set_spacegroup(self._intgr_spacegroup_number)

      hklout = '%s_reindex.mtz' % hklin[:-4]

      reindex.set_hklin(hklin)
      reindex.set_hklout(hklout)
      reindex.reindex()

      return hklout

    def _mosflm_test_refine_cell(self, test_lattice):
      '''Test performing cell refinement in with a different
      lattice to the one which was selected by the autoindex
      procedure. This should not change anything in the class.'''

      indxr = self.get_integrater_indexer()

      lattice = indxr.get_indexer_lattice()
      mosaic = indxr.get_indexer_mosaic()
      beam = indxr.get_indexer_beam_centre()
      distance = indxr.get_indexer_distance()
      matrix = indxr.get_indexer_payload('mosflm_orientation_matrix')

      phi_width = self.get_phi_width()
      if mosaic < 0.25 * phi_width:
        mosaic = 0.25 * phi_width

      input_matrix = ''
      for m in matrix:
        input_matrix += '%s\n' % m

      new_matrix = transmogrify_matrix(lattice, input_matrix,
                                       test_lattice,
                                       self.get_wavelength(),
                                       self.get_working_directory())

      spacegroup_number = lattice_to_spacegroup(test_lattice)

      if not self._mosflm_cell_ref_images:
        raise RuntimeError, 'wedges must be assigned already'

      open(os.path.join(self.get_working_directory(),
                        'test-xiaindex-%s.mat' % lattice),
           'w').write(new_matrix)

      self.start()

      if self._mosflm_gain:
        self.input('gain %5.2f' % self._mosflm_gain)

      self.input('template "%s"' % self.get_template())
      self.input('directory "%s"' % self.get_directory())

      self.input('matrix test-xiaindex-%s.mat' % lattice)
      self.input('newmat test-xiarefine.mat')

      self.input('beam %f %f' % beam)
      self.input('distance %f' % distance)

      self.input('symmetry %s' % spacegroup_number)

      # FIXME 18/JUN/08 - it may help to have an overestimate
      # of the mosaic spread in here as it *may* refine down
      # better than up... - this is not a good idea as it may
      # also not refine at all! - 12972 # integration failed

      # Bug # 3103
      if self._mosflm_cell_ref_double_mosaic:
        self.input('mosaic %f' % (2.0 * mosaic))
      else:
        self.input('mosaic %f' % mosaic)

      # if set, use the resolution for cell refinement - see
      # bug # 2078...

      if self._mosflm_cell_ref_resolution and not \
             Flags.get_microcrystal():
        self.input('resolution %f' % \
                   self._mosflm_cell_ref_resolution)

      if self._mosflm_postref_fix_mosaic:
        self.input('postref fix mosaic')

      if Flags.get_microcrystal():
        self.input('postref sdfac 2.0')

      # note well that the beam centre is coming from indexing so
      # should be already properly handled

      if self.get_wavelength_prov() == 'user':
        self.input('wavelength %f' % self.get_wavelength())

      # belt + braces mode - only to be used when considering failover,
      # will run an additional step of autoindexing prior to cell
      # refinement, to be used only after proving that not going it
      # will result in cell refinement failure - will use the first
      # wedge... N.B. this is only useful if the indexer is Labelit
      # not Mosflm...

      if self._mosflm_cell_ref_add_autoindex:
        assert(Flags.get_failover())
        cri = self._mosflm_cell_ref_images[0]
        for j in range(cri[0], 1 + cri[1]):
          self.input('autoindex dps refine image %d' % j)
        self.input('go')

      # get all of the stored parameter values
      parameters = self.get_integrater_parameters('mosflm')

      self.input('!parameters from autoindex run')
      for p in parameters.keys():
        self.input('%s %s' % (p, str(parameters[p])))

      detector = self.get_detector()
      detector_width, detector_height = detector[0].get_image_size_mm()

      lim_x = 0.5 * detector_width
      lim_y = 0.5 * detector_height

      Debug.write('Scanner limits: %.1f %.1f' % (lim_x, lim_y))
      self.input('limits xscan %f yscan %f' % (lim_x, lim_y))

      self.input('separation close')
      self.input('refinement residual 15.0')
      self.input('refinement include partials')

      self._reorder_cell_refinement_images()

      self.input('postref multi segments %d repeat 10' % \
                 len(self._mosflm_cell_ref_images))

      self.input('postref maxresidual 5.0')

      genfile = os.path.join(os.environ['CCP4_SCR'],
                             '%d_mosflm.gen' % self.get_xpid())

      self.input('genfile %s' % genfile)

      for cri in self._mosflm_cell_ref_images:
        self.input('process %d %d' % cri)
        self.input('go')

      # that should be everything
      self.close_wait()

      # get the log file
      output = self.get_all_output()

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

        if 'Processing Image' in o:
          new_image_counter = int(o.split()[2])
          parse_image = int(o.split()[2])

        if 'Repeating the entire run' in o:
          parse_cycle += 1

        if 'Background residual' in o:
          res = float(o.replace('residual=', '').split()[8])

          if not parse_cycle in background_residual:
            background_residual[parse_cycle] = { }
          background_residual[parse_cycle][parse_image] = res

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
              except ValueError, e:
                Debug.write(
                    'Error parsing %s as floats' % \
                    output[j][12:])

            j += 1


          # now transform back the new rms residual values
          # into the old structure... messy but effective!

          for cycle in new_rms_values.keys():
            images = new_rms_values[cycle].keys()
            images.sort()
            rms_values[cycle] = []
            for i in images:
              rms_values[cycle].append(
                  new_rms_values[cycle][i])

          rms_values_last = rms_values[max(cycles)]

      return rms_values, background_residual

    def _mosflm_refine_cell(self, set_spacegroup = None):
      '''Perform the refinement of the unit cell. This will populate
      all of the information needed to perform the integration.'''

      # FIXME this will die after #1285

      if not self.get_integrater_indexer():
        Debug.write('Replacing indexer of %s with self at %d' % \
                    (str(self.get_integrater_indexer()), __line__))
        self.set_integrater_indexer(self)

      indxr = self.get_integrater_indexer()

      if not indxr.get_indexer_payload('mosflm_orientation_matrix'):
        raise RuntimeError, 'unexpected situation in indexing'

      lattice = indxr.get_indexer_lattice()
      mosaic = indxr.get_indexer_mosaic()
      cell = indxr.get_indexer_cell()
      beam_centre = indxr.get_indexer_beam_centre()

      # bug # 3174 - if mosaic is very small (here defined to be
      # 0.25 x osc_width) then set to this minimum value.

      phi_width = self.get_phi_width()
      if mosaic < 0.25 * phi_width:
        mosaic = 0.25 * phi_width

      if indxr.get_indexer_payload('mosflm_beam_centre'):
        beam_centre = indxr.get_indexer_payload('mosflm_beam_centre')

      distance = indxr.get_indexer_distance()
      matrix = indxr.get_indexer_payload('mosflm_orientation_matrix')

      integration_params = indxr.get_indexer_payload(
          'mosflm_integration_parameters')

      if integration_params:
        if integration_params.has_key('separation'):
          self.set_integrater_parameter(
              'mosflm', 'separation',
              '%f %f' % tuple(integration_params['separation']))
        if integration_params.has_key('raster'):
          self.set_integrater_parameter(
              'mosflm', 'raster',
              '%d %d %d %d %d' % tuple(integration_params['raster']))

      indxr.set_indexer_payload('mosflm_integration_parameters', None)

      spacegroup_number = lattice_to_spacegroup(lattice)

      # copy these into myself for later reference, if indexer
      # is not myself - everything else is copied via the
      # cell refinement process...

      if indxr != self:
        from cctbx import sgtbx
        from dxtbx.model import crystal
        from dxtbx.model.detector_helpers import set_mosflm_beam_centre
        experiment = indxr.get_indexer_experiment_list()[0]
        set_mosflm_beam_centre(
          experiment.detector, experiment.beam, beam_centre)
        space_group = sgtbx.space_group_info(number=spacegroup_number).group()
        a, b, c = experiment.crystal.get_real_space_vectors()
        experiment.crystal = crystal.crystal_model(
          a, b, c, space_group=space_group)

      # FIXME surely these have been assigned further up?!

      if not self._mosflm_cell_ref_images:
        self._mosflm_cell_ref_images = self._refine_select_images(
            mosaic)

      f = open(os.path.join(self.get_working_directory(),
                            'xiaindex-%s.mat' % lattice), 'w')
      for m in matrix:
        f.write(m)
      f.close()

      # then start the cell refinement

      self.start()

      if self._mosflm_gain:
        self.input('gain %5.2f' % self._mosflm_gain)

      self.input('template "%s"' % self.get_template())
      self.input('directory "%s"' % self.get_directory())

      self.input('matrix xiaindex-%s.mat' % lattice)
      self.input('newmat xiarefine.mat')

      self.input('beam %f %f' % beam_centre)
      self.input('distance %f' % distance)

      if set_spacegroup:
        self.input('symmetry %s' % set_spacegroup)
      else:
        self.input('symmetry %s' % spacegroup_number)

      # FIXME 18/JUN/08 - it may help to have an overestimate
      # of the mosaic spread in here as it *may* refine down
      # better than up... - this is not a good idea as it may
      # also not refine at all! - 12972 # integration failed

      # Bug # 3103
      if self._mosflm_cell_ref_double_mosaic:
        self.input('mosaic %f' % (2.0 * mosaic))
      else:
        self.input('mosaic %f' % mosaic)

      if self._mosflm_postref_fix_mosaic:
        self.input('postref fix mosaic')

      # if set, use the resolution for cell refinement - see
      # bug # 2078...

      if self._mosflm_cell_ref_resolution and not \
             Flags.get_microcrystal():
        self.input('resolution %f' % \
                   self._mosflm_cell_ref_resolution)

      if Flags.get_microcrystal():
        self.input('postref sdfac 2.0')

      if self.get_wavelength_prov() == 'user':
        self.input('wavelength %f' % self.get_wavelength())

      # belt + braces mode - only to be used when considering failover,
      # will run an additional step of autoindexing prior to cell
      # refinement, to be used only after proving that not going it
      # will result in cell refinement failure - will use the first
      # wedge...

      if self._mosflm_cell_ref_add_autoindex:
        assert(Flags.get_failover())
        cri = self._mosflm_cell_ref_images[0]
        for j in range(cri[0], 1 + cri[1]):
          self.input('autoindex dps refine image %d' % j)
        self.input('go')

      parameters = self.get_integrater_parameters('mosflm')

      self.input('!parameters from autoindex run')
      for p in parameters.keys():
        self.input('%s %s' % (p, str(parameters[p])))

      self.input('separation close')
      self.input('refinement residual 15')
      self.input('refinement include partials')

      detector = self.get_detector()
      detector_width, detector_height = detector[0].get_image_size_mm()

      lim_x = 0.5 * detector_width
      lim_y = 0.5 * detector_height

      Debug.write('Scanner limits: %.1f %.1f' % (lim_x, lim_y))
      self.input('limits xscan %f yscan %f' % (lim_x, lim_y))

      self._reorder_cell_refinement_images()

      self.input('postref multi segments %d repeat 10' % \
                 len(self._mosflm_cell_ref_images))

      self.input('postref maxresidual 5.0')

      genfile = os.path.join(os.environ['CCP4_SCR'],
                             '%d_mosflm.gen' % self.get_xpid())

      self.input('genfile %s' % genfile)

      for cri in self._mosflm_cell_ref_images:
        self.input('process %d %d' % cri)
        self.input('go')

      # that should be everything
      self.close_wait()

      # get the log file
      output = self.get_all_output()

      # then look to see if the cell refinement worked ok - if it
      # didn't then this may indicate that the lattice was wrongly
      # selected.

      cell_refinement_ok = False

      for o in output:

        if 'Cell refinement is complete' in o:
          cell_refinement_ok = True

      if not cell_refinement_ok:
        if Flags.get_failover() and not \
               self._mosflm_cell_ref_add_autoindex:
          Debug.write('Repeating cell refinement...')
          self.set_integrater_prepare_done(False)
          self._mosflm_cell_ref_add_autoindex = True
          return [0.0], [0.0]

        Chatter.write(
            'Looks like cell refinement failed - more follows...')

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
          raise BadLatticeError, 'cell refinement failed'

        if 'An unrecoverable error has occurred in MOSFLM' in o:
          raise BadLatticeError, 'cell refinement failed'

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
              except ValueError, e:
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

          raise BadLatticeError, 'Cell refinement failed'

        # other possible problems in the cell refinement - a
        # negative mosaic spread, for instance

        if 'Refined mosaic spread (excluding safety factor)' in o:
          mosaic = float(o.split()[-1])

          if mosaic < 0.05:
            Debug.write('Negative mosaic spread (%5.2f)' %
                        mosaic)

            raise NegativeMosaicError, 'refinement failed'

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
          self._intgr_cell = refined_cell

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
          experiment = self.get_integrater_indexer(
            ).get_indexer_experiment_list()[0]
          from xia2.Wrappers.Mosflm.AutoindexHelpers import set_distance
          set_distance(experiment.detector, distance)

        if 'YSCALE as a function' in o:
          j = i + 1
          while output[j].strip() != '':
            j += 1
          yscales = map(float, output[j - 1].split()[2:])
          yscale = 0.0
          for y in yscales:
            yscale += y
          yscale /= len(yscales)

          self.set_integrater_parameter('mosflm',
                                        'distortion yscale',
                                        yscale)

        if 'Final optimised raster parameters:' in o:
          self.set_integrater_parameter('mosflm',
                                        'raster',
                                        o.split(':')[1].strip())

        if 'Separation parameters updated to' in o:
          tokens = o.replace('mm', ' ').split()
          self.set_integrater_parameter('mosflm',
                                        'separation',
                                        '%s %s' % \
                                        (tokens[4], tokens[8]))

        if 'XCEN    YCEN  XTOFRA' in o:
          numbers = output[i + 1].split()

          self.set_integrater_parameter('mosflm',
                                        'beam',
                                        '%s %s' % \
                                        (numbers[0], numbers[1]))
          self.set_integrater_parameter('mosflm',
                                        'distance',
                                        numbers[3])
          self.set_integrater_parameter('mosflm',
                                        'distortion tilt',
                                        numbers[5])
          self.set_integrater_parameter('mosflm',
                                        'distortion twist',
                                        numbers[6])

        if 'Refined mosaic spread' in o:
          indxr._indxr_mosaic = float(o.split()[-1])

      self.set_indexer_done(True)

      self.set_indexer_payload('mosflm_orientation_matrix', open(
          os.path.join(self.get_working_directory(),
                       'xiarefine.mat'), 'r').readlines())
      indxr.set_indexer_payload('mosflm_orientation_matrix', open(
          os.path.join(self.get_working_directory(),
                       'xiarefine.mat'), 'r').readlines())

      from xia2.Wrappers.Mosflm.AutoindexHelpers import crystal_model_from_mosflm_mat
      # make a dxtbx crystal_model object from the mosflm matrix
      experiment = self.get_integrater_indexer(
        ).get_indexer_experiment_list()[0]
      crystal_model = crystal_model_from_mosflm_mat(
        self._indxr_payload['mosflm_orientation_matrix'],
        unit_cell=refined_cell,
        space_group=experiment.crystal.get_space_group())
      experiment.crystal = crystal_model

      return rms_values, background_residual

    def _mosflm_integrate(self):
      '''Perform the actual integration, based on the results of the
      cell refinement or indexing (they have the equivalent form.)'''

      if not self.get_integrater_indexer():
        Debug.write('Replacing indexer of %s with self at %d' % \
                    (str(self.get_integrater_indexer()), __line__))
        self.set_integrater_indexer(self)

      indxr = self.get_integrater_indexer()

      if not indxr.get_indexer_payload('mosflm_orientation_matrix'):
        raise RuntimeError, 'unexpected situation in indexing'

      lattice = indxr.get_indexer_lattice()
      mosaic = indxr.get_indexer_mosaic()
      cell = indxr.get_indexer_cell()
      beam = indxr.get_indexer_beam_centre()
      distance = indxr.get_indexer_distance()
      matrix = indxr.get_indexer_payload('mosflm_orientation_matrix')

      integration_params = indxr.get_indexer_payload(
          'mosflm_integration_parameters')

      if integration_params:
        if integration_params.has_key('separation'):
          self.set_integrater_parameter(
              'mosflm', 'separation',
              '%f %f' % tuple(integration_params['separation']))
        if integration_params.has_key('raster'):
          self.set_integrater_parameter(
              'mosflm', 'raster',
              '%d %d %d %d %d' % tuple(integration_params['raster']))

      indxr.set_indexer_payload('mosflm_integration_parameters', None)

      spacegroup_number = lattice_to_spacegroup(lattice)

      f = open(os.path.join(self.get_working_directory(),
                            'xiaintegrate.mat'), 'w')
      for m in matrix:
        f.write(m)
      f.close()

      # then start the integration

      summary_file = 'summary_%s.log' % spacegroup_number

      self.add_command_line('SUMMARY')
      self.add_command_line(summary_file)

      self.start()

      if not self._mosflm_refine_profiles:
        self.input('profile nooptimise')

      pname, xname, dname = self.get_integrater_project_info()

      if pname != None and xname != None and dname != None:
        Debug.write('Harvesting: %s/%s/%s' % (pname, xname, dname))

        harvest_dir = os.path.join(os.environ['HARVESTHOME'],
                                   'DepositFiles', pname)

        if not os.path.exists(harvest_dir):
          Debug.write('Creating harvest directory...')
          os.makedirs(harvest_dir)

        # harvest file name will be %s.mosflm_run_start_end % dname

        self.input('harvest on')
        self.input('pname %s' % pname)
        self.input('xname %s' % xname)

        temp_dname = '%s_%s' % \
                     (dname, self.get_integrater_sweep_name())

        self.input('dname %s' % temp_dname)
        # self.input('ucwd')

      self.input('template "%s"' % self.get_template())
      self.input('directory "%s"' % self.get_directory())

      # check for ice - and if so, exclude (ranges taken from
      # XDS documentation)
      if self.get_integrater_ice() != 0:

        Debug.write('Excluding ice rings')

        for record in open(os.path.abspath(os.path.join(
            os.path.dirname(__file__), '..', '..',
            'Data', 'ice-rings.dat'))).readlines():

          resol = tuple(map(float, record.split()[:2]))
          self.input('resolution exclude %.2f %.2f' % (resol))

      # exclude specified resolution ranges
      if len(self.get_integrater_excluded_regions()) != 0:
        regions = self.get_integrater_excluded_regions()

        Debug.write('Excluding regions: %s' % `regions`)

        for upper, lower in regions:
          self.input('resolution exclude %.2f %.2f' % (upper, lower))

      mask = standard_mask(self.get_detector())
      for m in mask:
        self.input(m)

      self.input('matrix xiaintegrate.mat')

      self.input('beam %f %f' % beam)
      self.input('distance %f' % distance)
      self.input('symmetry %s' % spacegroup_number)
      self.input('mosaic %f' % mosaic)

      self.input('refinement include partials')

      if self.get_wavelength_prov() == 'user':
        self.input('wavelength %f' % self.get_wavelength())

      parameters = self.get_integrater_parameters('mosflm')
      for p in parameters.keys():
        self.input('%s %s' % (p, str(parameters[p])))

      if self._mosflm_gain:
        self.input('gain %5.2f' % self._mosflm_gain)

      # check for resolution limits
      if self._intgr_reso_high > 0.0:
        if self._intgr_reso_low:
          self.input('resolution %f %f' % (self._intgr_reso_high,
                                           self._intgr_reso_low))
        else:
          self.input('resolution %f' % self._intgr_reso_high)

      if Flags.get_mask():
        mask = Flags.get_mask().calculate_mask_mosflm(
            self.get_header())
        record = 'limits quad'
        for m in mask:
          record += ' %.1f %.1f' % m
        self.input(record)

      # set up the integration
      self.input('postref fix all')
      self.input('postref maxresidual 5.0')

      detector = self.get_detector()
      detector_width, detector_height = detector[0].get_image_size_mm()

      lim_x = 0.5 * detector_width
      lim_y = 0.5 * detector_height

      Debug.write('Scanner limits: %.1f %.1f' % (lim_x, lim_y))
      self.input('limits xscan %f yscan %f' % (lim_x, lim_y))

      if self._mosflm_postref_fix_mosaic:
        self.input('postref fix mosaic')

      self.input('separation close')

      ## XXX FIXME this is a horrible hack - I at least need to
      ## sand box this ...
      #if self.get_header_item('detector') == 'raxis':
        #self.input('adcoffset 0')

      offset = self.get_frame_offset()

      genfile = os.path.join(os.environ['CCP4_SCR'],
                             '%d_mosflm.gen' % self.get_xpid())

      self.input('genfile %s' % genfile)

      # add an extra chunk of orientation refinement

      if Flags.get_microcrystal():
        a = self._intgr_wedge[0] - offset
        if self._intgr_wedge[1] - self._intgr_wedge[0] > 20:
          b = a + 20
        else:
          b = self._intgr_wedge[1] - offset

        self.input('postref segment 1 fix all')
        self.input('process %d %d' % (a, b))
        self.input('go')
        self.input('postref nosegment')

        self.input('process %d %d block %d' % \
                   (self._intgr_wedge[0] - offset,
                    self._intgr_wedge[1] - offset,
                    1 + self._intgr_wedge[1] - self._intgr_wedge[0]))

      else:
        self.input('process %d %d' % (self._intgr_wedge[0] - offset,
                                      self._intgr_wedge[1] - offset))

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
          raise RuntimeError, 'serious mosflm error - inspect %s' % \
                self.get_log_file()

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

          # ignore for photon counting detectors

          if 'pilatus' in self.get_header_item('detector_class'):
            continue

          # look for the correct gain
          for j in range(i, i + 10):
            if output[j].split()[:2] == ['set', 'to']:
              gain = float(output[j].split()[-1][:-1])

              # check that this is not the input
              # value... Bug # 3374

              if self._mosflm_gain:

                if math.fabs(gain - self._mosflm_gain) > 0.02:

                  self.set_integrater_parameter(
                      'mosflm', 'gain', gain)
                  self.set_integrater_export_parameter(
                      'mosflm', 'gain', gain)
                  Debug.write('GAIN updated to %f' % gain)

                  self._mosflm_gain = gain
                  self._mosflm_rerun_integration = True

              else:

                self.set_integrater_parameter(
                    'mosflm', 'gain', gain)
                self.set_integrater_export_parameter(
                    'mosflm', 'gain', gain)
                Debug.write('GAIN found to be %f' % gain)

                self._mosflm_gain = gain
                self._mosflm_rerun_integration = True

        # FIXME if mosaic spread refines to a negative value
        # once the lattice has passed the triclinic postrefinement
        # test then fix this by setting "POSTREF FIX MOSAIC" and
        # restarting.

        if 'Smoothed value for refined mosaic spread' in o:
          mosaic = float(o.split()[-1])
          if mosaic < 0.0:
            raise IntegrationError, 'negative mosaic spread'

        if 'WRITTEN OUTPUT MTZ FILE' in o:
          self._mosflm_hklout = os.path.join(
              self.get_working_directory(),
              output[i + 1].split()[-1])

          Debug.write('Integration output: %s' % \
                      self._mosflm_hklout)

        if 'Number of Reflections' in o:
          self._intgr_n_ref = int(o.split()[-1])

        # if a BGSIG error happened try not refining the
        # profile and running again...

        if 'BGSIG too large' in o:
          if not self._mosflm_refine_profiles:
            raise RuntimeError, 'BGSIG error with profiles fixed'

          Debug.write(
              'BGSIG error detected - try fixing profile...')

          self._mosflm_refine_profiles = False
          self.set_integrater_done(False)

          return

        if 'An unrecoverable error has occurred in GETPROF' in o:
          Debug.write(
              'GETPROF error detected - try fixing profile...')
          self._mosflm_refine_profiles = False
          self.set_integrater_done(False)

          return

        if 'MOSFLM HAS TERMINATED EARLY' in o:
          Chatter.write('Mosflm has failed in integration')
          message = 'The input was:\n\n'
          for input in self.get_all_input():
            message += '  %s' % input
          Chatter.write(message)
          raise RuntimeError, \
                'integration failed: reason unknown (log %s)' % \
                self.get_log_file()

      if not self._mosflm_hklout:
        raise RuntimeError, 'processing abandoned'

      self._intgr_batches_out = (integrated_images_first,
                                 integrated_images_last)

      if mosaics and len(mosaics) > 0:
        self.set_integrater_mosaic_min_mean_max(
            min(mosaics), sum(mosaics) / len(mosaics), max(mosaics))
      else:
        m = indxr.get_indexer_mosaic()
        self.set_integrater_mosaic_min_mean_max(m, m, m)

      Chatter.write('Processed batches %d to %d' % \
                    self._intgr_batches_out)

      # write the report for each image as .*-#$ to Chatter -
      # detailed report will be written automagically to science...

      parsed_output = _parse_mosflm_integration_output(output)

      spot_status = _happy_integrate_lp(parsed_output)

      # inspect the output for e.g. very high weighted residuals

      images = parsed_output.keys()
      images.sort()

      max_weighted_residual = 0.0

      # FIXME bug 2175 this should probably look at the distribution
      # of values rather than the peak, since this is probably a better
      # diagnostic of a poor lattice.

      residuals = []
      for i in images:
        if parsed_output[i].has_key('weighted_residual'):
          residuals.append(parsed_output[i]['weighted_residual'])

      mean, sd = mean_sd(residuals)

      Chatter.write('Weighted RMSD: %.2f (%.2f)' % \
                    (mean, sd))

      for i in images:
        data = parsed_output[i]

        if data.has_key('weighted_residual'):

          if data['weighted_residual'] > max_weighted_residual:
            max_weighted_residual = data['weighted_residual']

      if len(spot_status) > 60:
        Chatter.write('Integration status per image (60/record):')
      else:
        Chatter.write('Integration status per image:')

      for chunk in [spot_status[i:i + 60] \
                    for i in range(0, len(spot_status), 60)]:
        Chatter.write(chunk)

      Chatter.write(
          '"o" => good        "%" => ok        "!" => bad rmsd')
      Chatter.write(
          '"O" => overloaded  "#" => many bad  "." => weak')
      Chatter.write(
          '"@" => abandoned')

      Chatter.write('Mosaic spread: %.3f < %.3f < %.3f' % \
                    self.get_integrater_mosaic_min_mean_max())

      # gather the statistics from the postrefinement

      try:
        postref_result = _parse_summary_file(
            os.path.join(self.get_working_directory(), summary_file))
      except AssertionError, e:
        postref_result = { }

      # now write this to a postrefinement log

      postref_log = os.path.join(self.get_working_directory(),
                                 'postrefinement.log')

      fout = open(postref_log, 'w')

      fout.write('$TABLE: Postrefinement for %s:\n' % \
                 self._intgr_sweep_name)
      fout.write('$GRAPHS: Missetting angles:A:1, 2, 3, 4: $$\n')
      fout.write('Batch PhiX PhiY PhiZ $$ Batch PhiX PhiY PhiZ $$\n')

      for image in sorted(postref_result):
        phix = postref_result[image].get('phix', 0.0)
        phiy = postref_result[image].get('phiy', 0.0)
        phiz = postref_result[image].get('phiz', 0.0)

        fout.write('%d %5.2f %5.2f %5.2f\n' % \
                   (image, phix, phiy, phiz))

      fout.write('$$\n')
      fout.close()

      if self.get_integrater_sweep_name():
        pname, xname, dname = self.get_integrater_project_info()
        FileHandler.record_log_file('%s %s %s %s postrefinement' % \
                                    (self.get_integrater_sweep_name(),
                                     pname, xname, dname),
                                    postref_log)

      return self._mosflm_hklout

    def _mosflm_parallel_integrate(self):
      '''Perform the integration as before, but this time as a
      number of parallel Mosflm jobs (hence, in separate directories)
      and including a step of pre-refinement of the mosaic spread and
      missets. This will all be kind of explicit and hence probably
      messy!'''

      # ok, in here try to get the missetting angles at two "widely
      # spaced" points, so that the missetting angle calculating
      # expert can do it's stuff.

      # FIXME remove this section?

      figured = False
      if figured:

        offset = self.get_frame_offset()
        start = self._intgr_wedge[0] - offset
        end = self._intgr_wedge[1] - offset
        next = start + \
               int(round(90.0 / self.get_header_item('phi_width')))

        if next > end:
          next = end

        end -= 3

        # right, run:

        wd = os.path.join(self.get_working_directory(),
                          'misset' % j)
        if not os.path.exists(wd):
          os.makedirs(wd)

        # create the Driver, configure
        job = DriverFactory.Driver(self._mosflm_driver_type)
        job.set_executable(self.get_executable())
        job.set_working_directory(wd)
        auto_logfiler(job)

      # FIXME why am I getting the cell constants and so on from the
      # indexer?! Because that is where the _integrate_prepare step
      # stores them... interesting!

      if not self.get_integrater_indexer():
        # should I raise a RuntimeError here?!
        Debug.write('Replacing indexer of %s with self at %d' % \
                    (str(self.get_integrater_indexer()), __line__))
        self.set_integrater_indexer(self)

      indxr = self.get_integrater_indexer()

      lattice = indxr.get_indexer_lattice()
      spacegroup_number = lattice_to_spacegroup(lattice)
      mosaic = indxr.get_indexer_mosaic()
      cell = indxr.get_indexer_cell()
      beam = indxr.get_indexer_beam_centre()
      distance = indxr.get_indexer_distance()
      matrix = indxr.get_indexer_payload('mosflm_orientation_matrix')

      # integration parameters - will have to be copied to all
      # of the running Mosflm instances...

      integration_params = indxr.get_indexer_payload(
          'mosflm_integration_parameters')

      if integration_params:
        if integration_params.has_key('separation'):
          self.set_integrater_parameter(
              'mosflm', 'separation',
              '%f %f' % tuple(integration_params['separation']))
        if integration_params.has_key('raster'):
          self.set_integrater_parameter(
              'mosflm', 'raster',
              '%d %d %d %d %d' % tuple(integration_params['raster']))

      indxr.set_indexer_payload('mosflm_integration_parameters', None)
      pname, xname, dname = self.get_integrater_project_info()

      # what follows below should (i) be run in separate directories
      # and (ii) be repeated N=parallel times.

      parallel = Flags.get_parallel()

      if not parallel:
        raise RuntimeError, 'parallel not set'
      if parallel < 2:
        raise RuntimeError, 'parallel not parallel: %s' % parallel

      jobs = []
      hklouts = []
      # reindex_ops = []
      nref = 0

      # calculate the chunks to use
      offset = self.get_frame_offset()
      start = self._intgr_wedge[0] - offset
      end = self._intgr_wedge[1] - offset

      left_images = 1 + end - start
      left_chunks = parallel
      chunks = []

      while left_images > 0:
        size = left_images // left_chunks
        chunks.append((start, start + size - 1))
        start += size
        left_images -= size
        left_chunks -= 1

      summary_files = []

      for j in range(parallel):

        # make some working directories, as necessary - chunk-(0:N-1)
        wd = os.path.join(self.get_working_directory(),
                          'chunk-%d' % j)
        if not os.path.exists(wd):
          os.makedirs(wd)

        # create the Driver, configure
        job = DriverFactory.Driver(self._mosflm_driver_type)
        job.set_executable(self.get_executable())
        job.set_working_directory(wd)

        auto_logfiler(job)

        # copy in the clibd/syminfo.lib to the working directory
        syminfo = os.path.join(os.environ['CLIBD'], 'syminfo.lib')
        shutil.copyfile(syminfo, os.path.join(wd, 'syminfo.lib'))

        # then tell the job about it
        job.set_working_environment('CLIBD', wd)

        l = indxr.get_indexer_lattice()

        # create the starting point
        f = open(os.path.join(wd, 'xiaintegrate-%s.mat' % l), 'w')
        for m in matrix:
          f.write(m)
        f.close()

        spacegroup_number = lattice_to_spacegroup(lattice)
        summary_file = 'summary_%s.log' % spacegroup_number
        job.add_command_line('SUMMARY')
        job.add_command_line(summary_file)

        summary_files.append(os.path.join(wd, summary_file))

        job.start()

        if not self._mosflm_refine_profiles:
          job.input('profile nooptimise')

        # N.B. for harvesting need to append N to dname.

        if pname != None and xname != None and dname != None:
          Debug.write('Harvesting: %s/%s/%s' %
                      (pname, xname, dname))

          harvest_dir = os.path.join(os.environ['HARVESTHOME'],
                                     'DepositFiles', pname)

          if not os.path.exists(harvest_dir):
            Debug.write('Creating harvest directory...')
            os.makedirs(harvest_dir)

          job.input('harvest on')
          job.input('pname %s' % pname)
          job.input('xname %s' % xname)

          temp_dname = '%s_%s' % \
                       (dname, self.get_integrater_sweep_name())

          job.input('dname %s' % temp_dname)

        job.input('template "%s"' % self.get_template())
        job.input('directory "%s"' % self.get_directory())

        # check for ice - and if so, exclude (ranges taken from
        # XDS documentation)
        if self.get_integrater_ice() != 0:

          Debug.write('Excluding ice rings')

          for record in open(os.path.abspath(os.path.join(
              os.path.dirname(__file__), '..', '..',
              'Data', 'ice-rings.dat'))).readlines():

            resol = tuple(map(float, record.split()[:2]))
            job.input('resolution exclude %.2f %.2f' % (resol))

        # exclude specified resolution ranges
        if len(self.get_integrater_excluded_regions()) != 0:
          regions = self.get_integrater_excluded_regions()

          Debug.write('Excluding regions: %s' % `regions`)

          for upper, lower in regions:
            job.input('resolution exclude %.2f %.2f' % \
                       (upper, lower))


        # generate the mask information from the detector class
        mask = standard_mask(self.get_detector())
        for m in mask:
          job.input(m)

        # suggestion from HRP 10/AUG/09
        job.input('matrix xiaintegrate-%s.mat' % l)
        # job.input('target xiaintegrate.mat')

        job.input('beam %f %f' % beam)
        job.input('distance %f' % distance)
        job.input('symmetry %s' % spacegroup_number)
        job.input('mosaic %f' % mosaic)

        if self._mosflm_postref_fix_mosaic:
          job.input('postref fix mosaic')

        job.input('refinement include partials')

        # note well that the beam centre is coming from indexing so
        # should be already properly handled - likewise the distance
        if self.get_wavelength_prov() == 'user':
          job.input('wavelength %f' % self.get_wavelength())

        # get all of the stored parameter values
        parameters = self.get_integrater_parameters('mosflm')
        for p in parameters.keys():
          job.input('%s %s' % (p, str(parameters[p])))

        # in here I need to get the GAIN parameter from the sweep
        # or from somewhere in memory....

        if self._mosflm_gain:
          job.input('gain %5.2f' % self._mosflm_gain)

        # check for resolution limits
        if self._intgr_reso_high > 0.0:
          if self._intgr_reso_low:
            job.input('resolution %f %f' % (self._intgr_reso_high,
                                             self._intgr_reso_low))
          else:
            job.input('resolution %f' % self._intgr_reso_high)

        if Flags.get_mask():
          mask = Flags.get_mask().calculate_mask_mosflm(
              self.get_header())
          record = 'limits quad'
          for m in mask:
            record += ' %.1f %.1f' % m
          job.input(record)

        # set up the integration
        job.input('postref fix all')
        # fudge this needs to be fixed. FIXME!
        job.input('postref maxresidual 5.0')

        # compute the detector limits to use for this...
        # these are w.r.t. the beam centre and are there to
        # ensure that spots are not predicted off the detector
        # (see bug # 2551)

        detector = self.get_detector()
        detector_width, detector_height = detector[0].get_image_size_mm()

        lim_x = 0.5 * detector_width
        lim_y = 0.5 * detector_height

        Debug.write('Scanner limits: %.1f %.1f' % (lim_x, lim_y))
        job.input('limits xscan %f yscan %f' % (lim_x, lim_y))

        # FIXME somewhere here need to include the pre-refinement
        # step... start with reprocessing first 4 images...

        a, b = chunks[j]

        if b - a > 3:
          b = a + 3

        job.input('postref multi segments 1')
        job.input('process %d %d' % (a, b))
        job.input('go')

        job.input('postref nosegment')

        if self._mosflm_postref_fix_mosaic:
          job.input('postref fix mosaic')

        job.input('separation close')

        ## XXX FIXME this is a horrible hack - I at least need to
        ## sand box this ...
        #if self.get_header_item('detector') == 'raxis':
          #job.input('adcoffset 0')

        genfile = os.path.join(os.environ['CCP4_SCR'],
                               '%d_%d_mosflm.gen' %
                               (self.get_xpid(), j))

        job.input('genfile %s' % genfile)

        job.input('process %d %d' % chunks[j])

        job.input('go')

        # these are now running so ...

        jobs.append(job)

        continue

      # ok, at this stage I need to ...
      #
      # (i) accumulate the statistics as a function of batch
      # (ii) mong them into a single block
      #
      # This is likely to be a pain in the arse!

      first_integrated_batch = 1.0e6
      last_integrated_batch = -1.0e6

      all_residuals = []
      all_spot_status = ''

      threads = []

      for j in range(parallel):
        job = jobs[j]

        # now wait for them to finish - first wait will really be the
        # first one, then all should be finished...

        thread = Background(job, 'close_wait')
        thread.start()
        threads.append(thread)

      mosaics = []

      for j in range(parallel):
        thread = threads[j]
        thread.stop()
        job = jobs[j]

        # get the log file
        output = job.get_all_output()

        # record a copy of it, perhaps - though not if parallel
        if self.get_integrater_sweep_name() and False:
          pname, xname, dname = self.get_integrater_project_info()
          FileHandler.record_log_file(
              '%s %s %s %s mosflm integrate' % \
              (self.get_integrater_sweep_name(),
               pname, xname, '%s_%d' % (dname, j)),
              job.get_log_file())

        # look for things that we want to know...
        # that is, the output reflection file name, the updated
        # value for the gain (if present,) any warnings, errors,
        # or just interesting facts.

        integrated_images_first = 1.0e6
        integrated_images_last = -1.0e6

        # look for major errors

        for i in range(len(output)):
          o = output[i]
          if 'LWBAT: error in ccp4_lwbat' in o:
            raise RuntimeError, 'serious error - inspect %s' % \
                  self.get_log_file()

        for i in range(len(output)):
          o = output[i]

          if 'Integrating Image' in o:
            batch = int(o.replace('Image', 'Image ').split()[2])
            if batch < integrated_images_first:
              integrated_images_first = batch
            if batch > integrated_images_last:
              integrated_images_last = batch
            if batch < first_integrated_batch:
              first_integrated_batch = batch
            if batch > last_integrated_batch:
              last_integrated_batch = batch

          if 'Smoothed value for refined mosaic' in o:
            mosaics.append(float(o.split()[-1]))

          if 'ERROR IN DETECTOR GAIN' in o:

            # ignore for photon counting detectors

            if 'pilatus' in self.get_header_item('detector_class'):
              continue

            # look for the correct gain
            for j in range(i, i + 10):
              if output[j].split()[:2] == ['set', 'to']:
                gain = float(output[j].split()[-1][:-1])

                # check that this is not the input
                # value... Bug # 3374

                if self._mosflm_gain:

                  if math.fabs(
                      gain - self._mosflm_gain) > 0.02:

                    self.set_integrater_parameter(
                        'mosflm', 'gain', gain)
                    self.set_integrater_export_parameter(
                        'mosflm', 'gain', gain)
                    Debug.write(
                        'GAIN updated to %f' % gain)

                    self._mosflm_gain = gain
                    self._mosflm_rerun_integration = True

                else:

                  self.set_integrater_parameter(
                      'mosflm', 'gain', gain)
                  self.set_integrater_export_parameter(
                      'mosflm', 'gain', gain)
                  Debug.write('GAIN found to be %f' % gain)

                  self._mosflm_gain = gain
                  self._mosflm_rerun_integration = True

          # FIXME if mosaic spread refines to a negative value
          # once the lattice has passed the triclinic postrefinement
          # test then fix this by setting "POSTREF FIX MOSAIC" and
          # restarting.

          if 'Smoothed value for refined mosaic spread' in o:
            mosaic = float(o.split()[-1])
            if mosaic < 0.0:
              raise IntegrationError, 'negative mosaic spread'

          if 'WRITTEN OUTPUT MTZ FILE' in o:
            hklout = os.path.join(
                job.get_working_directory(),
                output[i + 1].split()[-1])

            Debug.write('Integration output: %s' % hklout)
            hklouts.append(hklout)

          if 'Number of Reflections' in o:
            nref += int(o.split()[-1])

          if 'BGSIG too large' in o:
            Debug.write(
                'BGSIG error detected - try fixing profile...')
            self._mosflm_refine_profiles = False
            self.set_integrater_done(False)

            return

          if 'An unrecoverable error has occurred in GETPROF' in o:
            Debug.write(
                'GETPROF error detected - try fixing profile...')
            self._mosflm_refine_profiles = False
            self.set_integrater_done(False)

            return

          if 'MOSFLM HAS TERMINATED EARLY' in o:
            Chatter.write('Mosflm has failed in integration')
            message = 'The input was:\n\n'
            for input in self.get_all_input():
              message += '  %s' % input
            Chatter.write(message)
            raise RuntimeError, \
                  'integration failed: reason unknown (log %s)' % \
                  self.get_log_file()


        # here
        # write the report for each image as .*-#$ to Chatter -
        # detailed report will be written automagically to science...

        parsed_output = _parse_mosflm_integration_output(output)
        spot_status = _happy_integrate_lp(parsed_output)

        # inspect the output for e.g. very high weighted residuals

        images = parsed_output.keys()
        images.sort()

        max_weighted_residual = 0.0

        residuals = []
        for i in images:
          if parsed_output[i].has_key('weighted_residual'):
            residuals.append(parsed_output[i]['weighted_residual'])

        for r in residuals:
          all_residuals.append(r)

        for s in spot_status:
          all_spot_status += s

        # concatenate all of the output lines to our own output
        # channel (may be messy, but nothing better presents itself...
        # yuck, this involves delving in to the Driver interface...

        for record in output:
          self._standard_output_records.append(record)
          if not self._log_file is None:
            self._log_file.write(record)

      self._intgr_batches_out = (first_integrated_batch,
                                 last_integrated_batch)


      if mosaics and len(mosaics) > 0:
        self.set_integrater_mosaic_min_mean_max(
            min(mosaics), sum(mosaics) / len(mosaics), max(mosaics))
      else:
        m = indxr.get_indexer_mosaic()
        self.set_integrater_mosaic_min_mean_max(m, m, m)

      Chatter.write('Processed batches %d to %d' % \
                    self._intgr_batches_out)

      spot_status = all_spot_status

      if len(spot_status) > 60:
        Chatter.write('Integration status per image (60/record):')
      else:
        Chatter.write('Integration status per image:')

      for chunk in [spot_status[i:i + 60] \
                    for i in range(0, len(spot_status), 60)]:
        Chatter.write(chunk)

      Chatter.write(
          '"o" => good        "%" => ok        "!" => bad rmsd')
      Chatter.write(
          '"O" => overloaded  "#" => many bad  "." => weak')
      Chatter.write(
          '"@" => abandoned')

      Chatter.write('Mosaic spread: %.3f < %.3f < %.3f' % \
                    self.get_integrater_mosaic_min_mean_max())

      # gather the statistics from the postrefinement for all sweeps

      postref_result = { }

      for summary in summary_files:
        try:
          update = _parse_summary_file(summary)
        except AssertionError, e:
          update = { }
        postref_result.update(update)

      # now write this to a postrefinement log

      postref_log = os.path.join(self.get_working_directory(),
                                 'postrefinement.log')

      fout = open(postref_log, 'w')

      fout.write('$TABLE: Postrefinement for %s:\n' % \
                 self._intgr_sweep_name)
      fout.write('$GRAPHS: Missetting angles:A:1, 2, 3, 4: $$\n')
      fout.write('Batch PhiX PhiY PhiZ $$ Batch PhiX PhiY PhiZ $$\n')

      for image in sorted(postref_result):
        phix = postref_result[image].get('phix', 0.0)
        phiy = postref_result[image].get('phiy', 0.0)
        phiz = postref_result[image].get('phiz', 0.0)

        fout.write('%d %5.2f %5.2f %5.2f\n' % \
                   (image, phix, phiy, phiz))

      fout.write('$$\n')
      fout.close()

      if self.get_integrater_sweep_name():
        pname, xname, dname = self.get_integrater_project_info()
        FileHandler.record_log_file('%s %s %s %s postrefinement' % \
                                    (self.get_integrater_sweep_name(),
                                     pname, xname, dname),
                                    postref_log)

      hklouts.sort()

      hklout = os.path.join(self.get_working_directory(),
                            os.path.split(hklouts[0])[-1])

      Debug.write('Sorting data to %s' % hklout)
      for hklin in hklouts:
        Debug.write('<= %s' % hklin)

      sortmtz = Sortmtz()
      sortmtz.set_hklout(hklout)
      for hklin in hklouts:
        sortmtz.add_hklin(hklin)

      sortmtz.sort()

      self._mosflm_hklout = hklout

      return self._mosflm_hklout

    def _reorder_cell_refinement_images(self):
      if not self._mosflm_cell_ref_images:
        raise RuntimeError, 'no cell refinement images to reorder'

      hashmap = { }

      for m in self._mosflm_cell_ref_images:
        hashmap[m[0]] = m[1]

      keys = hashmap.keys()
      keys.sort()

      cell_ref_images = [(k, hashmap[k]) for k in keys]
      self._mosflm_cell_ref_images = cell_ref_images
      return

    def set_integrater_resolution(self, dmin, dmax, user = False):
      if user:
        Integrater.set_integrater_resolution(self, dmin, dmax, user)
      return

    def set_integrater_high_resolution(self, dmin, user = False):
      if user:
        Integrater.set_integrater_high_resolution(self, dmin, user)
      return

    def set_integrater_low_resolution(self, dmax, user = False):
      self._intgr_reso_low = dmax
      return

  return MosflmWrapper()


def _happy_integrate_lp(integrate_lp_stats):
  '''Return a string which explains how happy we are with the integration.'''

  images = integrate_lp_stats.keys()
  images.sort()

  results = ''

  max_weighted_residual = 0.0

  for i in images:
    data = integrate_lp_stats[i]

    # FIXME need to look for "blank" "many bad spots" "overloaded"

    if not data.has_key('weighted_residual'):
      pass
    elif data['weighted_residual'] < max_weighted_residual:
      max_weighted_residual = data['weighted_residual']

    # definitions...

    # rmsd pixel > 1.0 -> % (ok) > 2.5 -> ! (bad)
    # > 10% overloads -> O (overloads)

    if not data.has_key('rmsd_pixel'):
      status = '@'
    elif data.get('fraction_weak', 1.0) > 0.95:
      status = '.'
    elif data['rmsd_pixel'] > 2.5:
      status = '!'
    elif data['rmsd_pixel'] > 1.0:
      status = '%'
    elif data['overloads'] > 0.01 * data['strong']:
      status = 'O'
    else:
      status = 'o'

    # also - # bad O overloaded . blank ! problem ? other
    # @ ABANDONED PROCESSING

    results += status

  return results
