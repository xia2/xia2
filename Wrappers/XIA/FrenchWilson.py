#!/usr/bin/env python
# FrenchWilson.py
#   Copyright (C) 2015 Diamond Light Source, Richard Gildea
from __future__ import absolute_import, division, print_function

import os
import sys

from xia2.Driver.DriverFactory import DriverFactory

def FrenchWilson(DriverType = None):
  '''A factory for FrenchWilsonWrapper classes.'''

  DriverInstance = DriverFactory.Driver(DriverType)

  class FrenchWilsonWrapper(DriverInstance.__class__):
    '''A wrapper for cctbx French and Wilson analysis.'''

    def __init__(self):
      DriverInstance.__class__.__init__(self)

      self.set_executable('cctbx.python')

      self._anomalous = False
      self._nres = 0

      # should we do wilson scaling?
      self._wilson = True

      self._b_factor = 0.0
      self._moments = None

      self._wilson_fit_grad = 0.0
      self._wilson_fit_grad_sd = 0.0
      self._wilson_fit_m = 0.0
      self._wilson_fit_m_sd = 0.0
      self._wilson_fit_range = None

      # numbers of reflections in and out, and number of absences
      # counted

      self._nref_in = 0
      self._nref_out = 0
      self._nabsent = 0
      self._xmlout = None

    def set_anomalous(self, anomalous):
      self._anomalous = anomalous

    def set_wilson(self, wilson):
      '''Set the use of Wilson scaling - if you set this to False
      Wilson scaling will be switched off...'''
      self._wilson = wilson

    def set_hklin(self, hklin):
      self._hklin = hklin

    def get_hklin(self):
      return self._hklin

    def set_hklout(self, hklout):
      self._hklout = hklout

    def get_hklout(self):
      return self._hklout

    def check_hklout(self):
      return self.checkHklout()

    def get_xmlout(self):
      return self._xmlout

    def truncate(self):
      '''Actually perform the truncation procedure.'''

      from xia2.Modules import CctbxFrenchWilson as fw_module
      self.add_command_line(fw_module.__file__)

      self.add_command_line(self._hklin)
      self.add_command_line('hklout=%s' %self._hklout)

      if self._anomalous:
        self.add_command_line('anomalous=true')
      else:
        self.add_command_line('anomalous=false')

      self.start()
      self.close_wait()

      try:
        self.check_for_errors()

      except RuntimeError:
        try:
          os.remove(self.get_hklout())
        except Exception:
          pass

        raise RuntimeError('truncate failure')

      lines = self.get_all_output()
      for i, line in enumerate(lines):
        if 'ML estimate of overall B value:' in line:
          self._b_factor = float(lines[i+1].strip().split()[0])

    def get_b_factor(self):
      return self._b_factor

    def get_wilson_fit(self):
      return self._wilson_fit_grad, self._wilson_fit_grad_sd, \
             self._wilson_fit_m, self._wilson_fit_m_sd

    def get_wilson_fit_range(self):
      return self._wilson_fit_range

    def get_moments(self):
      return self._moments

    def get_nref_in(self):
      return self._nref_in

    def get_nref_out(self):
      return self._nref_out

    def get_nabsent(self):
      return self._nabsent

  return FrenchWilsonWrapper()

if __name__ == '__main__':

  fw = FrenchWilson()
  fw.set_hklin(sys.argv[1])
  fw.set_hklout(sys.argv[2])
  fw.truncate()

  print(fw.get_nref_in(), fw.get_nref_out(), \
        fw.get_nabsent())
