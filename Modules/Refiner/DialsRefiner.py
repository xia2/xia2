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

    self._sweep_handler = None

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
    refine.set_working_directory(self.get_working_directory())
    refine.set_scan_varying(False)
    refine.set_use_all_reflections(True)
    auto_logfiler(refine, 'REFINE')
    return refine

  def _refine_prepare(self):
    combiner = self.CombineExperiments()
    combiner.run()
    self._refinr_combined_experiments = combiner.get_combined_experiments_filename()
    self._refinr_combined_reflections = combiner.get_combined_reflections_filename()

  def _refine(self):
    refine = self.Refine()
    refine.set_experiments_filename(self._refinr_combined_experiments)
    refine.set_indexed_filename(self._refinr_combined_reflections)
    refine.run()
    from dxtbx.serialize import load
    refined_experiments = load.experiment_list(
      refine.get_refined_experiments_filename())
    self._refinr_refined_experiment_list = refined_experiments

  def _refine_finish(self):
    pass
