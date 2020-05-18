from collections import OrderedDict

from libtbx import phil
from dials.pychef import dose_phil_str

batch_phil_scope = """\
batch
  .multiple = True
{
  id = None
    .type = str
  range = None
    .type = ints(size=2, value_min=0)
}
"""

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
%s
"""
    % (dose_phil_str, batch_phil_scope)
)


class separate_unmerged:
    def __init__(self, unmerged_intensities, batches_all, id_to_batches=None):

        intensities = OrderedDict()
        batches = OrderedDict()

        if id_to_batches is None:
            run_id_to_batch_id = None
            run_id = 0
            unique_batches = sorted(set(batches_all.data()))
            last_batch = None
            run_start = unique_batches[0]
            for i, batch in enumerate(unique_batches):
                if (
                    last_batch is not None
                    and batch > (last_batch + 1)
                    or (i + 1) == len(unique_batches)
                ):
                    if (i + 1) == len(unique_batches):
                        last_batch += 1
                    batch_sel = (batches_all.data() >= run_start) & (
                        batches_all.data() <= last_batch
                    )
                    batches[run_id] = batches_all.select(batch_sel)
                    intensities[run_id] = unmerged_intensities.select(batch_sel)
                    run_id += 1
                    run_start = batch
                last_batch = batch

        else:
            run_id_to_batch_id = OrderedDict()
            run_id = 0
            for batch_id, batch_range in id_to_batches.items():
                run_id_to_batch_id[run_id] = batch_id
                run_start, last_batch = batch_range
                batch_sel = (batches_all.data() >= run_start) & (
                    batches_all.data() <= last_batch
                )
                batches[run_id] = batches_all.select(batch_sel)
                intensities[run_id] = unmerged_intensities.select(batch_sel)
                run_id += 1

        self.run_id_to_batch_id = run_id_to_batch_id
        self.intensities = intensities
        self.batches = batches
