#!/usr/bin/env python
# XDSIdxrefHelpers.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Routines which help with working with XDS IDXREF - e.g. parsing the
# output IDXREF.LP.
#

import math
import os
import sys

from xia2.Experts.LatticeExpert import ApplyLattice

def _parse_idxref_lp_distance_etc(lp_file_lines):
  '''Parse the LP file for refined distance, beam centre and so on...'''

  beam = None
  diatance = None

  i = 0
  while i < len(lp_file_lines):
    line = lp_file_lines[i]
    i += 1

    if 'DETECTOR COORDINATES' in line and 'DIRECT BEAM' in line:
      beam = tuple(map(float, line.split()[-2:]))
    if 'CRYSTAL TO DETECTOR' in line:
      distance = float(line.split()[-1])
      if distance < 0:
        distance *= -1

  return beam, distance

def _parse_idxref_index_origin(lp_file_lines):
  '''Parse the LP file for the possible index origin etc.'''

  origins = { }

  i = 0
  while i < len(lp_file_lines):
    line = lp_file_lines[i]
    i += 1
    if 'INDEX_' in line and 'QUALITY' in line and 'DELTA' in line:
      while not 'SELECTED' in line:
        line = lp_file_lines[i]
        i += 1
        try:
          hkl = tuple(map(int, line.split()[:3]))
          quality, delta, xd, yd = tuple(
              map(float, line.split()[3:7]))
          origins[hkl] = quality, delta, xd, yd
        except:
          pass

      return origins


  raise RuntimeError, 'should never reach this point'

def _parse_idxref_lp(lp_file_lines):
  '''Parse the list of lines from idxref.lp.'''

  lattice_character_info = {}

  i = 0

  mosaic = 0.0

  while i < len(lp_file_lines):
    line = lp_file_lines[i]
    i += 1

    # get the mosaic information

    if 'CRYSTAL MOSAICITY' in line:
      mosaic = float(line.split()[-1])

    # get the lattice character information - coding around the
    # non-standard possibility of mI, by simply ignoring it!
    # bug # 2355

    if 'CHARACTER  LATTICE     OF FIT      a      b      c' in line:
      j = i + 1
      while lp_file_lines[j].strip() != "":
        record = lp_file_lines[j].replace('*', ' ').split()
        character = int(record[0])
        lattice = record[1]

        # FIXME need to do something properly about this...
        # bug # 2355

        if lattice == 'mI':
          j += 1
          continue

        fit = float(record[2])
        cell = tuple(map(float, record[3:9]))
        reindex_card = tuple(map(int, record[9:]))
        constrained_cell = ApplyLattice(lattice, cell)[0]

        lattice_character_info[character] = {
            'lattice':lattice,
            'fit':fit,
            'cell':constrained_cell,
            'mosaic':mosaic,
            'reidx':reindex_card}

        j += 1


  return lattice_character_info

def _parse_idxref_lp_subtree(lp_file_lines):

  subtrees = { }

  i = 0

  while i < len(lp_file_lines):
    line = lp_file_lines[i]
    i += 1

    if line.split() == ['SUBTREE', 'POPULATION']:
      j = i + 1
      line = lp_file_lines[j]
      while line.strip():
        subtree, population = tuple(map(int, line.split()))
        subtrees[subtree] = population
        j += 1
        line = lp_file_lines[j]

  return subtrees

def _parse_idxref_lp_quality(lp_file_lines):
  fraction = None
  rmsd = None
  rmsphi = None

  for record in lp_file_lines:
    if 'OUT OF' in record and 'SPOTS INDEXED' in record:
      fraction = float(record.split()[0]) / float(record.split()[3])
    if 'STANDARD DEVIATION OF SPOT    POSITION' in record:
      rmsd = float(record.split()[-1])
    if 'STANDARD DEVIATION OF SPINDLE POSITION' in record:
      rmsphi = float(record.split()[-1])

  return fraction, rmsd, rmsphi

if __name__ == '__main__':

  fraction, rmsd, rmsphi = _parse_idxref_lp_quality(
      open(sys.argv[1], 'r').readlines())

  print '%.2f %.2f %.2f' % (fraction, rmsd, rmsphi)
