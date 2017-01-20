from __future__ import absolute_import, division

import sys

from iotbx import mtz
from cctbx import sgtbx
from cctbx import crystal

def measure(hklin, spacegroup):
  '''Look at HKLIN, see how strong the absences (according to the given
  spacegroup) are... looking for IPR / SIGIPR.'''

  mtz_obj = mtz.object(hklin)

  sg = sgtbx.space_group(sgtbx.space_group_symbols(spacegroup).hall())
  mi = mtz_obj.extract_miller_indices()
  sg_m = mtz_obj.space_group()

  ipr_column = None
  sigipr_column = None

  for crystal in mtz_obj.crystals():
    for dataset in crystal.datasets():
      for column in dataset.columns():

        if column.label() == 'IPR':
          ipr_column = column
        elif column.label() == 'SIGIPR':
          sigipr_column = column

  assert(ipr_column is not None)
  assert(sigipr_column is not None)

  ipr_values = ipr_column.extract_values(not_a_number_substitute = 0.0)
  sigipr_values = sigipr_column.extract_values(not_a_number_substitute = 0.0)

  present = []
  absent = []

  for j in range(mi.size()):
    hkl = mi[j]

    if sg.is_sys_absent(hkl):
      absent.append(ipr_values[j] / sigipr_values[j])
    else:
      present.append(ipr_values[j] / sigipr_values[j])

  print 'A: %f' % (sum(absent) / len(absent))
  print 'P: %f' % (sum(present) / len(present))

if __name__ == '__main__':

  hklin = sys.argv[1]
  spacegroup = sys.argv[2]

  measure(hklin, spacegroup)
