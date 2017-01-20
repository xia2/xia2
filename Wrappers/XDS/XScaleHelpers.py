#!/usr/bin/env python
# XScaleHelpers.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Helpers for the wrapper for XSCALE, the XDS Scaling program.
#

from __future__ import absolute_import, division

import math
import sys

def _generate_resolution_shells(low, high):
  '''Generate 9 evenly spaced in reciprocal space resolution
  shells from low to high resolution, e.g. in 1/d^2.'''

  dmin = (1.0 / high) * (1.0 / high)
  dmax = (1.0 / low) * (1.0 / low)
  diff = (dmin -  dmax) / 8.0

  shells = [1.0 / math.sqrt(dmax)]

  for j in range(8):
    shells.append(1.0 / math.sqrt(dmax + diff * (j + 1)))

  return shells

def generate_resolution_shells_str(low, high):
  '''Generate a string of 8 evenly spaced in reciprocal space resolution
  shells from low to high resolution, e.g. in 1/d^2.'''

  result = ''
  shells = _generate_resolution_shells(low, high)

  for s in shells:
    result += ' %.2f' % s

  return result

def get_correlation_coefficients_and_group(xscale_lp):
  '''Get and group correlation coefficients between data sets from the
  xscale log file. Also access the reflection file names to show which ones
  should be scaled together.'''

  ccs = { }

  file_names = { }

  xmax = 0

  records = open(xscale_lp).readlines()

  # first scan through to get the file names...

  for j, record in enumerate(records):
    if 'NUMBER OF UNIQUE REFLECTIONS' in record:

      k = j + 5

      while len(records[k].split()) == 5:
        values = records[k].split()
        file_names[int(values[0])] = values[-1]

        k += 1

      break

  if not file_names:
    for j, record in enumerate(records):
      if 'SET# INTENSITY  ACCEPTED REJECTED' in record:

        k = j + 1

        while len(records[k].split()) == 5:
          values = records[k].split()
          file_names[int(values[0])] = values[-1]

          k += 1

        break


  for j, record in enumerate(records):

    if 'CORRELATIONS BETWEEN INPUT DATA SETS' in record:

      k = j + 5

      while len(records[k].split()) == 6:
        values = records[k].split()

        _i = int(values[0])
        _j = int(values[1])
        _n = int(values[2])
        _cc = float(values[3])

        ccs[(_i, _j)] = (_n, _cc)
        ccs[(_j, _i)] = (_n, _cc)

        xmax = _i + 1

        k += 1

      break

  used = []
  groups = { }

  for j in range(xmax):
    test_file = file_names[j + 1]
    if test_file in used:
      continue
    used.append(test_file)
    groups[test_file] = [test_file]
    for k in range(j + 1, xmax):
      if ccs[(j + 1, k + 1)][1] > 0.9:
        groups[test_file].append(file_names[k + 1])
        used.append(file_names[k + 1])

  return groups

if __name__ == '__main__':
  get_correlation_coefficients_and_group(sys.argv[1])
