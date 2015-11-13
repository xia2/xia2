from __future__ import division
from libtbx.test_utils import approx_equal

def exercise_observations():
  from xia2.Modules.PyChef2 import Observations
  from cctbx.array_family import flex
  from cctbx import sgtbx
  miller_indices = flex.miller_index(
    ((1,2,3),(-1,2,3),(1,-2,3), (4,5,6),(4,5,-6)))
  sg = sgtbx.space_group_info(symbol="I222").group()
  anomalous_flag = True
  observations = Observations(miller_indices, sg, anomalous_flag)
  groups = observations.observation_groups()
  assert list(groups[(1,2,3)].iplus()) == [0]
  assert list(groups[(1,2,3)].iminus()) == [1,2]
  print "OK"

def exercise_accumulators():
  from xia2.Modules.PyChef2 import PyChef
  from xia2.Modules.PyChef2 import Observations
  from xia2.Modules.PyChef2 import CompletenessAccumulator
  from xia2.Modules.PyChef2 import RcpScpAccumulator
  from cctbx.array_family import flex

  from iotbx.reflection_file_reader import any_reflection_file
  f = "/Users/rjgildea/tmp/insulin_dials/DataFiles/AUTOMATIC_DEFAULT_scaled_unmerged.mtz"
  reader = any_reflection_file(f)
  assert reader.file_type() == 'ccp4_mtz'
  arrays = reader.as_miller_arrays(merge_equivalents=False)
  for ma in arrays:
    if ma.info().labels == ['BATCH']:
      batches = ma
    elif ma.info().labels == ['I', 'SIGI']:
      intensities = ma
    elif ma.info().labels == ['I(+)', 'SIGI(+)', 'I(-)', 'SIGI(-)']:
      intensities = ma
  assert intensities is not None
  assert batches is not None

  anomalous_flag = True
  if anomalous_flag:
    intensities = intensities.as_anomalous_array()

  stats = PyChef.statistics(intensities, batches.data())
  comp_stats = stats.calc_completeness_vs_dose()
  rcp_scp_stats = stats.calc_rcp_scp()

  miller_indices = batches.indices()
  sg = batches.space_group()

  observations = Observations(miller_indices, sg, anomalous_flag)
  n_steps = stats.n_steps
  dose = batches.data()
  range_width  = 1
  range_max = flex.max(dose)
  range_min = flex.min(dose) - range_width
  dose /= range_width
  dose -= range_min
  accumulate = CompletenessAccumulator(
    flex.size_t(list(dose)), stats.d_star_sq, stats.binner, n_steps)

  binner_non_anom = intensities.as_non_anomalous_array().use_binning(
    stats.binner)
  n_complete = binner_non_anom.counts_complete()[1:-1]

  for g in observations.observation_groups():
    accumulate(g.data())
  accumulate.finalise(flex.size_t(n_complete))

  assert approx_equal(accumulate.iplus_completeness(), comp_stats.iplus_comp_overall)
  assert approx_equal(accumulate.iminus_completeness(), comp_stats.iminus_comp_overall)
  assert approx_equal(accumulate.ieither_completeness(), comp_stats.ieither_comp_overall)
  assert approx_equal(accumulate.iboth_completeness(), comp_stats.iboth_comp_overall)

  accumulate_rcp_scp = RcpScpAccumulator(
    intensities.data(), intensities.sigmas(),
    flex.size_t(list(dose)), batches.d_star_sq().data(), stats.binner, n_steps)

  for g in observations.observation_groups():
    accumulate_rcp_scp(g.data())
  accumulate_rcp_scp.finalise()

  assert approx_equal(accumulate_rcp_scp.rcp(), rcp_scp_stats[1])
  assert approx_equal(accumulate_rcp_scp.scp(), rcp_scp_stats[3])

  print "OK"

def run():
  exercise_observations()
  exercise_accumulators()

if __name__ == '__main__':
  run()
