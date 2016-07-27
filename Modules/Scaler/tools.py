#!/usr/bin/env python
#
#   Copyright (C) 2009 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.

#
# Replacement function centralised to replace the use of cellparm.
#

def compute_average_unit_cell(unit_cell_list):
  '''Compute the weighted average unit cell based on a list of

  ((unit cell), nref)

  tuples.'''

  w_tot = 0.0

  a_tot = 0.0
  b_tot = 0.0
  c_tot = 0.0
  alpha_tot = 0.0
  beta_tot = 0.0
  gamma_tot = 0.0

  for cell, n_ref in unit_cell_list:
    w_tot += n_ref
    a_tot += cell[0] * n_ref
    b_tot += cell[1] * n_ref
    c_tot += cell[2] * n_ref
    alpha_tot += cell[3] * n_ref
    beta_tot += cell[4] * n_ref
    gamma_tot += cell[5] * n_ref

  return (a_tot / w_tot, b_tot / w_tot, c_tot / w_tot,
          alpha_tot / w_tot, beta_tot / w_tot, gamma_tot / w_tot)


#
# A replacement for the FORTRAN program DOSER, which adds two columns DOSE
# and TIME to unmerged MTZ files, so that they can be analysed dose-wise
# by CHEF. In reality, the functionality of both could be mapped to a
# single program now...
#

def add_dose_time_to_mtz(hklin, hklout, doses, times = None):
  '''Add doses and times from dictionaries doses, times (optional)
  to hklin to produce hklout. The dictionaries are indexed by the
  BATCH column in hklin. Will raise exception if no BATCH column.'''

  # instantiate the MTZ object representation

  from iotbx import mtz
  from cctbx.array_family import flex

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

  # right, so get the values out from the batch column, create a flex
  # array of the same size and assign DOSE, TIME, then add these to the
  # same dataset.

  batch_column_values = batch_column.extract_values(
      not_a_number_substitute = -1)

  dose_column = batch_dataset.add_column(label = 'DOSE', type = 'R')
  dose_column_values = flex.float()

  if times:
    time_column = batch_dataset.add_column(label = 'TIME', type = 'R')
    time_column_values = flex.float()

  valid = flex.bool()

  for b in batch_column_values:

    valid.append(True)
    dose_column_values.append(doses.get(b, -1.0))

    if times:
      time_column_values.append(times.get(b, -1.0))

  # add the columns back to the MTZ file structure

  dose_column.set_values(values = dose_column_values,
                         selection_valid = valid)

  if times:
    time_column.set_values(values = time_column_values,
                           selection_valid = valid)

  # and write this lot out as hklout

  mtz_obj.write(file_name = hklout)

if (__name__ == "__main__"):
  doses = { }
  times = { }

  for record in open('doser.in', 'r').readlines():
    values = record.split()
    if not values:
      continue
    batch = int(values[1])
    dose = float(values[3])
    time = float(values[5])

    doses[batch] = dose
    times[batch] = time

  import sys
  add_dose_time_to_mtz(hklin = sys.argv[1],
                       hklout = sys.argv[2],
                       doses = doses,
                       times = times)
