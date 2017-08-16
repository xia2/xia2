#!/usr/bin/env python
# Mtzdump.py
#   Copyright (C) 2013 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# A replacement for the wrapper for the CCP4 program MTZDUMP using CCTBX
# to access the file directly.

from __future__ import absolute_import, division

import os
import sys
import copy
from iotbx import mtz

class Mtzdump(object):
  '''A class to give the same functionality as the wrapper for the CCP4
  MTZDUMP program.'''

  def __init__(self):
    self._header = { }
    self._header['datasets'] = []
    self._header['dataset_info'] = { }

    self._batch_header = { }

    self._batches = None
    self._reflections = 0
    self._resolution_range = (0, 0)

    return

  def set_working_directory(self, wd):
    pass

  def get_working_directory(self):
    return None

  def set_hklin(self, hklin):
    self._hklin = hklin
    return

  def dump(self):
    '''Actually obtain the contents of the mtz file header.'''

    assert self._hklin, self._hklin
    assert os.path.exists(self._hklin), self._hklin

    mtz_obj = mtz.object(self._hklin)

    # work through the file acculumating the necessary information

    self._header['datasets'] = []
    self._header['dataset_info'] = { }

    self._batches = [batch.num() for batch in mtz_obj.batches()]
    self._header['column_labels'] = [column.label() for column
                                     in mtz_obj.columns()]
    self._header['column_types'] = [column.type() for column
                                    in mtz_obj.columns()]
    self._resolution_range = mtz_obj.max_min_resolution()

    self._header['spacegroup'] = mtz_obj.space_group_name()
    self._reflections = mtz_obj.n_reflections()

    for crystal in mtz_obj.crystals():
      if crystal.name() == 'HKL_base':
        continue

      pname = crystal.project_name()
      xname = crystal.name()
      cell = crystal.unit_cell().parameters()

      for dataset in crystal.datasets():
        dname = dataset.name()
        wavelength = dataset.wavelength()
        dataset_id = '%s/%s/%s' % (pname, xname, dname)
        dataset_number = dataset.i_dataset()

        assert(not dataset_id in self._header['datasets'])

        self._header['datasets'].append(dataset_id)
        self._header['dataset_info'][dataset_id] = { }
        self._header['dataset_info'][
            dataset_id]['wavelength'] = wavelength
        self._header['dataset_info'][
            dataset_id]['cell'] = cell
        self._header['dataset_info'][
            dataset_id]['id'] = dataset_number

    return

  def dump_batch_headers(self):
    '''Actually print the contents of the mtz file batch headers.'''

    assert self._hklin, self._hklin
    assert os.path.exists(self._hklin), self._hklin

    mtz_obj = mtz.object(self._hklin)

    for batch in mtz_obj.batches():
      current_batch = batch.num()
      umat = batch.umat()

      self._batch_header[current_batch] = {'umat': umat}

    return

  def get_batch_header(self, batch):
    return copy.deepcopy(self._batch_header[batch])

  def get_columns(self):
    '''Get a list of the columns and their types as tuples
    (label, type) in a list.'''

    results = []
    for i in range(len(self._header['column_labels'])):
      results.append((self._header['column_labels'][i],
                      self._header['column_types'][i]))
    return results

  def get_resolution_range(self):
    return self._resolution_range

  def get_datasets(self):
    '''Return a list of available datasets.'''
    return self._header['datasets']

  def get_dataset_info(self, dataset):
    '''Get the cell, spacegroup & wavelength associated with
    a dataset. The dataset is specified by pname/xname/dname.'''

    result = copy.deepcopy(self._header['dataset_info'][dataset])
    result['spacegroup'] = self._header['spacegroup']
    return result

  def get_spacegroup(self):
    '''Get the spacegroup recorded for this reflection file.'''
    return self._header['spacegroup']

  def get_batches(self):
    '''Get a list of batches found in this reflection file.'''
    return self._batches

  def get_column_range(self, column):
    '''Get the value ranges for this column. This now works by reading
    the file rather than using cached values => could be slow.'''

    assert self._hklin, self._hklin
    assert os.path.exists(self._hklin), self._hklin

    mtz_obj = mtz.object(self._hklin)
    col = mtz_obj.get_column(column)
    valid = col.extract_valid_values()

    return min(valid), max(valid)

  def get_reflections(self):
    '''Return the number of reflections found in the reflection
    file.'''

    return self._reflections

if __name__ == '__main__':
  m = Mtzdump()

  if len(sys.argv) > 1:
    m.set_hklin(sys.argv[1])
  else:
    raise RuntimeError, '%s hklin.mtz' % sys.argv[0]

  m.dump()
  print m.get_spacegroup()
