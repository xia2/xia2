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

if not os.environ.has_key('XIA2_ROOT'):
  raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
  sys.path.append(os.environ['XIA2_ROOT'])

from Background.Background import Background

# interfaces that this will present
from Schema.Interfaces.Integrater import Integrater

# output streams &c.
from Handlers.Streams import Chatter, Debug, Journal
from Handlers.Citations import Citations
from Handlers.Flags import Flags
from Handlers.Files import FileHandler

# helpers
from Wrappers.CCP4.MosflmHelpers import \
     _parse_mosflm_integration_output, decide_integration_resolution_limit, \
     standard_mask, detector_class_to_mosflm, \
     _parse_summary_file
from Wrappers.Mosflm.MosflmIntegrate import MosflmIntegrate

from Modules.GainEstimater import gain

from lib.bits import auto_logfiler, mean_sd
from lib.SymmetryLib import lattice_to_spacegroup

# exceptions
from Schema.Exceptions.BadLatticeError import BadLatticeError
from Schema.Exceptions.IntegrationError import IntegrationError

# other classes which are necessary to implement the integrater
# interface (e.g. new version, with reindexing as the finish...)
from Wrappers.CCP4.Reindex import Reindex
from Wrappers.CCP4.Sortmtz import Sortmtz

class MosflmIntegrater(Integrater):
  '''A wrapper for Mosflm integration.'''

  def __init__(self):
    super(MosflmIntegrater, self).__init__()

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

  def to_dict(self):
    obj = super(MosflmIntegrater, self).to_dict()
    import inspect
    attributes = inspect.getmembers(self, lambda m:not(inspect.isroutine(m)))
    for a in attributes:
      if a[0].startswith('_mosflm_'):
        obj[a[0]] = a[1]
    return obj

  def _integrate_prepare(self):
    '''Prepare for integration - note that if there is a reason
    why this is needed to be run again, set self._intgr_prepare_done
    as False.'''

    if not self._mosflm_gain and self.get_gain():
      self._mosflm_gain = self.get_gain()

    # if pilatus override GAIN to 1.0

    if self.get_imageset().get_detector()[0].get_type() == 'SENSOR_PAD':
      self._mosflm_gain = 1.0

    #self._intgr_refiner.set_prepare_done(False)

    self.digest_template()

    experiment = self._intgr_refiner.get_refined_experiment_list(
      self.get_integrater_epoch())[0]
    crystal_model = experiment.crystal
    self._intgr_cell = crystal_model.get_unit_cell().parameters()

    if not self._intgr_wedge:
      images = self.get_matching_images()
      self.set_integrater_wedge(min(images),
      max(images))

    self.set_integrater_parameters(
      {'mosflm': self._intgr_refiner.get_refiner_parameters('mosflm')})

    return

  def _integrate(self):
    '''Implement the integrater interface.'''

    # cite the program
    Citations.cite('mosflm')

    images_str = '%d to %d' % tuple(self._intgr_wedge)
    cell_str = '%.2f %.2f %.2f %.2f %.2f %.2f' % tuple(self._intgr_cell)

    if len(self._fp_directory) <= 50:
      dirname = self._fp_directory
    else:
      dirname = '...%s' % self._fp_directory[-46:]

    Journal.block(
        'integrating', self._intgr_sweep_name, 'mosflm',
        {'images':images_str,
         'cell':cell_str,
         'lattice':self.get_integrater_refiner().get_refiner_lattice(),
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
        self.get_integrater_refiner().get_refiner_lattice()):
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

  def _mosflm_integrate(self):
    '''Perform the actual integration, based on the results of the
    cell refinement or indexing (they have the equivalent form.)'''

    #if not self.get_integrater_indexer():
      #Debug.write('Replacing indexer of %s with self at %d' % \
                  #(str(self.get_integrater_indexer()), __line__))
      #self.set_integrater_indexer(self)

    #indxr = self.get_integrater_indexer()
    refinr = self.get_integrater_refiner()

    if not refinr.get_refiner_payload('mosflm_orientation_matrix'):
      raise RuntimeError, 'unexpected situation in indexing'

    lattice = refinr.get_refiner_lattice()
    spacegroup_number = lattice_to_spacegroup(lattice)
    #mosaic = indxr.get_indexer_mosaic()
    mosaic = refinr.get_refiner_payload('mosaic')
    #cell = self._intgr_cell
    beam = refinr.get_refiner_payload('beam')
    distance = refinr.get_refiner_payload('distance')
    matrix = refinr.get_refiner_payload('mosflm_orientation_matrix')

    integration_params = refinr.get_refiner_payload(
      'mosflm_integration_parameters')

    #beam = integration_params['beam']
    #distance = integration_params['distance']

    if integration_params:
      if integration_params.has_key('separation'):
        self.set_integrater_parameter(
          'mosflm', 'separation',
          '%s %s' % tuple(integration_params['separation']))
      if integration_params.has_key('raster'):
        self.set_integrater_parameter(
          'mosflm', 'raster',
          '%d %d %d %d %d' % tuple(integration_params['raster']))

    refinr.set_refiner_payload('mosflm_integration_parameters', None)

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

    integrater.set_template(os.path.basename(self.get_template()))
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

    self._intgr_per_image_statistics = integrater.get_per_image_statistics()

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

    Chatter.write(self.show_per_image_statistics())

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

    #if not self.get_integrater_indexer():
      ## should I raise a RuntimeError here?!
      #Debug.write('Replacing indexer of %s with self at %d' % \
                  #(str(self.get_integrater_indexer()), __line__))
      #self.set_integrater_indexer(self)

    #indxr = self.get_integrater_indexer()
    refinr = self.get_integrater_refiner()

    lattice = refinr.get_refiner_lattice()
    spacegroup_number = lattice_to_spacegroup(lattice)
    #mosaic = indxr.get_indexer_mosaic()
    mosaic = refinr.get_refiner_payload('mosaic')
    #cell = self._intgr_cell
    beam = refinr.get_refiner_payload('beam')
    distance = refinr.get_refiner_payload('distance')
    matrix = refinr.get_refiner_payload('mosflm_orientation_matrix')

    integration_params = refinr.get_refiner_payload(
      'mosflm_integration_parameters')

    #beam = integration_params['beam']
    #distance = integration_params['distance']

    if integration_params:
      if integration_params.has_key('separation'):
        self.set_integrater_parameter(
            'mosflm', 'separation',
            '%s %s' % tuple(integration_params['separation']))
      if integration_params.has_key('raster'):
        self.set_integrater_parameter(
            'mosflm', 'raster',
            '%d %d %d %d %d' % tuple(integration_params['raster']))

    refinr.set_refiner_payload('mosflm_integration_parameters', None)
    pname, xname, dname = self.get_integrater_project_info()

    # what follows below should (i) be run in separate directories
    # and (ii) be repeated N=parallel times.

    parallel = Flags.get_parallel()

    # FIXME this is something of a kludge - if too few frames refinement
    # and integration does not work well... ideally want at least 15
    # frames / chunk (say)
    nframes = self._intgr_wedge[1] - self._intgr_wedge[0] + 1

    if parallel > nframes / 15:
      parallel = nframes // 15

    if not parallel:
      raise RuntimeError, 'parallel not set'
    if parallel < 2:
      raise RuntimeError, 'parallel not parallel: %s' % parallel

    jobs = []
    hklouts = []
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

      l = refinr.get_refiner_lattice()

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

      job.set_template(os.path.basename(self.get_template()))
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

    integrated_images_first = 1.0e6
    integrated_images_last = -1.0e6
    self._intgr_per_image_statistics = {}

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

      batches = job.get_batches_out()
      integrated_images_first = min(batches[0], integrated_images_first)
      integrated_images_last = max(batches[1], integrated_images_last)

      mosaics.extend(job.get_mosaic_spreads())

      if min(mosaics) < 0:
        raise IntegrationError, 'negative mosaic spread: %s' % min(mosaic)

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

      self._intgr_per_image_statistics.update(job.get_per_image_statistics())
      postref_result.update(job.get_postref_result())

      # inspect the output for e.g. very high weighted residuals

      all_residuals.extend(job.get_residuals())

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

    Chatter.write(self.show_per_image_statistics())

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
