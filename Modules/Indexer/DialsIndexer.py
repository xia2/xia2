#!/usr/bin/env python
# DialsIndexer.py
#   Copyright (C) 2014 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# An indexer using the DIALS methods.

import os
import sys
import math
import shutil

if not os.environ.has_key('XIA2_ROOT'):
  raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
  sys.path.append(os.environ['XIA2_ROOT'])

import libtbx

# wrappers for programs that this needs: DIALS

from Wrappers.Dials.Import import Import as _Import
from Wrappers.Dials.Spotfinder import Spotfinder as _Spotfinder
from Wrappers.Dials.DiscoverBetterExperimentalModel \
     import DiscoverBetterExperimentalModel as _DiscoverBetterExperimentalModel
from Wrappers.Dials.Index import Index as _Index
from Wrappers.Dials.CheckIndexingSymmetry \
     import CheckIndexingSymmetry as _CheckIndexingSymmetry
from Wrappers.Dials.Reindex import Reindex as _Reindex
from Wrappers.Dials.Refine import Refine as _Refine
from Wrappers.Dials.RefineBravaisSettings import RefineBravaisSettings as \
     _RefineBravaisSettings

# interfaces that this must implement to be an indexer

from Schema.Interfaces.Indexer import Indexer

# odds and sods that are needed

from lib.bits import auto_logfiler, nint
from Handlers.Streams import Chatter, Debug, Journal
from Handlers.Flags import Flags
from Handlers.Phil import PhilIndex
from Handlers.Files import FileHandler
from Experts.SymmetryExpert import lattice_to_spacegroup_number

class DialsIndexer(Indexer):
  def __init__(self):
    super(DialsIndexer, self).__init__()

    self._background_images = None

    # place to store working data

    self._data_files = { }
    self._solutions = { }

    # FIXME this is a stupid low resolution limit to use...
    self._indxr_low_resolution = 40.0

    return

  # admin functions

  def get_indexed_filename(self):
    return self.get_indexer_payload("indexed_filename")

  # factory functions

  def Import(self):
    importer = _Import()
    importer.set_working_directory(self.get_working_directory())
    importer.setup_from_imageset(self.get_imageset())
    auto_logfiler(importer)
    importer.set_mosflm_beam_centre(self.get_beam_centre())
    importer.set_sweep_filename(
      os.path.join(self.get_working_directory(),
                   '%s_datablock_import.json' %importer.get_xpid()))
    return importer

  def Spotfinder(self):
    spotfinder = _Spotfinder()
    spotfinder.set_working_directory(self.get_working_directory())
    auto_logfiler(spotfinder)
    return spotfinder

  def DiscoverBetterExperimentalModel(self):
    discovery = _DiscoverBetterExperimentalModel()
    discovery.set_working_directory(self.get_working_directory())
    #params = PhilIndex.params.dials.index
    auto_logfiler(discovery)
    return discovery

  def Index(self):
    index = _Index()
    index.set_working_directory(self.get_working_directory())
    params = PhilIndex.params.dials.index
    index.set_use_all_reflections(params.use_all_reflections)
    if params.fft3d.n_points is not None:
      index.set_fft3d_n_points(params.fft3d.n_points)
    auto_logfiler(index)
    index.set_outlier_algorithm(PhilIndex.params.dials.outlier.algorithm)
    return index

  def CheckIndexingSymmetry(self):
    checksym = _CheckIndexingSymmetry()
    checksym.set_working_directory(self.get_working_directory())
    auto_logfiler(checksym)
    return checksym

  def Reindex(self):
    reindex = _Reindex()
    reindex.set_working_directory(self.get_working_directory())
    auto_logfiler(reindex)
    return reindex

  def Refine(self):
    refine = _Refine()
    params = PhilIndex.params.dials.refine
    refine.set_working_directory(self.get_working_directory())
    refine.set_scan_varying(False)
    refine.set_outlier_algorithm(PhilIndex.params.dials.outlier.algorithm)
    refine.set_close_to_spindle_cutoff(
      PhilIndex.params.dials.close_to_spindle_cutoff)
    if PhilIndex.params.dials.fix_geometry:
      refine.set_detector_fix('all')
      refine.set_beam_fix('all')
    auto_logfiler(refine)
    return refine

  def RefineBravaisSettings(self):
    rbs = _RefineBravaisSettings()
    rbs.set_working_directory(self.get_working_directory())
    rbs.set_close_to_spindle_cutoff(
      PhilIndex.params.dials.close_to_spindle_cutoff)
    auto_logfiler(rbs)
    return rbs

  ##########################################

  def _index_select_images_i(self):
    # FIXME copied from XDSIndexer.py!
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
      block_size = min(len(images), 5)

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

  def _index_prepare(self):

    from Handlers.Citations import Citations
    Citations.cite('dials')

    #all_images = self.get_matching_images()
    #first = min(all_images)
    #last = max(all_images)

    spot_lists = []
    datablocks = []

    for imageset, xsweep in zip(self._indxr_imagesets, self._indxr_sweeps):

      first, last = self._indxr_imagesets[0].get_scan().get_image_range()
      self._indxr_images = [(first, last)]

      # at this stage, break out to run the DIALS code: this sets itself up
      # now cheat and pass in some information... save re-reading all of the
      # image headers

      # FIXME need to adjust this to allow (say) three chunks of images

      from dxtbx.serialize import dump
      from dxtbx.datablock import DataBlock
      sweep_filename = os.path.join(
        self.get_working_directory(), '%s_datablock.json' %xsweep.get_name())
      dump.datablock(DataBlock([imageset]), sweep_filename)

      # FIXME this should really use the assigned spot finding regions
      #offset = self.get_frame_offset()
      spotfinder = self.Spotfinder()
      if last - first > 10:
        spotfinder.set_write_hot_mask(True)
      spotfinder.set_input_sweep_filename(sweep_filename)
      spotfinder.set_output_sweep_filename(
        '%s_%s_datablock.json' %(spotfinder.get_xpid(), xsweep.get_name()))
      spotfinder.set_input_spot_filename(
        '%s_%s_strong.pickle' %(spotfinder.get_xpid(), xsweep.get_name()))
      if PhilIndex.params.dials.fast_mode:
        wedges = self._index_select_images_i()
        spotfinder.set_scan_ranges(wedges)
      else:
        spotfinder.set_scan_ranges([(first, last)])
      if PhilIndex.params.dials.find_spots.phil_file is not None:
        spotfinder.set_phil_file(PhilIndex.params.dials.find_spots.phil_file)
      min_spot_size = PhilIndex.params.dials.find_spots.min_spot_size
      if min_spot_size is libtbx.Auto:
        if imageset.get_detector()[0].get_type() == 'SENSOR_PAD':
          min_spot_size = 3
        else:
          min_spot_size = None
      if min_spot_size is not None:
        spotfinder.set_min_spot_size(min_spot_size)
      min_local = PhilIndex.params.dials.find_spots.min_local
      if min_local is not None:
        spotfinder.set_min_local(min_local)
      sigma_strong = PhilIndex.params.dials.find_spots.sigma_strong
      if sigma_strong:
        spotfinder.set_sigma_strong(sigma_strong)
      filter_ice_rings = PhilIndex.params.dials.find_spots.filter_ice_rings
      if filter_ice_rings:
        spotfinder.set_filter_ice_rings(filter_ice_rings)
      kernel_size = PhilIndex.params.dials.find_spots.kernel_size
      if kernel_size:
        spotfinder.set_kernel_size(kernel_size)
      global_threshold = PhilIndex.params.dials.find_spots.global_threshold
      if global_threshold is not None:
        spotfinder.set_global_threshold(global_threshold)
      spotfinder.run()

      spot_filename = spotfinder.get_spot_filename()
      if not os.path.exists(spot_filename):
        raise RuntimeError("Spotfinding failed: %s does not exist."
                           %os.path.basename(spot_filename))

      spot_lists.append(spot_filename)
      datablocks.append(spotfinder.get_output_sweep_filename())

      if 0 and not PhilIndex.params.xia2.settings.trust_beam_centre:
        discovery = self.DiscoverBetterExperimentalModel()
        discovery.set_sweep_filename(self.get_indexer_payload("datablock.json"))
        discovery.set_spot_filename(spot_filename)
        wedges = self._index_select_images_i()
        discovery.set_scan_ranges(wedges)
        #discovery.set_scan_ranges([(first + offset, last + offset)])
        try:
          discovery.run()
        except Exception, e:
          Debug.write('DIALS beam centre search failed: %s' %str(e))
        else:
          datablocks.append(discovery.get_optimized_datablock_filename())

    self.set_indexer_payload("spot_lists", spot_lists)
    self.set_indexer_payload("datablocks", datablocks)

    return

  def _index(self):
    if PhilIndex.params.dials.index.method is None:
      if self._indxr_input_cell is not None:
        indexer = self._do_indexing("real_space_grid_search")
      else:
        indexer_fft3d = self._do_indexing(method="fft3d")
        nref_3d, rmsd_3d = indexer_fft3d.get_nref_rmsds()
        indexer_fft1d = self._do_indexing(method="fft1d")
        nref_1d, rmsd_1d = indexer_fft1d.get_nref_rmsds()

        if (nref_1d > nref_3d and
            rmsd_1d[0] < rmsd_3d[0] and
            rmsd_1d[1] < rmsd_3d[1] and
            rmsd_1d[2] < rmsd_3d[2]):
          indexer = indexer_fft1d
        else:
          indexer = indexer_fft3d

    else:
      indexer = self._do_indexing(
        method=PhilIndex.params.dials.index.method)

    # not strictly the P1 cell, rather the cell that was used in indexing
    self._p1_cell = indexer._p1_cell
    self.set_indexer_payload(
      "indexed_filename", indexer.get_indexed_filename())

    from cctbx.sgtbx import bravais_types
    from dxtbx.serialize import load

    indexed_file = indexer.get_indexed_filename()
    indexed_experiments = indexer.get_experiments_filename()

    trust_beam_centre = PhilIndex.params.xia2.settings.trust_beam_centre
    multi_sweep_indexing = PhilIndex.params.xia2.settings.developmental.multi_sweep_indexing

    if not trust_beam_centre and not multi_sweep_indexing:
      checksym = self.CheckIndexingSymmetry()
      checksym.set_experiments_filename(indexed_experiments)
      checksym.set_indexed_filename(indexed_file)
      checksym.set_grid_search_scope(1)
      checksym.run()
      hkl_offset = checksym.get_hkl_offset()
      Debug.write("hkl_offset: %s" %str(hkl_offset))
      if hkl_offset is not None and hkl_offset != (0,0,0):
        reindex = self.Reindex()
        reindex.set_hkl_offset(hkl_offset)
        reindex.set_indexed_filename(indexed_file)
        reindex.run()
        indexed_file = reindex.get_reindexed_reflections_filename()

        # do some scan-static refinement - run twice, first without outlier
        # rejection as the model is too far from reality to do a sensible job of
        # outlier rejection
        refiner = self.Refine()
        refiner.set_experiments_filename(indexed_experiments)
        refiner.set_indexed_filename(
            reindex.get_reindexed_reflections_filename())
        refiner.set_outlier_algorithm(None)
        refiner.run()
        indexed_experiments = refiner.get_refined_experiments_filename()

        # now again with outlier rejection (possibly)
        refiner = self.Refine()
        refiner.set_experiments_filename(indexed_experiments)
        refiner.set_indexed_filename(indexed_file)
        refiner.run()
        indexed_experiments = refiner.get_refined_experiments_filename()

    if self._indxr_input_lattice is None:

      # FIXME in here should respect the input unit cell and lattice if provided

      # FIXME from this (i) populate the helper table,
      # (ii) try to avoid re-running the indexing
      # step if we eliminate a solution as we have all of the refined results
      # already available.

      rbs = self.RefineBravaisSettings()
      rbs.set_experiments_filename(indexed_experiments)
      rbs.set_indexed_filename(indexed_file)
      if PhilIndex.params.dials.fix_geometry:
        rbs.set_detector_fix('all')
        rbs.set_beam_fix('all')

      FileHandler.record_log_file('%s LATTICE' % self.get_indexer_full_name(),
                                  rbs.get_log_file())
      rbs.run()

      rmsd_p1 = rbs.get_bravais_summary()[1]['rmsd']

      from cctbx import crystal, sgtbx

      for k in sorted(rbs.get_bravais_summary()):
        summary = rbs.get_bravais_summary()[k]

        # FIXME need to do this better - for the moment only accept lattices
        # where R.M.S. deviation is less than twice P1 R.M.S. deviation.

        if self._indxr_input_lattice is None:
          if summary['max_angular_difference'] < 0.5:
            if summary['min_cc'] < 0.5 and summary['rmsd'] > 1.5 * rmsd_p1:
              continue
          elif summary['min_cc'] < 0.7 and summary['rmsd'] > 2.0 * rmsd_p1:
            continue
          elif summary['rmsd'] > 3 * rmsd_p1:
            continue

        experiments = load.experiment_list(
          summary['experiments_file'], check_format=False)
        cryst = experiments.crystals()[0]
        cs = crystal.symmetry(unit_cell=cryst.get_unit_cell(),
                              space_group=cryst.get_space_group())
        cb_op_best_to_ref = cs.change_of_basis_op_to_reference_setting()
        cs_reference = cs.change_basis(cb_op_best_to_ref)
        lattice = str(bravais_types.bravais_lattice(
          group=cs_reference.space_group()))
        cb_op = cb_op_best_to_ref * sgtbx.change_of_basis_op(str(summary['cb_op']))

        self._solutions[k] = {
          'number':k,
          'mosaic':0.0,
          'metric':summary['max_angular_difference'],
          'rmsd':summary['rmsd'],
          'nspots':summary['nspots'],
          'lattice':lattice,
          'cell':cs_reference.unit_cell().parameters(),
          'experiments_file':summary['experiments_file'],
          'cb_op':str(cb_op)
          }

      self._solution = self.get_solution()
      self._indxr_lattice = self._solution['lattice']

      for solution in self._solutions.keys():
        lattice = self._solutions[solution]['lattice']
        if (self._indxr_input_lattice is not None and
            self._indxr_input_lattice != lattice):
          continue
        if self._indxr_other_lattice_cell.has_key(lattice):
          if self._indxr_other_lattice_cell[lattice]['metric'] < \
            self._solutions[solution]['metric']:
            continue

        self._indxr_other_lattice_cell[lattice] = {
          'metric':self._solutions[solution]['metric'],
          'cell':self._solutions[solution]['cell']}

      self._indxr_mosaic = self._solution['mosaic']

      experiment_list = load.experiment_list(self._solution['experiments_file'])
      self.set_indexer_experiment_list(experiment_list)

      # reindex the output experiments list to the reference setting
      # (from the best cell/conventional setting)
      cb_op_to_ref = experiment_list.crystals()[0].get_space_group().info()\
        .change_of_basis_op_to_reference_setting()
      reindex = self.Reindex()
      reindex.set_experiments_filename(self._solution['experiments_file'])
      reindex.set_cb_op(cb_op_to_ref)
      reindex.set_space_group(str(lattice_to_spacegroup_number(
        self._solution['lattice'])))
      reindex.run()
      experiments_file = reindex.get_reindexed_experiments_filename()
      experiment_list = load.experiment_list(experiments_file)
      self.set_indexer_experiment_list(experiment_list)
      self.set_indexer_payload("experiments_filename", experiments_file)

      # reindex the output reflection list to this solution
      reindex = self.Reindex()
      reindex.set_indexed_filename(indexed_file)
      reindex.set_cb_op(self._solution['cb_op'])
      reindex.set_space_group(str(lattice_to_spacegroup_number(
        self._solution['lattice'])))
      reindex.run()
      indexed_file = reindex.get_reindexed_reflections_filename()
      self.set_indexer_payload("indexed_filename", indexed_file)

    else:
      experiment_list = load.experiment_list(indexed_experiments)
      self.set_indexer_experiment_list(experiment_list)
      self.set_indexer_payload("experiments_filename", indexed_experiments)

      cryst = experiment_list.crystals()[0]
      lattice = str(bravais_types.bravais_lattice(
        group=cryst.get_space_group()))
      self._solutions = {}
      self._solutions[0] = {
        'number':0,
        'mosaic':0.0,
        'metric':-1,
        'rmsd':-1,
        'nspots':-1,
        'lattice':lattice,
        'cell':cryst.get_unit_cell().parameters(),
        'experiments_file':indexed_experiments,
        'cb_op':'a,b,c'
      }

      self._indxr_other_lattice_cell[lattice] = {
        'metric':self._solutions[0]['metric'],
        'cell':self._solutions[0]['cell']}

    return

  def _do_indexing(self, method=None):
    indexer = self.Index()
    for spot_list in self._indxr_payload["spot_lists"]:
      indexer.add_spot_filename(spot_list)
    for datablock in self._indxr_payload["datablocks"]:
      indexer.add_sweep_filename(datablock)
    if PhilIndex.params.dials.index.phil_file is not None:
      indexer.set_phil_file(PhilIndex.params.dials.index.phil_file)
    if PhilIndex.params.dials.index.max_cell:
      indexer.set_max_cell(PhilIndex.params.dials.index.max_cell)
    if Flags.get_small_molecule():
      indexer.set_min_cell(3)
    if PhilIndex.params.dials.fix_geometry:
      indexer.set_detector_fix('all')
      indexer.set_beam_fix('all')
    indexer.set_close_to_spindle_cutoff(
      PhilIndex.params.dials.close_to_spindle_cutoff)

    if self._indxr_input_lattice:
      indexer.set_indexer_input_lattice(self._indxr_input_lattice)
      Debug.write('Set lattice: %s' % self._indxr_input_lattice)

    if self._indxr_input_cell:
      indexer.set_indexer_input_cell(self._indxr_input_cell)
      Debug.write('Set cell: %f %f %f %f %f %f' % \
                  self._indxr_input_cell)
      original_cell = self._indxr_input_cell

    if method is None:
      if PhilIndex.params.dials.index.method is None:
        method = 'fft3d'
        Debug.write('Choosing indexing method: %s' % method)
      else:
        method = PhilIndex.params.dials.index.method

    FileHandler.record_log_file('%s INDEX' % self.get_indexer_full_name(),
                                indexer.get_log_file())
    indexer.run(method)

    if not os.path.exists(indexer.get_experiments_filename()):
      raise RuntimeError("Indexing has failed: %s does not exist."
                         %indexer.get_experiments_filename())
    elif not os.path.exists(indexer.get_indexed_filename()):
      raise RuntimeError("Indexing has failed: %s does not exist."
                         %indexer.get_indexed_filename())

    return indexer


  def _compare_cell(self, c_ref, c_test):
    '''Compare two sets of unit cell constants: if they differ by
    less than 5% / 5 degrees return True, else False.'''

    for j in range(3):
      if math.fabs((c_test[j] - c_ref[j]) / c_ref[j]) > 0.05:
        return False

    for j in range(3, 6):
      if math.fabs(c_test[j] - c_ref[j]) > 5:
        return False

    return True

  def get_solutions():
    return self._solutions

  def get_solution(self):

    import copy

    # FIXME I really need to clean up the code in here...

    if self._indxr_input_lattice is None:
      if PhilIndex.params.xia2.settings.integrate_p1:
        return copy.deepcopy(self._solutions[1])
      return copy.deepcopy(
        self._solutions[max(self._solutions.keys())])
    else:
      if self._indxr_input_cell:
        for s in self._solutions.keys():
          if self._solutions[s]['lattice'] == \
            self._indxr_input_lattice:
            if self._compare_cell(
                self._indxr_input_cell,
                self._solutions[s]['cell']):
              return copy.deepcopy(self._solutions[s])
            else:
              del(self._solutions[s])
          else:
            del(self._solutions[s])

        raise RuntimeError, \
          'no solution for lattice %s with given cell' % \
          self._indxr_input_lattice

      else:
        for s in self._solutions.keys():
          if self._solutions[s]['lattice'] == \
            self._indxr_input_lattice:
            return copy.deepcopy(self._solutions[s])
          else:
            del(self._solutions[s])

        raise RuntimeError, 'no solution for lattice %s' % \
          self._indxr_input_lattice

    return

  def _index_finish(self):
    # get estimate of low resolution limit from lowest resolution indexed
    # reflection

    from libtbx import easy_pickle
    from cctbx import crystal, miller, uctbx
    reflections = easy_pickle.load(self._indxr_payload["indexed_filename"])
    miller_indices = reflections['miller_index']
    miller_indices = miller_indices.select(miller_indices != (0,0,0))
    # it isn't necessarily the 'p1_cell', but it should be the cell that
    # corresponds to the miller indices in the indexed.pickle
    symmetry = crystal.symmetry(
      unit_cell=uctbx.unit_cell(self._p1_cell))
    miller_set = miller.set(symmetry, miller_indices)
    d_max, d_min = miller_set.d_max_min()
    d_max *= 1.05 # include an upper margin to avoid rounding errors
    Debug.write('Low resolution limit assigned as: %.2f' % d_max)
    self._indxr_low_resolution = d_max

    return
