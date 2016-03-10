#!/usr/bin/env python
# DialsIndexer.py
#   Copyright (C) 2015 Diamond Light Source, Richard Gildea
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# An indexer using the DIALS methods.

import os
import sys
import math
import shutil

import libtbx

# wrappers for programs that this needs: DIALS

from xia2.Wrappers.Dials.Import import Import as _Import
from xia2.Wrappers.Dials.Spotfinder import Spotfinder as _Spotfinder
from xia2.Wrappers.Dials.DiscoverBetterExperimentalModel \
     import DiscoverBetterExperimentalModel as _DiscoverBetterExperimentalModel
from xia2.Wrappers.Dials.Index import Index as _Index
from xia2.Wrappers.Dials.Reindex import Reindex as _Reindex
from xia2.Wrappers.Dials.RefineBravaisSettings import RefineBravaisSettings as \
     _RefineBravaisSettings

# interfaces that this must implement to be an indexer

from xia2.Schema.Interfaces.MultiIndexer import MultiIndexer
from xia2.Modules.Indexer.DialsIndexer import DialsIndexer

# odds and sods that are needed

from xia2.lib.bits import auto_logfiler, nint
from xia2.Handlers.Streams import Chatter, Debug, Journal
from xia2.Handlers.Flags import Flags
from xia2.Handlers.Phil import PhilIndex
from xia2.Handlers.Files import FileHandler
from xia2.Experts.SymmetryExpert import lattice_to_spacegroup_number

class DialsMultiIndexer(DialsIndexer, MultiIndexer):

  def _index_prepare(self):
    for indxr in self._indxr_indexers:
      indxr._index_prepare()
    return

  def _do_indexing(self, method=None):
    indexer = self.Index()
    for indxr in self._indxr_indexers:
      indexer.add_spot_filename(indxr._indxr_payload["spot_list"])
      indexer.add_sweep_filename(indxr._indxr_payload["datablock.json"])
    if PhilIndex.params.dials.index.phil_file is not None:
      indexer.set_phil_file(PhilIndex.params.dials.index.phil_file)
    if PhilIndex.params.dials.index.max_cell:
      indexer.set_max_cell(PhilIndex.params.dials.index.max_cell)
    if Flags.get_small_molecule():
      indexer.set_min_cell(3)
    if PhilIndex.params.dials.fix_geometry:
      indexer.set_detector_fix('all')
      indexer.set_beam_fix('all')

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

    indexer.run(method)

    if not os.path.exists(indexer.get_experiments_filename()):
      raise RuntimeError("Indexing has failed: %s does not exist."
                         %indexer.get_experiments_filename())
    elif not os.path.exists(indexer.get_indexed_filename()):
      raise RuntimeError("Indexing has failed: %s does not exist."
                         %indexer.get_indexed_filename())

    return indexer

  def _index_finish(self):
    super(DialsMultiIndexer, self)._index_finish()
    for i, indxr in enumerate(self._indxr_indexers):
      indxr._indxr_experiment_list = self._indxr_experiment_list[i:i+1]

    return
