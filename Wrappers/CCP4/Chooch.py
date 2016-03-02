#!/usr/bin/env python
# Chooch.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# A wrapper for Chooch, for use in deciding what has happened during
# collection of experimental phasing data, and also for helping with
# MAD experiments.
#
# 18th December 2006
#
#

import os
import sys
import math
import string
import exceptions

if not os.environ.has_key('XIA2_ROOT'):
  raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
  sys.path.append(os.environ['XIA2_ROOT'])

from Driver.DriverFactory import DriverFactory

# helper functions

def energy_to_wavelength(energy):
  h = 6.6260693e-34
  c = 2.9979246e8
  e = 1.6021765e-19

  return 1.0e10 * (h * c) / (e * energy)

def preprocess_scan(scan_file):
  '''Preprocess the scan file to a form that chooch will accept.'''

  try:
    i = int(open(scan_file, 'r').readlines()[1])
    return scan_file
  except:
    # assume that this is not in the friendly format...
    data = open(scan_file, 'r').readlines()
    more_data = []
    for d in data:
      if not '#' in d and d.strip():
        more_data.append(d)
    data = more_data
    count = len(data)
    out = open('xia2-chooch.raw', 'w')
    out.write('Chooch Scan File from xia2\n%d\n' % count)
    for d in data:
      out.write('%f %f\n' % tuple(map(float, d.split(',')[:2])))
    out.close()
    return 'xia2-chooch.raw'

def Chooch(DriverType = None):
  '''Factory for Chooch wrapper classes, with the specified
  Driver type.'''

  DriverInstance = DriverFactory.Driver(DriverType)

  class ChoochWrapper(DriverInstance.__class__):
    def __init__(self):

      DriverInstance.__class__.__init__(self)

      self.set_executable('chooch')
      self._scan = None
      self._edge_table = { }

      self._atom = 'se'

      self._data = []

    def set_scan(self, scan):
      '''Set a scan file for chooch to parse.'''

      self._scan = preprocess_scan(scan)
      return

    def set_atom(self, atom):
      '''Set the atom which should be in the scan.'''

      self._atom = atom
      return

    def scan(self):
      '''Run chooch.'''

      self.add_command_line('-e')
      self.add_command_line(self._atom)
      self.add_command_line(self._scan)

      self.start()
      self.close_wait()

      self.check_for_errors()

      self._data = []
      for o in open(os.path.join(self.get_working_directory(),
                                 'output.efs'), 'r').readlines():
        self._data.append(map(float, o.split()))

      output = self.get_all_output()
      collect = False

      for o in output:
        if collect:

          if '-------' in o:
            collect = False
            continue

          name, energy, fp, fpp = tuple(map(string.strip,
                                            o.split('|')[1:5]))
          self._edge_table[name] = {
              'energy':float(energy),
              'fp':float(fp),
              'fpp':float(fpp),
              'wave':energy_to_wavelength(float(energy))}

        if 'energy' in o and 'f\'' in o and 'f\'\'' in o:
          collect = True

    def get_edges(self):
      return self._edge_table

    def get_fp_fpp(self, wave):
      '''Get the fp, fpp for a wavelength.'''

      if not self._data:
        raise RuntimeError, 'data array empty'

      fp = 0.0
      fpp = 0.0
      closest = 1.0e100

      for d in self._data:
        w = energy_to_wavelength(d[0])
        if math.fabs(w - wave) < closest:
          fp = d[2]
          fpp = d[1]
          closest = math.fabs(w - wave)

      return fp, fpp

    def id_wavelength(self, wave):
      '''Try to identify a wavelength.'''

      min_wave_diff = 1.0e100
      name = None

      waves = []

      for edge in self._edge_table.keys():
        waves.append(self._edge_table[edge]['wave'])
        if math.fabs(self._edge_table[edge]['wave'] - wave) < \
           min_wave_diff:
          min_wave_diff = math.fabs(self._edge_table[edge]['wave'] -
                                    wave)
          name = edge

      if min_wave_diff > 0.01:
        # assume that this is a remote...
        if wave > max(waves):
          return 'LREM'
        else:
          return 'HREM'

      return name.upper()

  return ChoochWrapper()

if __name__ == '__main__':

  if len(sys.argv) < 2:

    c = Chooch()
    c.set_scan(os.path.join(os.environ['XIA2_ROOT'], 'Data',
                            'Test', 'Scans',
                            'TM0486-9172-Se.raw'))
    c.set_atom('se')
    c.scan()

    edges = c.get_edges()

    for key in edges.keys():
      print '%s %6.2f %6.2f %8.6f' % (key,
                                      edges[key]['fp'],
                                      edges[key]['fpp'],
                                      edges[key]['wave'])

  else:
    for scan in sys.argv[1:]:

      print os.path.split(scan)[-1]

      try:

        c = Chooch()
        c.set_scan(scan)
        c.set_atom('se')
        c.scan()

        edges = c.get_edges()

        for key in edges.keys():
          print '%s %6.2f %6.2f %8.6f' % (key,
                                          edges[key]['fp'],
                                          edges[key]['fpp'],
                                          edges[key]['wave'])
      except exceptions.Exception, e:
        print 'failed (%s)' % str(e)


      print ''
