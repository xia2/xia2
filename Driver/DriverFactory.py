#!/usr/bin/env python
# DriverFactory.py
#
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 24th May 2006
#
# A factory for Driver implementations.
#
# At the moment this will instantiate
#
# SimpleDriver, ScriptDriver, QSubDriver, InteractiveDriver
#
# instances only.
#

import os

from SimpleDriver import SimpleDriver
from ScriptDriver import ScriptDriver
from QSubDriver import QSubDriver
from InteractiveDriver import InteractiveDriver

# another factory to delegate to
from ClusterDriverFactory import ClusterDriverFactory

class _DriverFactory(object):

  def __init__(self):

    self._driver_type = 'simple'

    self._implemented_types = ['simple', 'script', 'interactive',
                               'qsub', 'cluster.sge']

    # should probably write a message or something explaining
    # that the following Driver implementation is being used

    if os.environ.has_key('XIA2CORE_DRIVERTYPE'):
      self.set_driver_type(os.environ['XIA2CORE_DRIVERTYPE'])

    return

  def set_driver_type(self, type):
    '''Set the kind of driver this factory should produce.'''
    if not type in self._implemented_types:
      raise RuntimeError, 'unimplemented driver class: %s' % type

    self._driver_type = type

    return

  def get_driver_type(self):
    return self._driver_type

  def Driver(self, type = None):
    '''Create a new Driver instance, optionally providing the
    type of Driver we want.'''

    if not type:
      type = self._driver_type

    if 'cluster' in type:
      return ClusterDriverFactory.Driver(type)

    if type == 'simple':
      return SimpleDriver()

    if type == 'script':
      return ScriptDriver()

    if type == 'interactive':
      return InteractiveDriver()

    if type == 'qsub':
      return QSubDriver()

    raise RuntimeError, 'Driver class "%s" unknown' % type

DriverFactory = _DriverFactory()

if __name__ == '__main__':
  # then run a test

  d = DriverFactory.Driver()

  d = DriverFactory.Driver('nosuchtype')
