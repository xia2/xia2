# Mtz2Scalepack.py
# Maintained by G.Winter
# 12th February 2007
#
# A module to convert a reflection file in MTZ format into a number of
# scalepack files containing the I's - one per wavelength / dataset defined
# in the input file, with names derived in the same way as for the
# CCP4ScalerImplementation (e.g. PNAME_XNAME_scaled_DNAME.sca)
#

import os
import sys
import math

from xia2.Wrappers.CCP4.Mtzdump import Mtzdump as _Mtzdump
from xia2.Wrappers.CCP4.Mtz2various import Mtz2various as _Mtz2various

class Mtz2Scalepack(object):
  '''A jiffy class to convert an MTZ file to scalepack merged format,
  for all pname, xname, dname found in the file.'''

  def __init__(self):
    self._hklin = None
    self._working_directory = os.getcwd()
    self._hklout = { }

    return

  def set_working_directory(self, working_directory):
    self._working_directory = working_directory
    return

  def get_working_directory(self):
    return self._working_directory

  def set_hklin(self, hklin):
    self._hklin = hklin
    return

  # factory methods

  def Mtzdump(self):
    m = _Mtzdump()
    m.set_working_directory(self.get_working_directory())
    return m

  def Mtz2various(self):
    m = _Mtz2various()
    m.set_working_directory(self.get_working_directory())
    return m

  def convert(self):
    if not self._hklin:
      raise RuntimeError, 'HKLIN not defined'

    # run mtzdump to get a list of the projects etc from the
    # reflection file

    m = self.Mtzdump()

    m.set_hklin(self._hklin)
    m.dump()

    datasets = m.get_datasets()

    # then for each combination run mtz2various to convert it
    # to scalepack format

    for d in datasets:
      pname, xname, dname = tuple(d.split('/'))

      # this will look for I(+) etc columns.
      # possible problem warning - what happens if
      # this is given a reflection file
      #
      # (1) without I's only F's?
      # (2) not separated anomalous pairs???

      m2 = self.Mtz2various()
      m2.set_hklin(self._hklin)
      m2.set_hklout(os.path.join(
          self._working_directory,
          '%s_%s_scaled_%s.sca' % \
          (pname, xname, dname)))
      m2.set_suffix(dname)
      m2.convert()

      # record this for external access
      self._hklout[dname] = m2.get_hklout()

    return self._hklout

if __name__ == '__main__':
  # then run a test...

  hklin = os.path.join(os.environ['X2TD_ROOT'],
                       'Test', 'UnitTest', 'Interfaces',
                       'Scaler', 'Merged', 'TS00_13185_merged_free.mtz')


  m2s = Mtz2Scalepack()
  m2s.set_hklin(hklin)
  print m2s.convert()
