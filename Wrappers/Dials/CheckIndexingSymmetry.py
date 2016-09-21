#!/usr/bin/env python
# CheckIndexingSymmetry.py
#
#   Copyright (C) 2015 Diamond Light Source, Richard Gildea
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Wrapper for dials.check_indexing_symmetry

from __future__ import division

import os

from __init__ import _setup_xia2_environ
_setup_xia2_environ()

def CheckIndexingSymmetry(DriverType = None):
  '''A factory for CheckIndexingSymmetryWrapper classes.'''

  from xia2.Driver.DriverFactory import DriverFactory
  DriverInstance = DriverFactory.Driver(DriverType)

  class CheckIndexingSymmetryWrapper(DriverInstance.__class__):

    def __init__(self):
      DriverInstance.__class__.__init__(self)
      self.set_executable('dials.check_indexing_symmetry')

      self._experiments_filename = None
      self._indexed_filename = None
      self._grid_search_scope = None

      return

    def set_experiments_filename(self, experiments_filename):
      self._experiments_filename = experiments_filename
      return

    def set_indexed_filename(self, indexed_filename):
      self._indexed_filename = indexed_filename
      return

    def set_grid_search_scope(self, grid_search_scope):
      self._grid_search_scope = abs(int(grid_search_scope))
      return

    def run(self):
      from xia2.Handlers.Streams import Debug
      Debug.write('Running dials.check_indexing_symmetry')

      wd = self.get_working_directory()

      self.clear_command_line()
      assert self._experiments_filename is not None
      self.add_command_line(self._experiments_filename)
      assert self._indexed_filename is not None
      self.add_command_line(self._indexed_filename)
      if self._grid_search_scope is not None:
        self.add_command_line("grid_search_scope=%s" % self._grid_search_scope)
      self.add_command_line("symop_threshold=0.7")
      self.start()
      self.close_wait()
      self.check_for_errors()

      lines = self.get_all_output()
      hkl_offsets = {}
      hkl_nref = {}
      for i, line in enumerate(lines):
        line = line.strip()
        if line.startswith('dH dK dL   Nref    CC'):
          while True:
            i += 1
            line = lines[i].strip()
            if line == '': break
            tokens = line.split()
            assert len(tokens) == 5
            h, k, l = [int(t) for t in tokens[:3]]
            nref, cc = [float(t) for t in tokens[3:]]
            hkl_offsets[(h,k,l)] = cc
            hkl_nref[(h,k,l)] = nref

      Debug.write("hkl_offset scores: %s" %str(hkl_offsets))
      Debug.write("hkl_nref scores: %s" %str(hkl_nref))
      if len(hkl_offsets) > 1:
        max_offset = max(hkl_offsets.values())
        max_nref = max(hkl_nref.values())

        # select "best" solution - needs nref > 0.5 max nref && highest CC
        # FIXME perform proper statistical test in here do not like heuristics

        best_hkl = 0,0,0
        best_hkl_score = 0.0

        for hkl in hkl_nref:
          if hkl_nref[hkl] < max_nref // 2:
            continue
          if hkl_offsets[hkl] > best_hkl_score:
            best_hkl_score = hkl_offsets[hkl]
            best_hkl = hkl

        self._hkl_offset = best_hkl
      else:
        self._hkl_offset = None

    def get_hkl_offset(self):
      return self._hkl_offset

  return CheckIndexingSymmetryWrapper()
