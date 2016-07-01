#!/usr/bin/env python
# Executables.py
#   Copyright (C) 2012 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 17 January 2012
#
# A handler for setting the executables to use for processing tasks,
# interfaced to the command line via -executable program=path.

import sys
import os

class _Executables(object):
  def __init__(self):
    self._executables = { }

  def add(self, executable, path):
    if not os.path.exists(path):
      raise RuntimeError, 'path %s not found' % path
    self._executables[executable] = path

  def get(self, executable):
    return self._executables.get(executable)

Executables = _Executables()
