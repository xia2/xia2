#!/usr/bin/env python
# DialsIntegrater.py
#   Copyright (C) 2014 Diamond Light Source, Richard Gildea & Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# An implementation of the Integrater interface using Dials. This depends on the
# Dials wrappers to actually implement the functionality.
#

from __future__ import absolute_import, division

import os
import sys
import math
import copy

# wrappers for programs that this needs

from xia2.Wrappers.Dials.Integrate import Integrate as _Integrate
from xia2.Wrappers.Dials.Report import Report as _Report
from xia2.Wrappers.Dials.ExportMtz import ExportMtz as _ExportMtz

# interfaces that this must implement to be an integrater

from xia2.Schema.Interfaces.Integrater import Integrater

# indexing functionality if not already provided - even if it is
# we still need to reindex with DIALS.

from xia2.Modules.Indexer.DialsIndexer import DialsIndexer
from xia2.Wrappers.CCP4.Reindex import Reindex

# odds and sods that are needed

from xia2.lib.bits import auto_logfiler
from xia2.lib.SymmetryLib import lattice_to_spacegroup
from xia2.Handlers.Streams import Chatter, Debug, Journal
from xia2.Handlers.Files import FileHandler
from xia2.Handlers.Phil import PhilIndex

class DialsIntegrater(Integrater):
  '''A class to implement the Integrater interface using *only* DIALS
  programs.'''

  def __init__(self):
    super(DialsIntegrater, self).__init__()

    # check that the programs exist - this will raise an exception if
    # they do not...

    integrate = _Integrate()

    # place to store working data
    self._data_files = { }

    # internal parameters to pass around
    self._integrate_parameters = { }
    self._intgr_integrated_filename = None

  # overload these methods as we don't want the resolution range
  # feeding back... aha - but we may want to assign them
  # from outside!

  def set_integrater_resolution(self, dmin, dmax, user = False):
    if user:
      Integrater.set_integrater_resolution(self, dmin, dmax, user)

  def set_integrater_high_resolution(self, dmin, user = False):
    if user:
      Integrater.set_integrater_high_resolution(self, dmin, user)

  def set_integrater_low_resolution(self, dmax, user = False):
    self._intgr_reso_low = dmax

  # admin functions

  def get_integrated_experiments(self):
    return self._intgr_experiments_filename

  def get_integrated_filename(self):
    return self._intgr_integrated_filename

  def get_integrated_reflections(self):
    return self._intgr_integrated_pickle

  # factory functions

  def Integrate(self, indexed_filename=None):
    params = PhilIndex.params.dials.integrate
    integrate = _Integrate()
    integrate.set_phil_file(params.phil_file)

    if params.mosaic == 'new':
      integrate.set_new_mosaic()

    if PhilIndex.params.dials.fast_mode:
      integrate.set_profile_fitting(False)
    else:
      profile_fitting = PhilIndex.params.xia2.settings.integration.profile_fitting
      integrate.set_profile_fitting(profile_fitting)

    integrate.set_background_outlier_algorithm(
      params.background_outlier_algorithm)
    integrate.set_background_algorithm(
      params.background_algorithm)
    integrate.set_working_directory(self.get_working_directory())

    integrate.set_experiments_filename(self._intgr_experiments_filename)

    integrate.set_reflections_filename(self._intgr_indexed_filename)

    auto_logfiler(integrate, 'INTEGRATE')

    return integrate

  def Report(self):
    report = _Report()
    report.set_working_directory(self.get_working_directory())
    report.set_experiments_filename(self._intgr_experiments_filename)
    report.set_reflections_filename(self._intgr_integrated_pickle)
    auto_logfiler(report, 'REPORT')
    return report

  def ExportMtz(self):
    params = PhilIndex.params.dials.integrate
    export = _ExportMtz()
    export.set_working_directory(self.get_working_directory())

    export.set_experiments_filename(self._intgr_experiments_filename)
    export.set_include_partials(params.include_partials)

    auto_logfiler(export, 'EXPORTMTZ')

    return export

  # now some real functions, which do useful things

  def _integrater_reset_callback(self):
    '''Delete all results on a reset.'''
    Debug.write('Deleting all stored results.')
    self._data_files = { }
    self._integrate_parameters = { }

  def _integrate_prepare(self):
    '''Prepare for integration - in XDS terms this may mean rerunning
    IDXREF to get the XPARM etc. DEFPIX is considered part of the full
    integration as it is resolution dependent.'''

    from xia2.Handlers.Citations import Citations
    Citations.cite('dials')

    # decide what images we are going to process, if not already
    # specified
    if not self._intgr_wedge:
      images = self.get_matching_images()
      self.set_integrater_wedge(min(images),
                                max(images))

    Debug.write('DIALS INTEGRATE PREPARE:')
    Debug.write('Wavelength: %.6f' % self.get_wavelength())
    Debug.write('Distance: %.2f' % self.get_distance())

    #if not self._intgr_indexer:
      #self.set_integrater_indexer(DialsIndexer())
      #self.get_integrater_indexer().set_indexer_sweep(
          #self.get_integrater_sweep())

      #self._intgr_indexer.set_working_directory(
          #self.get_working_directory())

      #self._intgr_indexer.setup_from_imageset(self.get_imageset())

      #if self.get_frame_wedge():
        #wedge = self.get_frame_wedge()
        #Debug.write('Propogating wedge limit: %d %d' % wedge)
        #self._intgr_indexer.set_frame_wedge(wedge[0], wedge[1],
                                            #apply_offset = False)

      ## this needs to be set up from the contents of the
      ## Integrater frame processer - wavelength &c.

      #if self.get_beam_centre():
        #self._intgr_indexer.set_beam_centre(self.get_beam_centre())

      #if self.get_distance():
        #self._intgr_indexer.set_distance(self.get_distance())

      #if self.get_wavelength():
        #self._intgr_indexer.set_wavelength(
            #self.get_wavelength())

    ## get the unit cell from this indexer to initiate processing
    ## if it is new... and also copy out all of the information for
    ## the Dials indexer if not...

    #experiments = self._intgr_indexer.get_indexer_experiment_list()
    #assert len(experiments) == 1 # currently only handle one lattice/sweep
    #experiment = experiments[0]
    #crystal_model = experiment.crystal
    #lattice = self._intgr_indexer.get_indexer_lattice()

    ## check if the lattice was user assigned...
    #user_assigned = self._intgr_indexer.get_indexer_user_input_lattice()

    # XXX check that the indexer is an Dials indexer - if not then
    # create one...

    # set a low resolution limit (which isn't really used...)
    # this should perhaps be done more intelligently from an
    # analysis of the spot list or something...?

    if not self.get_integrater_low_resolution():

      dmax = self._intgr_refiner.get_indexer_low_resolution(
        self.get_integrater_epoch())
      self.set_integrater_low_resolution(dmax)

      Debug.write('Low resolution set to: %s' % \
                  self.get_integrater_low_resolution())

    ## copy the data across
    from dxtbx.serialize import load

    refiner = self.get_integrater_refiner()
    self._intgr_experiments_filename = refiner.get_refiner_payload(
      "experiments.json")
    experiments = load.experiment_list(self._intgr_experiments_filename)
    experiment = experiments[0]
    self._intgr_indexed_filename = refiner.get_refiner_payload(
      "reflections.pickle")

    # this is the result of the cell refinement
    self._intgr_cell = experiment.crystal.get_unit_cell().parameters()

    Debug.write('Files available at the end of DIALS integrate prepare:')
    for f in self._data_files.keys():
      Debug.write('%s' % f)

    self.set_detector(experiment.detector)
    self.set_beam_obj(experiment.beam)
    self.set_goniometer(experiment.goniometer)

  def _integrate(self):
    '''Actually do the integration - in XDS terms this will mean running
    DEFPIX and INTEGRATE to measure all the reflections.'''

    images_str = '%d to %d' % tuple(self._intgr_wedge)
    cell_str = '%.2f %.2f %.2f %.2f %.2f %.2f' % tuple(self._intgr_cell)

    if len(self._fp_directory) <= 50:
      dirname = self._fp_directory
    else:
      dirname = '...%s' % self._fp_directory[-46:]

    Journal.block(
        'integrating', self._intgr_sweep_name, 'DIALS',
        {'images':images_str,
         'cell':cell_str,
         'lattice':self.get_integrater_refiner().get_refiner_lattice(),
         'template':self._fp_template,
         'directory':dirname,
         'resolution':'%.2f' % self._intgr_reso_high})

    integrate = self.Integrate()

    # decide what images we are going to process, if not already
    # specified

    if not self._intgr_wedge:
      images = self.get_matching_images()
      self.set_integrater_wedge(min(images),
                                max(images))

    imageset = self.get_imageset()
    beam = imageset.get_beam()
    detector = imageset.get_detector()

    d_min_limit = detector.get_max_resolution(beam.get_s0())
    if d_min_limit > self._intgr_reso_high \
        or PhilIndex.params.xia2.settings.resolution.keep_all_reflections:
      Debug.write('Overriding high resolution limit: %f => %f' % \
                  (self._intgr_reso_high, d_min_limit))
      self._intgr_reso_high = d_min_limit

    integrate.set_experiments_filename(self._intgr_experiments_filename)
    integrate.set_reflections_filename(self._intgr_indexed_filename)
    integrate.set_d_max(self._intgr_reso_low)
    integrate.set_d_min(self._intgr_reso_high)
    pname, xname, dname = self.get_integrater_project_info()
    sweep = self.get_integrater_sweep_name()
    FileHandler.record_log_file('%s %s %s %s INTEGRATE' % \
                                (pname, xname, dname, sweep),
                                integrate.get_log_file())

    try:
      integrate.run()
    except RuntimeError, e:
      s = str(e)
      if ('dials.integrate requires more memory than is available.' in s
          and not self._intgr_reso_high):
        # Try to estimate a more sensible resolution limit for integration
        # in case we were just integrating noise to the edge of the detector
        images = self._integrate_select_images_wedges()

        Debug.write(
          'Integrating subset of images to estimate resolution limit.\n'
          'Integrating images %s' %images)

        integrate = self.Integrate()
        integrate.set_experiments_filename(self._intgr_experiments_filename)
        integrate.set_reflections_filename(self._intgr_indexed_filename)
        integrate.set_d_max(self._intgr_reso_low)
        integrate.set_d_min(self._intgr_reso_high)
        for (start, stop) in images:
          integrate.add_scan_range(start-self.get_matching_images()[0], stop-self.get_matching_images()[0])
        integrate.set_reflections_per_degree(1000)
        integrate.run()

        integrated_pickle = integrate.get_integrated_filename()

        from xia2.Wrappers.Dials.EstimateResolutionLimit import EstimateResolutionLimit
        d_min_estimater = EstimateResolutionLimit()
        d_min_estimater.set_working_directory(self.get_working_directory())
        auto_logfiler(d_min_estimater)
        d_min_estimater.set_experiments_filename(self._intgr_experiments_filename)
        d_min_estimater.set_reflections_filename(integrated_pickle)
        d_min = d_min_estimater.run()

        Debug.write('Estimate for d_min: %.2f' %d_min)
        Debug.write('Re-running integration to this resolution limit')

        self._intgr_reso_high = d_min
        self.set_integrater_done(False)
        return
      raise

    self._intgr_experiments_filename = integrate.get_integrated_experiments()

    # also record the batch range - needed for the analysis of the
    # radiation damage in chef...

    self._intgr_batches_out = (self._intgr_wedge[0], self._intgr_wedge[1])

    # FIXME (i) record the log file, (ii) get more information out from the
    # integration log on the quality of the data and (iii) the mosaic spread
    # range observed and R.M.S. deviations.

    self._intgr_integrated_pickle = integrate.get_integrated_reflections()
    if not os.path.isfile(self._intgr_integrated_pickle):
      raise RuntimeError("Integration failed: %s does not exist."
                         %self._intgr_integrated_pickle)

    self._intgr_per_image_statistics = integrate.get_per_image_statistics()
    Chatter.write(self.show_per_image_statistics())

    report = self.Report()
    html_filename = os.path.join(
      self.get_working_directory(),
      '%i_dials.integrate.report.html' %report.get_xpid())
    report.set_html_filename(html_filename)
    report.run()
    FileHandler.record_html_file('%s %s %s %s INTEGRATE' % \
                                 (pname, xname, dname, sweep),
                                 html_filename)

    import dials
    from dxtbx.serialize import load
    experiments = load.experiment_list(self._intgr_experiments_filename)
    profile = experiments.profiles()[0]
    mosaic = profile.sigma_m()
    self.set_integrater_mosaic_min_mean_max(mosaic, mosaic, mosaic)

    Chatter.write('Mosaic spread: %.3f < %.3f < %.3f' % \
                  self.get_integrater_mosaic_min_mean_max())

    return self._intgr_integrated_pickle

  def _integrate_finish(self):
    '''Finish off the integration by running dials.export.'''

    # FIXME - do we want to export every time we call this method
    # (the file will not have changed) and also (more important) do
    # we want a different exported MTZ file every time (I do not think
    # that we do; these can be very large) - was exporter.get_xpid() ->
    # now dials

    exporter = self.ExportMtz()
    exporter.set_reflections_filename(self._intgr_integrated_pickle)
    mtz_filename = os.path.join(
      self.get_working_directory(), '%s_integrated.mtz' % 'dials')
    exporter.set_mtz_filename(mtz_filename)
    exporter.run()
    self._intgr_integrated_filename = mtz_filename

    # record integrated MTZ file for e.g. BLEND.

    pname, xname, dname = self.get_integrater_project_info()
    sweep = self.get_integrater_sweep_name()
    FileHandler.record_more_data_file(
        '%s %s %s %s INTEGRATE' % (pname, xname, dname, sweep), mtz_filename)

    from iotbx.reflection_file_reader import any_reflection_file
    miller_arrays = any_reflection_file(self._intgr_integrated_filename).as_miller_arrays()
    # look for profile-fitted intensities
    intensities = [ma for ma in miller_arrays
                   if ma.info().labels == ['IPR', 'SIGIPR']]
    if len(intensities) == 0:
      # look instead for summation-integrated intensities
      intensities = [ma for ma in miller_arrays
                     if ma.info().labels == ['I', 'SIGI']]
      assert len(intensities)
    self._intgr_n_ref = intensities[0].size()

    if not os.path.isfile(self._intgr_integrated_filename):
      raise RuntimeError("dials.export failed: %s does not exist."
                         % self._intgr_integrated_filename)

    if self._intgr_reindex_operator is None and \
      self._intgr_spacegroup_number == lattice_to_spacegroup(
        self.get_integrater_refiner().get_refiner_lattice()):
      Debug.write('Not reindexing to spacegroup %d (%s)' % \
                    (self._intgr_spacegroup_number,
                     self._intgr_reindex_operator))
      return mtz_filename

    if self._intgr_reindex_operator is None and \
      self._intgr_spacegroup_number == 0:
      Debug.write('Not reindexing to spacegroup %d (%s)' % \
                    (self._intgr_spacegroup_number,
                     self._intgr_reindex_operator))
      return mtz_filename

    Debug.write('Reindexing to spacegroup %d (%s)' % \
                (self._intgr_spacegroup_number,
                 self._intgr_reindex_operator))

    hklin = mtz_filename
    reindex = Reindex()
    reindex.set_working_directory(self.get_working_directory())
    auto_logfiler(reindex)

    reindex.set_operator(self._intgr_reindex_operator)

    if self._intgr_spacegroup_number:
      reindex.set_spacegroup(self._intgr_spacegroup_number)
    else:
      reindex.set_spacegroup(lattice_to_spacegroup(
        self.get_integrater_refiner().get_refiner_lattice()))

    hklout = '%s_reindex.mtz' % hklin[:-4]
    reindex.set_hklin(hklin)
    reindex.set_hklout(hklout)
    reindex.reindex()
    self._intgr_integrated_filename = hklout
    self._intgr_cell = reindex.get_cell()

    pname, xname, dname = self.get_integrater_project_info()
    sweep = self.get_integrater_sweep_name()
    FileHandler.record_more_data_file(
      '%s %s %s %s experiments' % (pname, xname, dname, sweep),
      self.get_integrated_experiments())

    return hklout

  def _integrate_select_images_wedges(self):
    '''Select correct images based on image headers.'''

    phi_width = self.get_phi_width()

    images = self.get_matching_images()

    # characterise the images - are there just two (e.g. dna-style
    # reference images) or is there a full block?

    wedges = []

    if len(images) < 3:
      # work on the assumption that this is a reference pair

      wedges.append(images[0])

      if len(images) > 1:
        wedges.append(images[1])

    else:
      block_size = min(len(images), int(math.ceil(5/phi_width)))

      Debug.write('Adding images for indexer: %d -> %d' % \
                  (images[0], images[block_size - 1]))

      wedges.append((images[0], images[block_size - 1]))

      if int(90.0 / phi_width) + block_size in images:
        # assume we can add a wedge around 45 degrees as well...
        Debug.write('Adding images for indexer: %d -> %d' % \
                    (int(45.0 / phi_width) + images[0],
                     int(45.0 / phi_width) + images[0] +
                     block_size - 1))
        Debug.write('Adding images for indexer: %d -> %d' % \
                    (int(90.0 / phi_width) + images[0],
                     int(90.0 / phi_width) + images[0] +
                     block_size - 1))
        wedges.append(
            (int(45.0 / phi_width) + images[0],
             int(45.0 / phi_width) + images[0] + block_size - 1))
        wedges.append(
            (int(90.0 / phi_width) + images[0],
             int(90.0 / phi_width) + images[0] + block_size - 1))

      else:

        # add some half-way anyway
        first = (len(images) // 2) - (block_size // 2) + images[0] - 1
        if first > wedges[0][1]:
          last = first + block_size - 1
          Debug.write('Adding images for indexer: %d -> %d' % \
                      (first, last))
          wedges.append((first, last))
        if len(images) > block_size:
          Debug.write('Adding images for indexer: %d -> %d' % \
                      (images[- block_size], images[-1]))
          wedges.append((images[- block_size], images[-1]))

    return wedges

  def get_integrater_corrected_intensities(self):
    self.integrate()
    from xia2.Wrappers.Dials.ExportXDSASCII import ExportXDSASCII
    exporter = ExportXDSASCII()
    exporter.set_experiments_filename(self.get_integrated_experiments())
    exporter.set_reflections_filename(self.get_integrated_reflections())
    exporter.set_working_directory(self.get_working_directory())
    auto_logfiler(exporter)
    self._intgr_corrected_hklout = os.path.join(
      self.get_working_directory(), '%i_DIALS.HKL' %exporter.get_xpid())
    exporter.set_hkl_filename(self._intgr_corrected_hklout)
    exporter.run()
    assert os.path.exists(self._intgr_corrected_hklout)
    return self._intgr_corrected_hklout


if __name__ == '__main__':

  # run a demo test

  di = DialsIntegrater()
  di.setup_from_image(sys.argv[1])
  from xia2.Schema.XCrystal import XCrystal
  from xia2.Schema.XWavelength import XWavelength
  from xia2.Schema.XSweep import XSweep
  cryst = XCrystal("CRYST1", None)
  wav = XWavelength("WAVE1", cryst, di.get_wavelength())
  directory, image = os.path.split(sys.argv[1])
  sweep = XSweep('SWEEP1', wav, directory=directory, image=image)
  di.set_integrater_sweep(sweep)
  di.integrate()
