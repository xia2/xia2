from __future__ import absolute_import, division, print_function

from cctbx.array_family import flex
from libtbx import phil
from xia2.Modules.PyChef import dose_phil_str
from xia2.Modules.MultiCrystalAnalysis import batch_phil_scope

phil_scope = phil.parse("""\
d_min = None
  .type = float(value_min=0)
d_max = None
  .type = float(value_min=0)
resolution_bins = 20
  .type = int
anomalous = False
  .type = bool
use_internal_variance = False
  .type = bool
  .help = Use internal variance of the data in the calculation of the merged sigmas
  .short_caption = "Use internal variance"
eliminate_sys_absent = False
  .type = bool
  .help = Eliminate systematically absent reflections before computation of merging statistics.
  .short_caption = "Eliminate systematic absences before calculation"
range {
  width = 1
    .type = float(value_min=0)
  min = None
    .type = float(value_min=0)
  max = None
    .type = float(value_min=0)
}
cc_half_significance_level = 0.01
  .type = float(value_min=0, value_max=1)
cc_half_method = *half_dataset sigma_tau
  .type = choice
chef_min_completeness = None
  .type = float(value_min=0, value_max=1)
  .help = "Minimum value of completeness in outer resolution shell used to "
          "determine suitable resolution cutoff for CHEF analysis"
%s
xtriage_analysis = True
  .type = bool
include_radiation_damage = True
  .type = bool
include_probability_plots = False
  .type = bool
%s
""" % (dose_phil_str, batch_phil_scope))

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
  for i_ref in range(n_ref + 1):
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
  for i_ref in range(n_ref + 1):
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
        data.append(numerator / denominator)
      else:
        data.append(0)

      i_batch_start = i_ref
      if i_ref < n_ref:
        current_batch = batches[i_batch_start]

  return batch_binned_data(bins, data)

def i_sig_i_vs_batch(intensities, batches):
  assert intensities.size() == batches.size()
  assert intensities.sigmas() is not None
  sel = intensities.sigmas() > 0

  i_sig_i = intensities.data().select(sel) / intensities.sigmas().select(sel)
  batches = batches.select(sel)

  bins = []
  data = []

  perm = flex.sort_permutation(batches.data())
  batches = batches.data().select(perm)
  i_sig_i = i_sig_i.select(perm)

  i_batch_start = 0
  current_batch = flex.min(batches)
  n_ref = batches.size()
  for i_ref in range(n_ref + 1):
    if i_ref == n_ref or batches[i_ref] != current_batch:
      assert batches[i_batch_start:i_ref].all_eq(current_batch)
      data.append(flex.mean(i_sig_i[i_batch_start:i_ref]))
      bins.append(current_batch)
      i_batch_start = i_ref
      if i_ref < n_ref:
        current_batch = batches[i_batch_start]

  return batch_binned_data(bins, data)
