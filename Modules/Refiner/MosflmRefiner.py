#!/usr/bin/env python
# MosflmRefiner.py
#   Copyright (C) 2015 Diamond Light Source, Richard Gildea
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#

from Schema.Interfaces.Refiner import Refiner
from Handlers.Streams import Debug, Chatter, Journal
from Handlers.Flags import Flags

import os
import math

from lib.bits import auto_logfiler
from Handlers.Files import FileHandler

from Wrappers.Mosflm.MosflmRefineCell import MosflmRefineCell
from lib.SymmetryLib import lattice_to_spacegroup

from Experts.MatrixExpert import transmogrify_matrix

from Schema.Exceptions.NegativeMosaicError import NegativeMosaicError

from dxtbx.model.experiment.experiment_list import ExperimentList

class MosflmRefiner(Refiner):

  def __init__(self):
    super(MosflmRefiner, self).__init__()

    # local parameters used in cell refinement
    self._mosflm_gain = None
    self._mosflm_cell_ref_images = None
    self._mosflm_cell_ref_double_mosaic = False
    self._mosflm_postref_fix_mosaic = False

    # belt + braces for very troublesome cases - this will only
    # be used in failover / microcrystal mode
    self._mosflm_cell_ref_add_autoindex = False

  # factory functions

  def _refine_prepare(self):
    pass

  def _refine(self):

    for epoch, idxr in self._refinr_indexers.iteritems():
      #self.digest_template()

      if not self._mosflm_gain and idxr.get_gain():
        self._mosflm_gain = idxr.get_gain()

      # if pilatus override GAIN to 1.0

      if idxr.get_imageset().get_detector()[0].get_type() == 'SENSOR_PAD':
        self._mosflm_gain = 1.0

      #indxr = self.get_refiner_indexer()
      indxr = idxr

      if not self._mosflm_cell_ref_images:
        mosaic = indxr.get_indexer_mosaic()

        if Flags.get_microcrystal():
          self._mosflm_cell_ref_images = self._refine_select_twenty(
            idxr, mosaic)
        else:
          self._mosflm_cell_ref_images = self._refine_select_images(
            idxr, mosaic)

      # generate human readable output

      images_str = '%d to %d' % tuple(self._mosflm_cell_ref_images[0])
      for i in self._mosflm_cell_ref_images[1:]:
        images_str += ', %d to %d' % tuple(i)

      cell_str = '%.2f %.2f %.2f %.2f %.2f %.2f' % \
        indxr.get_indexer_cell()

      if len(idxr._fp_directory) <= 50:
        dirname = idxr._fp_directory
      else:
        dirname = '...%s' % idxr._fp_directory[-46:]

      Journal.block('cell refining', idxr._indxr_sweep_name, 'mosflm',
                    {'images':images_str,
                     'start cell':cell_str,
                     'target lattice':indxr.get_indexer_lattice(),
                     'template':idxr._fp_template,
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

        integration_params = self._mosflm_generate_raster(images, indxr)
        indxr.set_indexer_payload('mosflm_integration_params', integration_params)

        # copy them over to where they are needed

        if integration_params.has_key('separation'):
          self.set_refiner_parameter(
            'mosflm', 'separation',
            '%f %f' % tuple(integration_params['separation']))
        if integration_params.has_key('raster'):
          self.set_refiner_parameter(
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
           idxr.get_indexer_sweep().get_user_lattice():
          rms_deviations_p1 = []
          br_p1 = []
        else:
          rms_deviations_p1, br_p1 = self._mosflm_test_refine_cell(
            idxr, 'aP')

        rms_deviations, br = self._mosflm_refine_cell(idxr)

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

      if not self.get_refiner_done():
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
        self._refinr_cell

      Journal.entry({'refined cell':cell_str})

  def _refine_finish(self):
    pass

  def _refine_select_twenty(self, idxr, mosaic):
    '''Select images for cell refinement - first 20 in the sweep.'''

    cell_ref_images = []

    images = idxr.get_matching_images()

    cell_ref_images = []

    if len(images) > 20:
      cell_ref_images.append((images[0], images[19]))
    else:
      cell_ref_images.append((images[0], images[-1]))

    return cell_ref_images

  def _refine_select_images(self, idxr, mosaic):
    '''Select images for cell refinement based on image headers.'''

    cell_ref_images = []

    phi_width = idxr.get_phi_width()
    min_images = max(3, int(2 * mosaic / phi_width))

    if min_images > 9:
      min_images = 9

    images = idxr.get_matching_images()

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

  def _mosflm_test_refine_cell(self, idxr, test_lattice):
    '''Test performing cell refinement in with a different
    lattice to the one which was selected by the autoindex
    procedure. This should not change anything in the class.'''

    #idxr = self.get_integrater_indexer()

    lattice = idxr.get_indexer_lattice()
    mosaic = idxr.get_indexer_mosaic()
    beam_centre = idxr.get_indexer_beam_centre()
    distance = idxr.get_indexer_distance()
    matrix = idxr.get_indexer_payload('mosflm_orientation_matrix')

    phi_width = idxr.get_phi_width()
    if mosaic < 0.25 * phi_width:
      mosaic = 0.25 * phi_width

    input_matrix = ''
    for m in matrix:
      input_matrix += '%s\n' % m

    new_matrix = transmogrify_matrix(lattice, input_matrix,
                                     test_lattice,
                                     idxr.get_wavelength(),
                                     self.get_working_directory())

    spacegroup_number = lattice_to_spacegroup(test_lattice)

    if not self._mosflm_cell_ref_images:
      raise RuntimeError, 'wedges must be assigned already'

    open(os.path.join(self.get_working_directory(),
                      'test-xiaindex-%s.mat' % lattice),
         'w').write(new_matrix)


    refiner = MosflmRefineCell()
    refiner.set_working_directory(self.get_working_directory())
    auto_logfiler(refiner)

    if self._mosflm_gain:
      refiner.set_gain(self._mosflm_gain)

    refiner.set_template(idxr.get_template())
    refiner.set_directory(idxr.get_directory())
    refiner.set_input_mat_file('test-xiaindex-%s.mat' % lattice)
    refiner.set_output_mat_file('test-xiarefine.mat')
    refiner.set_beam_centre(beam_centre)
    refiner.set_distance(distance)
    refiner.set_space_group_number(spacegroup_number)

    # FIXME 18/JUN/08 - it may help to have an overestimate
    # of the mosaic spread in here as it *may* refine down
    # better than up... - this is not a good idea as it may
    # also not refine at all! - 12972 # integration failed

    # Bug # 3103
    if self._mosflm_cell_ref_double_mosaic:
      mosaic *= 2.0
    refiner.set_mosaic(mosaic)

    # if set, use the resolution for cell refinement - see
    # bug # 2078...

    if self._mosflm_cell_ref_resolution and not \
       Flags.get_microcrystal():
      refiner.set_resolution(self._mosflm_cell_ref_resolution)

    refiner.set_fix_mosaic(self._mosflm_postref_fix_mosaic)

    if Flags.get_microcrystal():
      refiner.set_sdfac(2.0)

    # note well that the beam centre is coming from indexing so
    # should be already properly handled

    if idxr.get_wavelength_prov() == 'user':
      refiner.set_wavelength(idxr.get_wavelength())

    # belt + braces mode - only to be used when considering failover,
    # will run an additional step of autoindexing prior to cell
    # refinement, to be used only after proving that not going it
    # will result in cell refinement failure - will use the first
    # wedge... N.B. this is only useful if the indexer is Labelit
    # not Mosflm...

    refiner.set_add_autoindex(self._mosflm_cell_ref_add_autoindex)

    # XXX
    # get all of the stored parameter values
    parameters = self.get_refiner_parameters('mosflm')
    refiner.update_parameters(parameters)

    detector = idxr.get_detector()
    detector_width, detector_height = detector[0].get_image_size_mm()

    lim_x = 0.5 * detector_width
    lim_y = 0.5 * detector_height

    Debug.write('Scanner limits: %.1f %.1f' % (lim_x, lim_y))
    refiner.set_limits(lim_x, lim_y)
    refiner.set_images(self._mosflm_cell_ref_images)

    refiner.run()

    rms_values = refiner.get_rms_values()
    background_residual = refiner.get_background_residual()

    return rms_values, background_residual

  def _mosflm_refine_cell(self, idxr, set_spacegroup = None):
    '''Perform the refinement of the unit cell. This will populate
    all of the information needed to perform the integration.'''

    # FIXME this will die after #1285

    #if not self.get_integrater_indexer():
      #Debug.write('Replacing indexer of %s with self at %d' % \
                  #(str(self.get_integrater_indexer()), __line__))
      #self.set_integrater_indexer(self)

    #idxr = self.get_integrater_indexer()

    if not idxr.get_indexer_payload('mosflm_orientation_matrix'):
      raise RuntimeError, 'unexpected situation in indexing'

    lattice = idxr.get_indexer_lattice()
    mosaic = idxr.get_indexer_mosaic()
    cell = idxr.get_indexer_cell()
    beam_centre = idxr.get_indexer_beam_centre()

    # bug # 3174 - if mosaic is very small (here defined to be
    # 0.25 x osc_width) then set to this minimum value.

    phi_width = idxr.get_phi_width()
    if mosaic < 0.25 * phi_width:
      mosaic = 0.25 * phi_width

    if idxr.get_indexer_payload('mosflm_beam_centre'):
      beam_centre = idxr.get_indexer_payload('mosflm_beam_centre')

    distance = idxr.get_indexer_distance()
    matrix = idxr.get_indexer_payload('mosflm_orientation_matrix')

    integration_params = idxr.get_indexer_payload(
      'mosflm_integration_parameters')

    if integration_params is None:
      integration_params = {}

    if integration_params:
      if integration_params.has_key('separation'):
        self.set_refiner_parameter(
          'mosflm', 'separation',
          '%f %f' % tuple(integration_params['separation']))
      if integration_params.has_key('raster'):
        self.set_refiner_parameter(
          'mosflm', 'raster',
          '%d %d %d %d %d' % tuple(integration_params['raster']))

    idxr.set_indexer_payload('mosflm_integration_parameters', None)

    spacegroup_number = lattice_to_spacegroup(lattice)

    # copy these into myself for later reference, if indexer
    # is not myself - everything else is copied via the
    # cell refinement process...

    from cctbx import sgtbx
    from dxtbx.model import crystal
    from dxtbx.model.detector_helpers import set_mosflm_beam_centre
    experiment = idxr.get_indexer_experiment_list()[0]
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

    refiner = MosflmRefineCell()
    refiner.set_working_directory(self.get_working_directory())
    auto_logfiler(refiner)

    if self._mosflm_gain:
      refiner.set_gain(self._mosflm_gain)

    refiner.set_template(idxr.get_template())
    refiner.set_directory(idxr.get_directory())
    refiner.set_input_mat_file('xiaindex-%s.mat' % lattice)
    refiner.set_output_mat_file('xiarefine.mat')
    refiner.set_beam_centre(beam_centre)
    refiner.set_unit_cell(cell)
    refiner.set_distance(distance)
    if set_spacegroup:
      refiner.set_space_group_number(set_spacegroup)
    else:
      refiner.set_space_group_number(spacegroup_number)

    # FIXME 18/JUN/08 - it may help to have an overestimate
    # of the mosaic spread in here as it *may* refine down
    # better than up... - this is not a good idea as it may
    # also not refine at all! - 12972 # integration failed

    # Bug # 3103
    if self._mosflm_cell_ref_double_mosaic:
      mosaic *= 2.0
    refiner.set_mosaic(mosaic)

    # if set, use the resolution for cell refinement - see
    # bug # 2078...

    if self._mosflm_cell_ref_resolution and not \
       Flags.get_microcrystal():
      refiner.set_resolution(self._mosflm_cell_ref_resolution)

    refiner.set_fix_mosaic(self._mosflm_postref_fix_mosaic)

    if Flags.get_microcrystal():
      refiner.set_sdfac(2.0)

    # note well that the beam centre is coming from indexing so
    # should be already properly handled

    if idxr.get_wavelength_prov() == 'user':
      refiner.set_wavelength(idxr.get_wavelength())

    # belt + braces mode - only to be used when considering failover,
    # will run an additional step of autoindexing prior to cell
    # refinement, to be used only after proving that not going it
    # will result in cell refinement failure - will use the first
    # wedge... N.B. this is only useful if the indexer is Labelit
    # not Mosflm...

    refiner.set_add_autoindex(self._mosflm_cell_ref_add_autoindex)

    # get all of the stored parameter values
    parameters = self.get_refiner_parameters('mosflm')
    refiner.update_parameters(parameters)

    detector = idxr.get_detector()
    detector_width, detector_height = detector[0].get_image_size_mm()

    lim_x = 0.5 * detector_width
    lim_y = 0.5 * detector_height

    Debug.write('Scanner limits: %.1f %.1f' % (lim_x, lim_y))
    refiner.set_limits(lim_x, lim_y)
    refiner.set_images(self._mosflm_cell_ref_images)

    if Flags.get_failover() and not \
       self._mosflm_cell_ref_add_autoindex:
      refiner.set_ignore_cell_refinement_failure(True)

    refiner.run()

    # then look to see if the cell refinement worked ok - if it
    # didn't then this may indicate that the lattice was wrongly
    # selected.

    cell_refinement_ok = refiner.cell_refinement_ok()

    if not cell_refinement_ok:
      Debug.write('Repeating cell refinement...')
      self.set_integrater_prepare_done(False)
      self._mosflm_cell_ref_add_autoindex = True
      return [0.0], [0.0]

    rms_values = refiner.get_rms_values()
    background_residual = refiner.get_background_residual()
    self._refinr_cell = refiner.get_refined_unit_cell()
    distance = refiner.get_refined_distance2()
    experiment = idxr.get_indexer_experiment_list()[0]
    from Wrappers.Mosflm.AutoindexHelpers import set_distance
    set_distance(experiment.detector, distance)

    self.set_refiner_parameter('mosflm',
                                  'distortion yscale',
                                  refiner.get_refined_distortion_yscale())

    self.set_refiner_parameter('mosflm',
                               'raster',
                               refiner.get_raster())

    #integration_params['distortion yscale'] \
      #= refiner.get_refined_distortion_yscale()
    #integration_params['raster'] = refiner.get_raster()

    separation = refiner.get_separation()
    if separation is not None:
      self.set_refiner_parameter('mosflm',
                                 'separation',
                                 '%s %s' %refiner.get_separation())
      #integration_params['separation'] = refiner.get_separation()

    self.set_refiner_parameter('mosflm',
                                  'beam',
                                  '%s %s' %refiner.get_refined_beam_centre())
    self.set_refiner_parameter('mosflm',
                                  'distance',
                                  refiner.get_refined_distance())
    self.set_refiner_parameter('mosflm',
                                  'distortion tilt',
                                  refiner.get_refined_distortion_tilt())
    self.set_refiner_parameter('mosflm',
                                  'distortion twist',
                                  refiner.get_refined_distortion_twist())

    integration_params['beam'] = tuple(
      float(b) for b in refiner.get_refined_beam_centre())
    integration_params['distance'] = refiner.get_refined_distance()
    integration_params['distortion tilt'] = refiner.get_refined_distortion_tilt()
    integration_params['distortion twist'] = refiner.get_refined_distortion_twist()

    idxr._indxr_mosaic = refiner.get_refined_mosaic()

    idxr.set_indexer_payload('mosflm_orientation_matrix', open(
      os.path.join(self.get_working_directory(),
                   'xiarefine.mat'), 'r').readlines())
    self.set_refiner_payload('mosflm_orientation_matrix', idxr.get_indexer_payload(
      'mosflm_orientation_matrix'))
    self.set_refiner_payload('mosaic', refiner.get_refined_mosaic())
    self.set_refiner_payload('beam', integration_params['beam'])
    self.set_refiner_payload('distance', integration_params['distance'])

    from Wrappers.Mosflm.AutoindexHelpers import crystal_model_from_mosflm_mat
    # make a dxtbx crystal_model object from the mosflm matrix
    experiment = idxr.get_indexer_experiment_list()[0]
    crystal_model = crystal_model_from_mosflm_mat(
      idxr._indxr_payload['mosflm_orientation_matrix'],
      unit_cell=refiner.get_refined_unit_cell(),
      space_group=experiment.crystal.get_space_group())
    experiment.crystal = crystal_model

    #self.set_refiner_payload(
      #'mosflm_integration_parameters', integration_params)

    self._refinr_refined_experiment_list = ExperimentList([experiment])

    return rms_values, background_residual

  def _mosflm_generate_raster(self, _images, indexer):
    from Wrappers.Mosflm.GenerateRaster import GenerateRaster
    gr = GenerateRaster()
    gr.set_working_directory(self.get_working_directory())
    return gr(indexer, _images)
