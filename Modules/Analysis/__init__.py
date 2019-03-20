from __future__ import absolute_import, division, print_function

from cctbx.array_family import flex
from libtbx import phil
from xia2.Modules.PyChef import dose_phil_str
from xia2.Modules.MultiCrystalAnalysis import batch_phil_scope

phil_scope = phil.parse(
    """\
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
"""
    % (dose_phil_str, batch_phil_scope)
)
