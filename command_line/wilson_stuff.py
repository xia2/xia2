from __future__ import division
from mmtbx.scaling import data_statistics
from iotbx import mtz
import sys

m = mtz.object(sys.argv[1])
mas = m.as_miller_arrays()

data = None

for ma in mas:
  if ma.is_xray_intensity_array():
    data = ma
    break

def nres_from_mtz(m):
  sg = m.space_group()
  uc = m.crystals()[0].unit_cell()
  n_ops = len(sg.all_ops())
  v_asu = uc.volume() / n_ops
  return v_asu / (2.7 * 128)

n_res = nres_from_mtz(m)

wilson_scaling = data_statistics.wilson_scaling(miller_array=data,
                                                n_residues=n_res)
wilson_scaling.show()

