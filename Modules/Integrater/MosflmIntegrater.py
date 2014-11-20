#!/usr/bin/env python
# MosflmIntegrater.py
#   Copyright (C) 2006-2014 CCLRC, Graeme Winter & Richard Gildea
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

if not os.environ.has_key('XIA2CORE_ROOT'):
  raise RuntimeError, 'XIA2CORE_ROOT not defined'
if not os.environ.has_key('XIA2_ROOT'):
  raise RuntimeError, 'XIA2_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
  sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))
if not os.environ['XIA2_ROOT'] in sys.path:
  sys.path.append(os.environ['XIA2_ROOT'])

from Background.Background import Background

# interfaces that this will present
from Schema.Interfaces.FrameProcessor import FrameProcessor
from Schema.Interfaces.Integrater import Integrater

# output streams &c.
from Handlers.Streams import Chatter, Debug, Journal
from Handlers.Citations import Citations
from Handlers.Flags import Flags
from Handlers.Files import FileHandler

# helpers
from Wrappers.CCP4.MosflmHelpers import _happy_integrate_lp, \
     _parse_mosflm_integration_output, decide_integration_resolution_limit, \
     standard_mask, detector_class_to_mosflm, \
     _parse_summary_file
from Wrappers.Mosflm.MosflmRefineCell import MosflmRefineCell
from Wrappers.Mosflm.MosflmIntegrate import MosflmIntegrate

from Modules.GainEstimater import gain
from Handlers.Files import FileHandler

from lib.bits import auto_logfiler, mean_sd
from lib.SymmetryLib import lattice_to_spacegroup

from Experts.MatrixExpert import transmogrify_matrix

# exceptions
from Schema.Exceptions.BadLatticeError import BadLatticeError
from Schema.Exceptions.NegativeMosaicError import NegativeMosaicError
from Schema.Exceptions.IntegrationError import IntegrationError

# other classes which are necessary to implement the integrater
# interface (e.g. new version, with reindexing as the finish...)
from Wrappers.CCP4.Reindex import Reindex
from Wrappers.CCP4.Sortmtz import Sortmtz

class MosflmIntegrater(FrameProcessor, Integrater):
  '''A wrapper for Mosflm integration.'''

  def __init__(self):
    # generic things
    FrameProcessor.__init__(self)
    Integrater.__init__(self)

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

  def _mosflm_generate_raster(self, _images):
    from Wrappers.Mosflm.GenerateRaster import GenerateRaster
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
        rms_deviations_p1, br_p1 = self._mosflm_test_refine_cell(
            'aP')

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

      #self.reset()
      #auto_logfiler(self)

      if self.get_integrater_sweep_name():
        pname, xname, dname = self.get_integrater_project_info()
        #FileHandler.record_log_file(
            #'%s %s %s %s mosflm integrate' % \
            #(self.get_integrater_sweep_name(),
             #pname, xname, dname),
            #self.get_log_file())

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
    beam_centre = indxr.get_indexer_beam_centre()
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


    refiner = MosflmRefineCell()
    refiner.set_working_directory(self.get_working_directory())
    auto_logfiler(refiner)

    if self._mosflm_gain:
      refiner.set_gain(self._mosflm_gain)

    refiner.set_reverse_phi(self.get_reversephi())
    refiner.set_template(self.get_template())
    refiner.set_directory(self.get_directory())
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

    if self.get_wavelength_prov() == 'user':
      refiner.set_wavelength(self.get_wavelength())

    # belt + braces mode - only to be used when considering failover,
    # will run an additional step of autoindexing prior to cell
    # refinement, to be used only after proving that not going it
    # will result in cell refinement failure - will use the first
    # wedge... N.B. this is only useful if the indexer is Labelit
    # not Mosflm...

    refiner.set_add_autoindex(self._mosflm_cell_ref_add_autoindex)

    # get all of the stored parameter values
    parameters = self.get_integrater_parameters('mosflm')
    refiner.update_parameters(parameters)

    detector = self.get_detector()
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
      from Wrappers.Mosflm.AutoindexHelpers import set_mosflm_beam_centre
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

    refiner = MosflmRefineCell()
    refiner.set_working_directory(self.get_working_directory())
    auto_logfiler(refiner)

    if self._mosflm_gain:
      refiner.set_gain(self._mosflm_gain)

    refiner.set_reverse_phi(self.get_reversephi())
    refiner.set_template(self.get_template())
    refiner.set_directory(self.get_directory())
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

    if self.get_wavelength_prov() == 'user':
      refiner.set_wavelength(self.get_wavelength())

    # belt + braces mode - only to be used when considering failover,
    # will run an additional step of autoindexing prior to cell
    # refinement, to be used only after proving that not going it
    # will result in cell refinement failure - will use the first
    # wedge... N.B. this is only useful if the indexer is Labelit
    # not Mosflm...

    refiner.set_add_autoindex(self._mosflm_cell_ref_add_autoindex)

    # get all of the stored parameter values
    parameters = self.get_integrater_parameters('mosflm')
    refiner.update_parameters(parameters)

    detector = self.get_detector()
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
    self._intgr_cell = refiner.get_refined_unit_cell()
    distance = refiner.get_refined_distance2()
    experiment = self.get_integrater_indexer(
      ).get_indexer_experiment_list()[0]
    from Wrappers.Mosflm.AutoindexHelpers import set_distance
    set_distance(experiment.detector, distance)

    self.set_integrater_parameter('mosflm',
                                  'distortion yscale',
                                  refiner.get_refined_distortion_yscale())

    self.set_integrater_parameter('mosflm',
                                  'raster',
                                  refiner.get_raster())

    separation = refiner.get_separation()
    if separation is not None:
      self.set_integrater_parameter('mosflm',
                                    'separation',
                                    '%s %s' %refiner.get_separation())

    self.set_integrater_parameter('mosflm',
                                  'beam',
                                  '%s %s' %refiner.get_refined_beam_centre())
    self.set_integrater_parameter('mosflm',
                                  'distance',
                                  refiner.get_refined_distance())
    self.set_integrater_parameter('mosflm',
                                  'distortion tilt',
                                  refiner.get_refined_distortion_tilt())
    self.set_integrater_parameter('mosflm',
                                  'distortion twist',
                                  refiner.get_refined_distortion_twist())

    indxr._indxr_mosaic = refiner.get_refined_mosaic()

    indxr.set_indexer_payload('mosflm_orientation_matrix', open(
        os.path.join(self.get_working_directory(),
                     'xiarefine.mat'), 'r').readlines())

    from Wrappers.Mosflm.AutoindexHelpers import crystal_model_from_mosflm_mat
    # make a dxtbx crystal_model object from the mosflm matrix
    experiment = self.get_integrater_indexer(
      ).get_indexer_experiment_list()[0]
    crystal_model = crystal_model_from_mosflm_mat(
      indxr._indxr_payload['mosflm_orientation_matrix'],
      unit_cell=refiner.get_refined_unit_cell(),
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
    integrater = MosflmIntegrate()
    integrater.set_working_directory(self.get_working_directory())
    auto_logfiler(integrater)

    integrater.set_refine_profiles(self._mosflm_refine_profiles)

    pname, xname, dname = self.get_integrater_project_info()

    if pname != None and xname != None and dname != None:
      Debug.write('Harvesting: %s/%s/%s' % (pname, xname, dname))

      harvest_dir = os.path.join(os.environ['HARVESTHOME'],
                                 'DepositFiles', pname)

      if not os.path.exists(harvest_dir):
        Debug.write('Creating harvest directory...')
        os.makedirs(harvest_dir)

      # harvest file name will be %s.mosflm_run_start_end % dname
      temp_dname = '%s_%s' % \
                   (dname, self.get_integrater_sweep_name())
      integrater.set_pname_xname_dname(pname, xname, temp_dname)

    integrater.set_reverse_phi(self.get_reversephi())

    integrater.set_template(self.get_template())
    integrater.set_directory(self.get_directory())

    # check for ice - and if so, exclude (ranges taken from
    # XDS documentation)
    if self.get_integrater_ice() != 0:
      Debug.write('Excluding ice rings')
      integrater.set_exclude_ice(True)

    # exclude specified resolution ranges
    if len(self.get_integrater_excluded_regions()) != 0:
      regions = self.get_integrater_excluded_regions()
      Debug.write('Excluding regions: %s' % `regions`)
      integrater.set_exclude_regions(regions)

    mask = standard_mask(self.get_detector())
    for m in mask:
      integrater.add_instruction(m)

    integrater.set_input_mat_file('xiaintegrate.mat')

    integrater.set_beam_centre(beam)
    integrater.set_distance(distance)
    integrater.set_space_group_number(spacegroup_number)
    integrater.set_mosaic(mosaic)

    if self.get_wavelength_prov() == 'user':
      integrater.set_wavelength(self.get_wavelength())

    parameters = self.get_integrater_parameters('mosflm')
    integrater.update_parameters(parameters)

    if self._mosflm_gain:
      integrater.set_gain(self._mosflm_gain)

    # check for resolution limits
    if self._intgr_reso_high > 0.0:
      integrater.set_d_min(self._intgr_reso_high)
    if self._intgr_reso_low:
      integrater.set_d_max(self._intgr_reso_low)

    if Flags.get_mask():
      mask = Flags.get_mask().calculate_mask_mosflm(
          self.get_header())
      integrater.set_mask(mask)

    detector = self.get_detector()
    detector_width, detector_height = detector[0].get_image_size_mm()

    lim_x = 0.5 * detector_width
    lim_y = 0.5 * detector_height

    Debug.write('Scanner limits: %.1f %.1f' % (lim_x, lim_y))
    integrater.set_limits(lim_x, lim_y)

    integrater.set_fix_mosaic(self._mosflm_postref_fix_mosaic)

    ## XXX FIXME this is a horrible hack - I at least need to
    ## sand box this ...
    #if self.get_header_item('detector') == 'raxis':
      #self.input('adcoffset 0')

    offset = self.get_frame_offset()

    integrater.set_image_range(
      (self._intgr_wedge[0] - offset, self._intgr_wedge[1] - offset))

    try:
      integrater.run()
    except RuntimeError, e:
      if 'integration failed: reason unknown' in str(e):
        Chatter.write('Mosflm has failed in integration')
        message = 'The input was:\n\n'
        for input in integrater.get_all_input():
          message += '  %s' % input
        Chatter.write(message)
      raise

    FileHandler.record_log_file(
        '%s %s %s %s mosflm integrate' % \
        (self.get_integrater_sweep_name(),
         pname, xname, dname),
        integrater.get_log_file())

    self._mosflm_hklout = integrater.get_hklout()
    Debug.write('Integration output: %s' %self._mosflm_hklout)

    self._intgr_n_ref = integrater.get_nref()

    # if a BGSIG error happened try not refining the
    # profile and running again...

    if integrater.get_bgsig_too_large():
      if not self._mosflm_refine_profiles:
        raise RuntimeError, 'BGSIG error with profiles fixed'

      Debug.write(
          'BGSIG error detected - try fixing profile...')

      self._mosflm_refine_profiles = False
      self.set_integrater_done(False)

      return

    if integrater.get_getprof_error():
      Debug.write(
          'GETPROF error detected - try fixing profile...')
      self._mosflm_refine_profiles = False
      self.set_integrater_done(False)

      return

    if (integrater.get_detector_gain_error() and not
        (self.get_imageset().get_detector()[0].get_type() == 'SENSOR_PAD')):
      gain = integrater.get_suggested_gain()
      if gain is not None:
        self.set_integrater_parameter('mosflm', 'gain', gain)
        self.set_integrater_export_parameter('mosflm', 'gain', gain)
        if self._mosflm_gain:
          Debug.write('GAIN updated to %f' % gain)
        else:
          Debug.write('GAIN found to be %f' % gain)

        self._mosflm_gain = gain
        self._mosflm_rerun_integration = True

    if not self._mosflm_hklout:
      raise RuntimeError, 'processing abandoned'

    self._intgr_batches_out = integrater.get_batches_out()

    mosaics = integrater.get_mosaic_spreads()
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

    residuals = integrater.get_residuals()
    mean, sd = mean_sd(residuals)
    Chatter.write('Weighted RMSD: %.2f (%.2f)' % \
                  (mean, sd))

    #for i in images:
      #data = parsed_output[i]

      #if data.has_key('weighted_residual'):

        #if data['weighted_residual'] > max_weighted_residual:
          #max_weighted_residual = data['weighted_residual']

    spot_status = integrater.get_spot_status()
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
    postref_result = integrater.get_postref_result()

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

      job = MosflmIntegrate()
      job.set_working_directory(wd)

      auto_logfiler(job)

      l = indxr.get_indexer_lattice()

      # create the starting point
      f = open(os.path.join(wd, 'xiaintegrate-%s.mat' % l), 'w')
      for m in matrix:
        f.write(m)
      f.close()

      spacegroup_number = lattice_to_spacegroup(lattice)

      job.set_refine_profiles(self._mosflm_refine_profiles)

      # N.B. for harvesting need to append N to dname.

      if pname != None and xname != None and dname != None:
        Debug.write('Harvesting: %s/%s/%s' %
                    (pname, xname, dname))

        harvest_dir = os.path.join(os.environ['HARVESTHOME'],
                                   'DepositFiles', pname)

        if not os.path.exists(harvest_dir):
          Debug.write('Creating harvest directory...')
          os.makedirs(harvest_dir)

        temp_dname = '%s_%s' % \
                     (dname, self.get_integrater_sweep_name())
        job.set_pname_xname_dname(pname, xname, temp_dname)

      job.set_reverse_phi(self.get_reversephi())

      job.set_template(self.get_template())
      job.set_directory(self.get_directory())

      # check for ice - and if so, exclude (ranges taken from
      # XDS documentation)
      if self.get_integrater_ice() != 0:
        Debug.write('Excluding ice rings')
        job.set_exclude_ice(True)

      # exclude specified resolution ranges
      if len(self.get_integrater_excluded_regions()) != 0:
        regions = self.get_integrater_excluded_regions()
        Debug.write('Excluding regions: %s' % `regions`)
        job.set_exclude_regions(regions)

      mask = standard_mask(self.get_detector())
      for m in mask:
        job.add_instruction(m)

      job.set_input_mat_file('xiaintegrate-%s.mat' % l)

      job.set_beam_centre(beam)
      job.set_distance(distance)
      job.set_space_group_number(spacegroup_number)
      job.set_mosaic(mosaic)

      if self.get_wavelength_prov() == 'user':
        job.set_wavelength(self.get_wavelength())

      parameters = self.get_integrater_parameters('mosflm')
      job.update_parameters(parameters)

      if self._mosflm_gain:
        job.set_gain(self._mosflm_gain)

      # check for resolution limits
      if self._intgr_reso_high > 0.0:
        job.set_d_min(self._intgr_reso_high)
      if self._intgr_reso_low:
        job.set_d_max(self._intgr_reso_low)

      if Flags.get_mask():
        mask = Flags.get_mask().calculate_mask_mosflm(
            self.get_header())
        job.set_mask(mask)

      detector = self.get_detector()
      detector_width, detector_height = detector[0].get_image_size_mm()

      lim_x = 0.5 * detector_width
      lim_y = 0.5 * detector_height

      Debug.write('Scanner limits: %.1f %.1f' % (lim_x, lim_y))
      job.set_limits(lim_x, lim_y)

      job.set_fix_mosaic(self._mosflm_postref_fix_mosaic)

      ## XXX FIXME this is a horrible hack - I at least need to
      ## sand box this ...
      #if self.get_header_item('detector') == 'raxis':
        #self.input('adcoffset 0')

      job.set_pre_refinement(True)
      job.set_image_range(chunks[j])


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

      thread = Background(job, 'run')
      thread.start()
      threads.append(thread)

    mosaics = []
    postref_result = { }

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

      batches = job.get_batches_out()
      integrated_images_first = min(batches[0], integrated_images_first)
      integrated_images_last = max(batches[1], integrated_images_last)

      mosaics.extend(job.get_mosaic_spreads())
      if min(mosaics) < 0:
        raise IntegrationError, 'negative mosaic spread: %s' %min(mosaic)

      if (job.get_detector_gain_error() and not
          (self.get_imageset().get_detector()[0].get_type() == 'SENSOR_PAD')):
        gain = job.get_suggested_gain()
        if gain is not None:
          self.set_integrater_parameter('mosflm', 'gain', gain)
          self.set_integrater_export_parameter('mosflm', 'gain', gain)
          if self._mosflm_gain:
            Debug.write('GAIN updated to %f' % gain)
          else:
            Debug.write('GAIN found to be %f' % gain)

          self._mosflm_gain = gain
          self._mosflm_rerun_integration = True

      hklout = job.get_hklout()
      Debug.write('Integration output: %s' % hklout)
      hklouts.append(hklout)

      nref += job.get_nref()

      # if a BGSIG error happened try not refining the
      # profile and running again...

      if job.get_bgsig_too_large():
        if not self._mosflm_refine_profiles:
          raise RuntimeError, 'BGSIG error with profiles fixed'

        Debug.write(
            'BGSIG error detected - try fixing profile...')

        self._mosflm_refine_profiles = False
        self.set_integrater_done(False)

        return

      if job.get_getprof_error():
        Debug.write(
            'GETPROF error detected - try fixing profile...')
        self._mosflm_refine_profiles = False
        self.set_integrater_done(False)

        return

      # here
      # write the report for each image as .*-#$ to Chatter -
      # detailed report will be written automagically to science...

      spot_status = job.get_spot_status()
      postref_result.update(job.get_postref_result())

      # inspect the output for e.g. very high weighted residuals

      all_residuals.extend(job.get_residuals())

      for s in spot_status:
        all_spot_status += s

      ## concatenate all of the output lines to our own output
      ## channel (may be messy, but nothing better presents itself...
      ## yuck, this involves delving in to the Driver interface...

      #output = job.get_all_output()
      #for record in output:
        #self._standard_output_records.append(record)
        #if not self._log_file is None:
          #self._log_file.write(record)

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
