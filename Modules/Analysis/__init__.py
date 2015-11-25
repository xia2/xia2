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

  perm = flex.sort_permutation(batches.data())
  batches = batches.data().select(perm)
  scales = scales.data().select(perm)

  i_batch_start = 0
  current_batch = flex.min(batches)
  n_ref = batches.size()
  for i_ref in range(n_ref+1):
    if i_ref == n_ref or batches[i_ref] != current_batch:
      assert batches[i_batch_start:i_ref].all_eq(current_batch)
      data.append(flex.mean(scales[i_batch_start:i_ref]))
      bins.append(current_batch)
      i_batch_start = i_ref
      if i_ref < n_ref:
        current_batch = batches[i_batch_start]

  return batch_binned_data(bins, data)


def rmerge_vs_batch(intensities, batches):
  assert intensities.size() == batches.size()

  intensities = intensities.map_to_asu()

  bins = []
  data = []

  merging = intensities.merge_equivalents()
  merged_intensities = merging.array()

  perm = flex.sort_permutation(batches.data())
  batches = batches.data().select(perm)
  intensities = intensities.select(perm)

  from cctbx import miller

  matches = miller.match_multi_indices(
    merged_intensities.indices(), intensities.indices())
  pairs = matches.pairs()

  i_batch_start = 0
  current_batch = flex.min(batches)
  n_ref = batches.size()
  for i_ref in range(n_ref+1):
    if i_ref == n_ref or batches[i_ref] != current_batch:
      assert batches[i_batch_start:i_ref].all_eq(current_batch)

      numerator = 0
      denominator = 0

      for p in pairs[i_batch_start:i_ref]:
        unmerged_Ij = intensities.data()[p[1]]
        merged_Ij = merged_intensities.data()[p[0]]
        numerator += abs(unmerged_Ij - merged_Ij)
        denominator += unmerged_Ij

      bins.append(current_batch)
      if denominator > 0:
        data.append(numerator/denominator)
      else:
        data.append(0)

      i_batch_start = i_ref
      if i_ref < n_ref:
        current_batch = batches[i_batch_start]

  return batch_binned_data(bins, data)
