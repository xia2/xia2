#!/usr/bin/env python
# CCP4InterRadiationDamageDetector.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 15th January 2007
#
# A detector for radiation damage between wavelengths - in particular for
# detecting radiation damage and eliminating wavelengths at the end of
# the scaling process.
#
# Will be used in:
#
# CCP4 Scaler, XDS Scaler.
#
# Uses:
#
# Scaleit.py
#

import os
import sys
import math

from xia2.Wrappers.CCP4.Scaleit import Scaleit
from xia2.lib.bits import auto_logfiler

# Operation:
#
# This will work by comparing the relative scale and b factors between
# the data sets - presuming that they are input in a reasonable approximation
# of collection order - and decide when radiation damage has become a problem.
# Exactly what to do about this - that is the decision to be made by
# the calling routine.
#
# This will return a list of wavelengths which are "ok" and a list of ones
# which are "damaged".

class CCP4InterRadiationDamageDetector(object):
  '''A class to detect radiation damage.'''

  def __init__(self):
    self._working_directory = os.getcwd()
    self._hklin = None
    self._hklout = None
    self._anomalous = False

    return

  def set_hklin(self, hklin):
    self._hklin = hklin
    return

  def set_anomalous(self, anomalous):
    self._anomalous = anomalous
    return

  def get_hklin(self):
    return self._hklin

  def check_hklin(self):
    if self._hklin is None:
      raise RuntimeError, 'hklin not defined'
    if not os.path.exists(self._hklin):
      raise RuntimeError, 'hklin %s does not exist' % self._hklin

    return

  def set_hklout(self, hklout):
    self._hklout = hklout
    return

  def get_hklout(self):
    return self._hklout

  def check_hklout(self):
    if self._hklout is None:
      raise RuntimeError, 'hklout not defined'

    # check that these are different files!

    if self._hklout == self._hklin:
      raise RuntimeError, 'hklout and hklin are the same file'

    return

  def set_working_directory(self, working_directory):
    self._working_directory = working_directory
    pass

  def get_working_directory(self):
    return self._working_directory

  def detect(self):
    '''Detect radiation damage between wavelengths / datasets in a
    reflection file. Will assume that the input is in order of data
    collection. Will further assume that this is for MAD phasing.'''

    self.check_hklin()
    self.check_hklout()

    # check that hklin is an mtz file.

    scaleit = Scaleit()
    scaleit.set_working_directory(self.get_working_directory())
    auto_logfiler(scaleit)

    if self._anomalous:
      scaleit.set_anomalous(True)

    scaleit.set_hklin(self.get_hklin())
    scaleit.set_hklout(self.get_hklout())

    try:
      scaleit.scaleit()
    except RuntimeError, e:
      return ()

    statistics = scaleit.get_statistics()

    wavelengths = statistics['mapping']
    b_factors = statistics['b_factor']

    derivatives = wavelengths.keys()
    derivatives.sort()

    status = []

    for j in derivatives:
      name = b_factors[j]['dname']
      b = b_factors[j]['b']
      r = b_factors[j]['r']

      # this is arbitrary!

      if r > 0.50:
        misindexed = ', misindexed'
      else:
        misindexed = ''

      if b < -3:
        status.append((name, '%5.1f %4.2f (damaged%s)' % \
                       (b, r, misindexed)))
      else:
        status.append((name, '%5.1f %4.2f (ok%s)' % \
                       (b, r, misindexed)))

    return status

if __name__ == '__main__':

  c = CCP4InterRadiationDamageDetector()

  hklin = os.path.join(
      os.environ['X2TD_ROOT'],
      'Test', 'UnitTest', 'Wrappers', 'Scaleit',
      'TS03_INTER_RD.mtz')

  c.set_hklin(hklin)
  c.set_hklout('junk.mtz')

  status = c.detect()

  for s in status:
    print '%s %s' % s
