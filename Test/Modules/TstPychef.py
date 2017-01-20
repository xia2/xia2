from __future__ import absolute_import, division
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
  from xia2.Modules.PyChef2 import ChefStatistics
  from iotbx.reflection_file_reader import any_reflection_file
  from cctbx.array_family import flex
  import libtbx.load_env
  import os

  xia2_regression = libtbx.env.find_in_repositories("xia2_regression")
  if xia2_regression is None:
    print "Skipping exercise_accumulators(): xia2_regression not available"
    return

  f = os.path.join(xia2_regression, "test/insulin_dials_scaled_unmerged.mtz")
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

  pystats = PyChef.PyStatistics(intensities, batches.data())

  miller_indices = batches.indices()
  sg = batches.space_group()

  n_steps = pystats.n_steps
  dose = batches.data()
  range_width  = 1
  range_max = flex.max(dose)
  range_min = flex.min(dose) - range_width
  dose /= range_width
  dose -= range_min

  binner_non_anom = intensities.as_non_anomalous_array().use_binning(
    pystats.binner)
  n_complete = flex.size_t(binner_non_anom.counts_complete()[1:-1])

  dose = flex.size_t(list(dose))

  chef_stats = ChefStatistics(
    miller_indices, intensities.data(), intensities.sigmas(),
    intensities.d_star_sq().data(), dose, n_complete, pystats.binner,
    sg, anomalous_flag, n_steps)

  # test completeness

  assert approx_equal(chef_stats.iplus_completeness(), pystats.iplus_comp_overall)
  assert approx_equal(chef_stats.iminus_completeness(), pystats.iminus_comp_overall)
  assert approx_equal(chef_stats.ieither_completeness(), pystats.ieither_comp_overall)
  assert approx_equal(chef_stats.iboth_completeness(), pystats.iboth_comp_overall)

  # test rcp,scp

  assert approx_equal(chef_stats.rcp(), pystats.rcp)
  assert approx_equal(chef_stats.scp(), pystats.scp)

  # test Rd

  assert approx_equal(chef_stats.rd(), pystats.rd)

  print "OK"

def run():
  exercise_observations()
  exercise_accumulators()

if __name__ == '__main__':
  run()
