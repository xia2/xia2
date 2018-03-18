#!/usr/bin/env python
# PyChefHelpers.py
#
#   Copyright (C) 2009 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Functions to help with the implementation of PyChef - little jiffy
# bits which don't really need to be embedded in the main program.
#

from __future__ import absolute_import, division

import sys

from cctbx.crystal import symmetry as crystal_symmetry
from cctbx.miller import build_set
from iotbx.mtz import object as mtz_factory

def get_mtz_column_list(hklin):

  mtz_obj = mtz_factory(file_name=hklin)

  # construct a list of columns in the file

  cnames = []

  batch_column = None
  batch_dataset = None

  for crystal in mtz_obj.crystals():
    for dataset in crystal.datasets():
      for column in dataset.columns():
        cnames.append(column.label())

  return cnames

def compute_unique_reflections(unit_cell, space_group, anomalous,
                               high_resolution_limit,
                               low_resolution_limit=None):
  '''Compute the list of unique reflections from the unit cell and space
  group.'''

  cs = crystal_symmetry(unit_cell=unit_cell, space_group=space_group)

  return [
      hkl for hkl in build_set(cs, anomalous, d_min=high_resolution_limit,
                               d_max=low_resolution_limit).indices()
  ]

if __name__ == '__main__':

  for hklin in sys.argv[1:]:

    mtz_obj = mtz_factory(file_name=hklin)
    sg = mtz_obj.space_group().build_derived_patterson_group()

    for crystal in mtz_obj.crystals():
      uc = crystal.unit_cell()

      for dataset in crystal.datasets():

        print crystal.name(), dataset.name()

    dmax, dmin = mtz_obj.max_min_resolution()

    print len(compute_unique_reflections(uc, sg, True, dmin, dmax))

    ms = set()

    miller_indices = mtz_obj.extract_miller_indices()

    for hkl in miller_indices:
      ms.add(hkl)

    print len(ms)
