from cctbx.array_family import flex
from iotbx.data_plots import table_data
from libtbx import phil

import math

phil_scope = phil.parse("""\
d_min = None
  .type = float(value_min=0)
d_max = None
  .type = float(value_min=0)
resolution_bins = 20
  .type = int
anomalous = False
  .type = bool
range {
  width = 1
    .type = float(value_min=0)
  min = None
    .type = float(value_min=0)
  max = None
    .type = float(value_min=0)
}
batch
  .multiple = True
{
  range = None
    .type = ints(value_min=0, size=2)
  dose_start = None
    .type = float(value_min=0)
  dose_step = None
    .type = float(value_min=0)
}
""")


class batch_binned_data(object):
  def __init__(self, batches, data, data_fmt=None):
    self.batches = batches
    self.data = data
    self.data_fmt = data_fmt

  def as_simple_table(self, data_label, data_fmt=None):
    pass


def scales_vs_batch(scales, batches):
  assert scales.size() == batches.size()

  bins = []
  data = []

  for i in range(int(math.floor(flex.min(batches.data()))),
                 int(math.ceil(flex.max(batches.data())))+1):
    sel = (batches.data() >= i) & (batches.data() < (i+1))

    sc = scales.data().select(sel)
    bins.append(i)
    data.append(flex.mean(sc))

  return batch_binned_data(bins, data)


def rmerge_vs_batch(intensities, batches):
  assert intensities.size() == batches.size()

  intensities = intensities.map_to_asu()

  bins = []
  data = []

  merging = intensities.merge_equivalents()
  merged_intensities = merging.array()

  from cctbx import miller

  for i in range(int(math.floor(flex.min(batches.data()))),
                 int(math.ceil(flex.max(batches.data())))+1):
    sel = (batches.data() >= i) & (batches.data() < (i+1))

    numerator = 0
    denominator = 0

    intensities_sel = intensities.select(sel)
    matches = miller.match_multi_indices(
      merged_intensities.indices(), intensities_sel.indices())

    for p in matches.pairs():
      unmerged_Ij = intensities_sel.data()[p[1]]
      merged_Ij = merged_intensities.data()[p[0]]
      numerator += abs(unmerged_Ij - merged_Ij)
      denominator += unmerged_Ij

    bins.append(i)
    if denominator > 0:
      data.append(numerator/denominator)
    else:
      data.append(0)

  return batch_binned_data(bins, data)
