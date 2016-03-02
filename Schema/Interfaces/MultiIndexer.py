#!/usr/bin/env python
# Indexer.py
#   Copyright (C) 2015 Diamond Light Source, Richard Gildea
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#

import os
import sys
import inspect

from xia2.Handlers.Streams import Debug, Chatter
from xia2.Handlers.Phil import PhilIndex

from xia2.Experts.LatticeExpert import SortLattices

# interfaces that this inherits from ...
from xia2.Schema.Interfaces.Indexer import Indexer


class MultiIndexer(Indexer):
  '''A class interface to present autoindexing functionality in a standard
  way for all indexing programs. Note that this interface defines the
  contract - what the implementation actually does is a matter for the
  implementation.'''

  def __init__(self):

    super(MultiIndexer, self).__init__()

    self._indxr_sweeps = []
    self._indxr_indexers = []

    return

  def add_indexer_sweep(self, sweep):
    self._indxr_sweeps.append(sweep)

  def get_indexer_sweeps(self):
    return self._indxr_sweeps

  def add_indexer(self, indexer):
    self._indxr_indexers.append(indexer)

  def get_indexers(self):
    return self._indxr_indexers
