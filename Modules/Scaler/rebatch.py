#!/usr/bin/env python
# rebatch.py
#
#   Copyright (C) 2011 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Replacement for CCP4 program rebatch, using cctbx Python.
#

import sys

from iotbx import mtz
from cctbx.array_family import flex

def rebatch(hklin, hklout, first_batch):
    '''Need to implement: include batch range, exclude batches, add N to
    batches, start batches at N.'''

    mtz_obj = mtz.object(file_name = hklin)

    batch_column = None
    batch_dataset = None

    for crystal in mtz_obj.crystals():
        for dataset in crystal.datasets():
            for column in dataset.columns():
                if column.label() == 'BATCH':
                    batch_column = column
                    batch_dataset = dataset

    if not batch_column:
        raise RuntimeError, 'no BATCH column found in %s' % hklin

    batch_column_values = batch_column.extract_values(
        not_a_number_substitute = -1)

    valid = flex.bool()

    # modify batch columns, and also the batch headers

    if first_batch != None:
        offset = first_batch - min(batch_column_values)
        batch_column_values = batch_column_values + offset

        for batch in mtz_obj.batches():
            batch.set_num(int(batch.num() + offset))

    # done modifying

    batch_column.set_values(values = batch_column_values,
                            selection_valid = valid)

    # and write this lot out as hklout

    mtz_obj.write(file_name = hklout)

def copy_r_file(hklin, hklout):

    mtz_obj = mtz.object(file_name = hklin)

    mtz_out = mtz.object()

    mtz_out.set_space_group(mtz_obj.space_group())

    for batch in mtz_obj.batches():
        if batch.num() % 2 == 0:
            batch_out = mtz_out.add_batch()
            batch_out.set_num(batch.num())
            batch_out.set_title(batch.title())
            batch_out.set_gonlab(batch.gonlab())
            batch_out.set_ndet(batch.ndet())
            batch_out.set_phixyz(batch.phixyz())
            batch_out.set_detlm(batch.detlm())

    batch_column = None

    for crystal in mtz_obj.crystals():

        crystal_out = mtz_out.add_crystal(
            crystal.name(), crystal.project_name(), crystal.unit_cell())

        for dataset in crystal.datasets():

            dataset_out = crystal_out.add_dataset(dataset.name(),
                                                  dataset.wavelength())

            for column in dataset.columns():

                dataset_out.add_column(column.label(), column.type())

                if column.label() == 'BATCH':
                    batch_column = column

    if not batch_column:
        raise RuntimeError, 'no BATCH column found in %s' % hklin

    batch_column_values = batch_column.extract_values(
        not_a_number_substitute = -1)

    valid = flex.bool()

    remove = []

    for j, b in enumerate(batch_column_values):
        if b % 2 != 0:
            remove.append(j)

    remove.reverse()

    for crystal in mtz_obj.crystals():
        for dataset in crystal.datasets():
            for column in dataset.columns():
                print column.label()
                values = column.extract_values(
                    not_a_number_substitute = -999999)
                for r in remove:
                    del(values[r])
                mtz_out.get_column(column.label()).set_values(
                    values = values, selection_valid = valid)

    mtz_out.write(file_name = hklout)

    return

if __name__ == '__main__':

    import sys

    hklin = sys.argv[1]
    hklout = 'arse.mtz'

    copy_r_file(hklin, hklout)
