#!/usr/bin/env python
# BadLatticeError.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# An exception to be raised when an integration program decides that the
# lattice it is interating with is not appropriate for the reflections -
# most often this is the result of a pseudo-higher-symmetry lattice.


class BadLatticeError(Exception):
    """An exception to be raised when a lattice is not right."""

    def __init__(self, value):
        self.parameter = value

    def __str__(self):
        return repr(self.parameter)
