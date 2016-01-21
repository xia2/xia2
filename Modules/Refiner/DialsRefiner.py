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
    refine.set_outlier_algorithm(PhilIndex.params.dials.outlier.algorithm)
    if PhilIndex.params.dials.fix_geometry:
      refine.set_detector_fix('all')
      refine.set_beam_fix('all')
    refine.set_close_to_spindle_cutoff(
      PhilIndex.params.dials.close_to_spindle_cutoff)
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

      indexed_experiments = idxr.get_indexer_payload("experiments_filename")
      indexed_reflections = idxr.get_indexer_payload("indexed_filename")

      if len(experiments) > 1:
        xsweeps = idxr._indxr_sweeps
        assert len(xsweeps) == len(experiments)
        assert len(self._refinr_sweeps) == 1 # don't currently support joint refinement
        xsweep = self._refinr_sweeps[0]
        i = xsweeps.index(xsweep)
        experiments = experiments[i:i+1]

        # Extract and output experiment and reflections for current sweep
        indexed_experiments = os.path.join(
          self.get_working_directory(),
          "%s_indexed_experiments.json" %xsweep.get_name())
        indexed_reflections = os.path.join(
          self.get_working_directory(),
          "%s_indexed_reflections.pickle" %xsweep.get_name())

        from dxtbx.serialize import dump
        dump.experiment_list(experiments, indexed_experiments)

        from libtbx import easy_pickle
        from scitbx.array_family import flex
        reflections = easy_pickle.load(
          idxr.get_indexer_payload("indexed_filename"))
        sel = reflections['id'] == i
        assert sel.count(True) > 0
        imageset_id = reflections['imageset_id'].select(sel)
        assert imageset_id.all_eq(imageset_id[0])
        sel = reflections['imageset_id'] == imageset_id[0]
        reflections = reflections.select(sel)
        # set indexed reflections to id == 0 and imageset_id == 0
        reflections['id'].set_selected(reflections['id'] == i, 0)
        reflections['imageset_id'] = flex.int(len(reflections), 0)
        easy_pickle.dump(indexed_reflections, reflections)

      assert len(experiments.crystals()) == 1 # currently only handle one lattice/sweep
      crystal_model = experiments.crystals()[0]
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
      refiner.set_experiments_filename(indexed_experiments)
      refiner.set_indexed_filename(indexed_reflections)

      # XXX Temporary workaround for dials.refine error for scan_varying
      # refinement with smaller wedges
      total_phi_range = idxr._indxr_imagesets[0].get_scan().get_oscillation_range()[1]
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
      self._refinr_indexed_filename = refiner.get_refined_filename()
      self.set_refiner_payload("experiments.json", self._refinr_experiments_filename)
      self.set_refiner_payload("reflections.pickle", self._refinr_indexed_filename)

      # this is the result of the cell refinement
      self._refinr_cell = experiments.crystals()[0].get_unit_cell().parameters()


  def _refine_finish(self):
    pass
