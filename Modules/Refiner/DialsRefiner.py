#!/usr/bin/env python
# DialsRefiner.py
#   Copyright (C) 2015 Diamond Light Source, Richard Gildea
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#

from Schema.Interfaces.Refiner import Refiner
from Handlers.Streams import Debug, Chatter
from Handlers.Flags import Flags
from Handlers.Phil import PhilIndex
from Handlers.Files import FileHandler

import os
import math

from lib.bits import auto_logfiler
from Handlers.Files import FileHandler

from Wrappers.Dials.CombineExperiments import CombineExperiments \
     as _CombineExperiments
from Wrappers.Dials.Refine import Refine as _Refine

class DialsRefiner(Refiner):

  def __init__(self):
    super(DialsRefiner, self).__init__()

  # factory functions

  def CombineExperiments(self):
    combiner = _CombineExperiments()
    combiner.set_working_directory(self.get_working_directory())
    auto_logfiler(combiner)
    for idxr in self._refinr_indexers.values():
      combiner.add_experiments(
        idxr.get_indexer_payload("experiments_filename"))
      combiner.add_reflections(idxr.get_indexed_filename())
    return combiner

  def Refine(self):
    refine = _Refine()
    params = PhilIndex.params.dials.refine
    refine.set_phil_file(params.phil_file)
    refine.set_working_directory(self.get_working_directory())
    if  PhilIndex.params.dials.fast_mode:
      # scan-static refinement in fast mode
      refine.set_scan_varying(False)
    else:
      refine.set_scan_varying(params.scan_varying)
    refine.set_use_all_reflections(params.use_all_reflections)
    if params.reflections_per_degree and not params.use_all_reflections:
      refine.set_reflections_per_degree(params.reflections_per_degree)
    refine.set_interval_width_degrees(params.interval_width_degrees)
    if PhilIndex.params.dials.outlier_rejection:
      refine.set_outlier_algorithm('tukey')
    if PhilIndex.params.dials.fix_geometry:
      refine.set_detector_fix('all')
      refine.set_beam_fix('all')
    auto_logfiler(refine, 'REFINE')

    return refine

  def _refine_prepare(self):
    pass

  def _refine(self):

    for epoch, idxr in self._refinr_indexers.iteritems():
      # decide what images we are going to process, if not already
      # specified
      #if not self._intgr_wedge:
        #images = self.get_matching_images()
        #self.set_integrater_wedge(min(images),
                    #max(images))

      #Debug.write('DIALS INTEGRATE PREPARE:')
      #Debug.write('Wavelength: %.6f' % self.get_wavelength())
      #Debug.write('Distance: %.2f' % self.get_distance())

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

      # get the unit cell from this indexer to initiate processing
      # if it is new... and also copy out all of the information for
      # the Dials indexer if not...

      experiments = idxr.get_indexer_experiment_list()
      assert len(experiments) == 1 # currently only handle one lattice/sweep
      experiment = experiments[0]
      crystal_model = experiment.crystal
      lattice = idxr.get_indexer_lattice()

      # check if the lattice was user assigned...
      user_assigned = idxr.get_indexer_user_input_lattice()

      # XXX check that the indexer is an Dials indexer - if not then
      # create one...

      # set a low resolution limit (which isn't really used...)
      # this should perhaps be done more intelligently from an
      # analysis of the spot list or something...?

      #if not self.get_integrater_low_resolution():

        #dmax = idxr.get_indexer_low_resolution()
        #self.set_integrater_low_resolution(dmax)

        #Debug.write('Low resolution set to: %s' % \
              #self.get_integrater_low_resolution())

      ## copy the data across
      from dxtbx.serialize import load, dump

      refiner = self.Refine()
      refiner.set_experiments_filename(
        idxr.get_indexer_payload("experiments_filename"))
      refiner.set_indexed_filename(
        idxr.get_indexer_payload("indexed_filename"))

      # XXX Temporary workaround for dials.refine error for scan_varying
      # refinement with smaller wedges
      all_images = idxr.get_matching_images()
      phi_width = idxr.get_phi_width()
      total_phi_range = len(all_images) * phi_width
      if total_phi_range < 5: # arbitrary value
        refiner.set_scan_varying(False)
      elif total_phi_range < 36:
        refiner.set_interval_width_degrees(total_phi_range/2)

      FileHandler.record_log_file('%s REFINE' % idxr.get_indexer_full_name(),
                                  refiner.get_log_file())
      refiner.run()
      self._refinr_experiments_filename \
        = refiner.get_refined_experiments_filename()
      experiments = load.experiment_list(self._refinr_experiments_filename)
      experiment = experiments[0]
      self._refinr_indexed_filename = idxr.get_indexer_payload("indexed_filename")
      self.set_refiner_payload("experiments.json", self._refinr_experiments_filename)
      self.set_refiner_payload("reflections.pickle", self._refinr_indexed_filename)

      # this is the result of the cell refinement
      self._refinr_cell = experiment.crystal.get_unit_cell().parameters()


  def _refine_finish(self):
    pass
