#!/usr/bin/env cctbx.python
# MtzFactory.py
#
#   Copyright (C) 2010 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# A toolkit component to read MTZ format reflection files, wrapping the
# functionality in iotbx. This will return a data structure to represent
# merged and unmerged MTZ files.

from __future__ import absolute_import, division

import sys

from iotbx import mtz

class mtz_dataset(object):
  '''A class to represent the MTZ dataset in the hierarchy. This will
  be instantiated in the mtz_crystal class below, and contain:

   - a list of columns

  Maybe more things will be added.'''

  def __init__(self, iotbx_dataset):
    self._name = iotbx_dataset.name()
    self._column_table = { }
    for column in iotbx_dataset.columns():
      self._column_table[column.label()] = column

    return

  def get_column_names(self):
    return list(self._column_table)

  def get_column(self, column_label):
    return self._column_table[column_label]

  def get_column_values(self, column_label, nan_value = 0.0):
    return self._column_table[column_label].extract_values(
        not_a_number_substitute = nan_value)

class mtz_crystal(object):
  '''A class to represent the MTZ crystal in the hierarchy. This will
  be instantiated by the factories below.'''

  def __init__(self, iotbx_crystal):
    self._name = iotbx_crystal.name()
    self._unit_cell = iotbx_crystal.unit_cell()

    self._dataset_table = { }
    for dataset in iotbx_crystal.datasets():
      self._dataset_table[dataset.name()] = mtz_dataset(dataset)

    self._column_table = { }

    for dname in self._dataset_table:
      dataset = self._dataset_table[dname]
      for column_name in dataset.get_column_names():
        assert(not column_name in self._column_table)
        self._column_table[column_name] = dataset.get_column(
            column_name)

    return

  def get_dataset_names(self):
    return list(self._dataset_table)

  def get_dataset(self, dataset_name):
    return self._dataset_table[dataset_name]

  def get_unit_cell_parameters(self):
    return tuple(self._unit_cell.parameters())

  def get_unit_cell(self):
    return self._unit_cell

  def get_column_names(self):
    return list(self._column_table)

  def get_column(self, column_label):
    return self._column_table[column_label]

  def get_column_values(self, column_label, nan_value = 0.0):
    return self._column_table[column_label].extract_values(
        not_a_number_substitute = nan_value)

class mtz_file(object):
  '''A class to represent the full MTZ file in the hierarchy - this
  will have a list of one or more crystals contained within it each
  with its own unit cell and datasets.'''

  # FIXME need to keep in mind MTZ batch headers - can I access these?
  # yes - through stuff like this:
  #
  #    for batch in mtz_obj.batches():
  #        for token in dir(batch):
  #            print token
  #        print batch.num()
  #
  # but need to decide what I am looking for... will bake this in with
  # a future update (it would be interesting to look at how the UB
  # matrices behave.)

  def __init__(self, hklin):
    mtz_obj = mtz.object(hklin)

    self._miller_indices = mtz_obj.extract_miller_indices()
    self._resolution_range = mtz_obj.max_min_resolution()
    self._space_group = mtz_obj.space_group()

    self._crystal_table = { }

    for crystal in mtz_obj.crystals():
      self._crystal_table[crystal.name()] = mtz_crystal(crystal)

    self._column_table = { }

    for xname in self._crystal_table:
      crystal = self._crystal_table[xname]
      for dname in crystal.get_dataset_names():
        dataset = crystal.get_dataset(dname)
        for column_name in dataset.get_column_names():
          assert(not column_name in self._column_table)
          self._column_table[column_name] = dataset.get_column(
              column_name)

    return

  def get_crystal_names(self):
    return list(self._crystal_table)

  def get_crystal(self, crystal_name):
    return self._crystal_table[crystal_name]

  def get_unit_cell(self):
    '''Get the unit cell object from HKL_base for other calculations.'''

    return self.get_crystal('HKL_base').get_unit_cell()

  def get_space_group(self):
    return self._space_group

  def get_resolution_range(self):
    return self._resolution_range

  def get_symmetry_operations(self):
    return [smx for smx in self._space_group.smx()]

  def get_centring_operations(self):
    return [ltr for ltr in self._space_group.ltr()]

  def get_miller_indices(self):
    return self._miller_indices

  def get_column_names(self):
    return list(self._column_table)

  def get_column(self, column_label):
    return self._column_table[column_label]

  def get_column_values(self, column_label, nan_value = 0.0):
    return self._column_table[column_label].extract_values(
        not_a_number_substitute = nan_value)

def mtz_dump(hklin):
  '''An implementation of mtzdump using the above classes.'''

  mtz = mtz_file(hklin)

  print 'Reading file: %s' % hklin
  print 'Spacegroup: %s' % mtz.get_space_group().type(
       ).universal_hermann_mauguin_symbol()

  print 'Centring operations:'
  for cenop in mtz.get_centring_operations():
    print cenop

  print 'Symmetry operations:'
  for symop in mtz.get_symmetry_operations():
    print symop

  for xname in mtz.get_crystal_names():
    crystal = mtz.get_crystal(xname)
    print 'Crystal: %s' % xname
    print 'Cell: %.3f %.3f %.3f %.3f %.3f %.3f' % \
          crystal.get_unit_cell_parameters()

    for dname in crystal.get_dataset_names():
      dataset = crystal.get_dataset(dname)
      print 'Dataset: %s' % dname
      print 'Columns (with min / max)'
      for column in dataset.get_column_names():
        values = dataset.get_column_values(column)
        print '%20s %.4e %.4e' % (column, min(values), max(values))

  print 'All columns:'
  for column in mtz.get_column_names():
    print column

if __name__ == '__main__':
  mtz_dump(sys.argv[1])
