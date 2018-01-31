#!/usr/bin/env python
# IndexingError.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# An exception to be raised when an indexing program decides that there
# is a specific problem with indexing - this should be recoverable.

from __future__ import absolute_import, division

class IndexingError(Exception):
  '''An exception to be raised when a lattice is not right.'''

  def __init__(self, value):
    self.parameter = value

  def __str__(self):
    return repr(self.parameter)
