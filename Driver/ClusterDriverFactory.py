#!/usr/bin/env python
# ClusterDriverFactory.py
#
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 19th June 2006
#
# A DriverFactory for cluster-specific driver instances.
# At the moment this supports the following machines:
#
# Linux/Sun Grid Engine
#
#

from __future__ import absolute_import, division

import os

from xia2.Driver.SunGridEngineClusterDriver import SunGridEngineClusterDriver

class _ClusterDriverFactory(object):
  def __init__(self):

    self._driver_type = 'cluster.sge'

    self._implemented_types = ['cluster.sge']

    # should probably write a message or something explaining
    # that the following Driver implementation is being used

    if 'XIA2CORE_DRIVERTYPE' in os.environ:
      if 'cluster' in os.environ['XIA2CORE_DRIVERTYPE']:
        self.setDriver_type(os.environ['XIA2CORE_DRIVERTYPE'])

    return

  def set_driver_type(self, type):
    return self.setDriver_type(type)

  def setDriver_type(self, type):
    '''Set the kind of driver this factory should produce.'''

    if not type in self._implemented_types:
      raise RuntimeError('unimplemented driver class: %s' % type)

    self._driver_type = type

    return

  def Driver(self, type=None):
    '''Create a new Driver instance, optionally providing the
    type of Driver we want.'''

    if not type:
      type = self._driver_type

    if type == 'cluster.sge':
      return SunGridEngineClusterDriver()

    raise RuntimeError('Driver class "%s" unknown' % type)

ClusterDriverFactory = _ClusterDriverFactory()

if __name__ == '__main__':
  # then run a test

  d = ClusterDriverFactory.Driver()

  d = ClusterDriverFactory.Driver('nosuchtype')
