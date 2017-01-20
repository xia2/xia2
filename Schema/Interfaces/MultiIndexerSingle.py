#!/usr/bin/env python
# Indexer.py
#   Copyright (C) 2015 Diamond Light Source, Richard Gildea
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#

from __future__ import absolute_import, division

# interfaces that this inherits from ...
from xia2.Schema.Interfaces.Indexer import Indexer

class MultiIndexerSingle(Indexer):
  '''A class interface to present autoindexing functionality in a standard
  way for all indexing programs. Note that this interface defines the
  contract - what the implementation actually does is a matter for the
  implementation.'''

  LATTICE_POSSIBLE = 'LATTICE_POSSIBLE'
  LATTICE_IMPOSSIBLE = 'LATTICE_IMPOSSIBLE'
  LATTICE_CORRECT = 'LATTICE_CORRECT'

  def __init__(self):

    super(MultiIndexerSingle, self).__init__()
    self._indxr_multi_indexer = None

  def set_multi_indexer(self, multi_indexer):
    self._indxr_multi_indexer = multi_indexer

  # setters and getters of the status of the tasks - note that
  # these will cascade, so setting an early task not done will
  # set later tasks not done.

  def set_indexer_prepare_done(self, done = True):
    assert self._indxr_multi_indexer is not None
    self._indxr_multi_indexer.set_indexer_prepare_done(done)

  def set_indexer_done(self, done = True):
    assert self._indxr_multi_indexer is not None
    self._indxr_multi_indexer.set_indexer_done(done)

  def set_indexer_finish_done(self, done = True):
    assert self._indxr_multi_indexer is not None
    self._indxr_multi_indexer.set_indexer_finish_done(done)

  def get_indexer_prepare_done(self):
    assert self._indxr_multi_indexer is not None
    return self._indxr_multi_indexer.get_indexer_prepare_done()

  def get_indexer_done(self):
    assert self._indxr_multi_indexer is not None
    return self._indxr_multi_indexer.get_indexer_done()

  def get_indexer_finish_done(self):
    assert self._indxr_multi_indexer is not None
    return self._indxr_multi_indexer.get_indexer_finish_done()

  def index(self):
    assert self._indxr_multi_indexer is not None
    self._indxr_multi_indexer.index()

def multi_indexer_single_factory(indexer_cls):

  class cls(indexer_cls, MultiIndexerSingle):
    pass

  return cls()
