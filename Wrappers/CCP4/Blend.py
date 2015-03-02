#!/usr/bin/env python
# Sortmtz.py
#   Copyright (C) 2014 Diamond Light Source, Richard Gildea
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# A wrapper for the CCP4 program Blend.

import os
import sys

if not os.environ.has_key('XIA2CORE_ROOT'):
  raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
  sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                               'Python'))

if not os.environ['XIA2_ROOT'] in sys.path:
  sys.path.append(os.environ['XIA2_ROOT'])

from Driver.DriverFactory import DriverFactory
from Decorators.DecoratorFactory import DecoratorFactory
from Handlers.Streams import Chatter

def Blend(DriverType = None):
  '''A factory for BlendWrapper classes.'''

  DriverInstance = DriverFactory.Driver(DriverType)

  class BlendWrapper(DriverInstance.__class__):
    '''A wrapper for Blend.'''

    def __init__(self):
      # generic things
      super(BlendWrapper, self).__init__()

      self.set_executable(os.path.join(
          os.environ.get('CBIN', ''), 'blend'))

      self._hklin_files = []

      return

    def add_hklin(self, hklin):
      '''Add a reflection file to the list to be sorted together.'''
      self._hklin_files.append(hklin)
      return

    def analysis(self):
      '''Run blend in analysis mode.'''

      assert len(self._hklin_files) > 1, "BLEND requires more than one reflection file"

      input_files_dat = os.path.join(
        self.get_working_directory(), 'input_files.dat')
      with open(input_files_dat, 'wb') as f:
        for hklin in self._hklin_files:
          print >> f, hklin

      self.add_command_line('-a')
      self.add_command_line(input_files_dat)

      self.start()

      self.close_wait()

      # general errors - SEGV and the like
      self.check_for_errors()

      self._clusters_file = 'CLUSTERS.txt'
      assert os.path.isfile(self._clusters_file)

      self._summary_file = 'BLEND_SUMMARY.txt'
      assert os.path.isfile(self._summary_file)

      self._analysis_file = 'FINAL_list_of_files.dat'
      assert os.path.isfile(self._analysis_file)

      self._summary = parse_summary_file(self._summary_file)
      self._clusters = parse_clusters_file(self._clusters_file)
      self._analysis = parse_final_list_of_files_dat(self._analysis_file)

    def get_clusters_file(self):
      return self._clusters_file

    def get_summary_file(self):
      return self._summary_file

    def get_analysis_file(self):
      return self._analysis_file

    def get_summary(self):
      return self._summary

    def get_clusters(self):
      return self._clusters

    def get_analysis(self):
      return self._analysis

  return BlendWrapper()


def parse_summary_file(summary_file):
  with open(summary_file, 'rb') as f:
    lines = f.readlines()

  summary = {}
  for line in lines:
    row = line.strip().strip('|').split('|')
    row = [s.strip() for s in row]
    if len(row) != 7:
      continue

    try:
      crystal_id = int(row[0])
    except ValueError, e:
      continue

    cell = tuple(float(s) for s in row[1].split())
    assert len(cell) == 6
    volume = float(row[2].strip())
    mosaicity = float(row[3].strip())
    d_max, d_min = (float(s) for s in row[4].split())
    distance = float(row[5].strip())
    wavelength = float(row[6].strip())

    summary[crystal_id] = {
      'cell': cell,
      'volume': volume,
      'mosaicity': mosaicity,
      'd_max': d_max,
      'd_min': d_min,
      'distance': distance,
      'wavelength': wavelength,
    }

  return summary

def parse_clusters_file(clusters_file):
  with open(clusters_file, 'rb') as f:
    lines = f.readlines()

  clusters = {}
  for line in lines:
    row = line.split()
    if len(row) < 6:
      continue

    try:
      cluster_id = int(row[0])
    except ValueError, e:
      continue

    n_datasets = int(row[1])
    height = float(row[2])
    lcv = float(row[3])
    alcv = float(row[4])
    dataset_ids = [int(s) for s in row[5:]]

    clusters[cluster_id] = {
      'n_datasets': n_datasets,
      'height': height,
      'lcv': lcv,
      'alcv': alcv,
      'dataset_ids': dataset_ids
    }

  return clusters

def parse_final_list_of_files_dat(filename):
  # The "FINAL_list_of_files.dat" file has 6 columns. The first
  # is the path to the input files, the second is the serial number assigned
  # from BLEND (and used in cluster analysis), the fourth and fifth are
  # initial and final input image numbers, the third is the image number after
  # which data are discarded because weakened by radiation damage, the sixth
  # is resolution cutoff.

  with open(filename, 'rb') as f:
    lines = f.readlines()

  result = {}
  for line in lines:
    row = line.split()
    if len(row) != 6:
      continue

    input_file = row[0]
    serial_no = int(row[1])
    rad_dam_cutoff = int(row[2])
    start_image = int(row[3])
    final_image = int(row[4])
    d_min = float(row[5])

    result[serial_no] = {
      'input_file': input_file,
      'radiation_damage_cutoff': rad_dam_cutoff,
      'start_image': start_image,
      'final_image': final_image,
      'd_min': d_min
    }

  return result


if __name__ == '__main__':
  b = Blend()
  for arg in sys.argv[1:]:
    b.add_hklin(arg)
  b.analysis()
  print "".join(b.get_all_output())
  print b.get_analysis()
  print b.get_summary()
  print b.get_clusters()
