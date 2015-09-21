from __future__ import division
import math

from cctbx.array_family import flex

from libtbx import phil
phil_scope = phil.parse("""\
resolution_bins = 8
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
""")

def run(args):
  from iotbx.reflection_file_reader import any_reflection_file

  interp = phil_scope.command_line_argument_interpreter()
  params, unhandled = interp.process_and_fetch(
    args, custom_processor='collect_remaining')
  params = params.extract()
  n_bins = params.resolution_bins

  args = unhandled

  intensities = None
  batches = None

  f = args[0]

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
  mtz_object = reader.file_content()

  indices = mtz_object.extract_original_index_miller_indices()
  intensities = intensities.customized_copy(indices=indices)
  batches = batches.customized_copy(indices=indices)

  if params.anomalous:
    intensities = intensities.as_anomalous_array()
    batches = batches.as_anomalous_array()
  intensities_asu = intensities.map_to_asu()
  merged = intensities.merge_equivalents().array()

  unique_indices = merged.indices()

  n_batches = flex.max(batches.data())

  dose = batches.data()

  range_min = params.range.min
  range_max = params.range.max
  range_width = params.range.width
  assert range_width > 0

  if range_min is None:
    range_min = flex.min(dose)
  if range_max is None:
    range_max = flex.max(dose)
  n_steps = 2 + int((range_max - range_min) - range_width)

  sel = (dose.as_double() <= range_max) & (dose.as_double() >= range_min)
  dose = dose.select(sel)
  intensities_asu = intensities_asu.select(sel)

  intensities_data = intensities_asu.data()
  sigmas = intensities_asu.sigmas()
  d_star_sq = intensities_asu.d_star_sq().data()

  binner = merged.setup_binner(n_bins=n_bins)
  A = [[0] * n_steps for i in xrange(n_bins)]
  B = [[0] * n_steps for i in xrange(n_bins)]
  isigma = [[0] * n_steps for i in xrange(n_bins)]
  count = [[0] * n_steps for i in xrange(n_bins)]

  from cctbx import miller
  matches = miller.match_multi_indices(unique_indices, intensities_asu.indices())
  pairs = matches.pairs()
  n_pairs = pairs.size()

  for i_pair, (i_unique, i_ref) in enumerate(pairs):
    dose_i = dose[i_ref]
    I_i = intensities_data[i_ref]
    sigi_i = sigmas[i_ref]
    i_bin = binner.get_i_bin(d_star_sq[i_ref])-1
    for j_pair in xrange(i_pair+1, n_pairs):
      j_unique, j_ref = pairs[j_pair]
      if i_unique != j_unique:
        break
      assert i_ref != j_ref
      I_j = intensities_data[j_ref]
      sigi_j = sigmas[i_ref]
      A_part = math.fabs(I_i - I_j)
      B_part = 0.5 * math.fabs(I_i + I_j)
      dose_j = dose[j_ref]
      dose_0 = int((max(dose_i, dose_j) - range_min)/range_width)
      assert dose_0 >= 0
      A[i_bin][dose_0] += A_part
      B[i_bin][dose_0] += B_part
      isigma[i_bin][dose_0] += (I_i/sigi_i) + (I_j/sigi_j)
      count[i_bin][dose_0] += 2

  # now accumulate as a function of time

  for i_bin in xrange(n_bins):
    for j in xrange(1, n_steps):
      A[i_bin][j] += A[i_bin][j-1]
      B[i_bin][j] += B[i_bin][j-1]
      isigma[i_bin][j] += isigma[i_bin][j-1]
      count[i_bin][j] += count[i_bin][j-1]

  # accumulate as a function of dose and resolution

  rcp_overall = flex.double(n_steps, 0)
  rcp_bins = []
  scp_overall = flex.double(n_steps, 0)
  scp_bins = []
  for i_bin in xrange(n_bins):
    rcp_b = flex.double()
    scp_b = flex.double()
    for d in xrange(n_steps):
      top = A[i_bin][d]
      bottom = B[i_bin][d]
      rcp = 0.0
      scp = 0.0
      if bottom > 0:
        rcp = top/bottom
        if count[i_bin][d] > 100:
          isig = isigma[i_bin][d] / count[i_bin][d]
          scp = rcp / (1.1284 / isig)
      rcp_b.append(rcp)
      scp_b.append(scp)
    rcp_bins.append(rcp_b)
    scp_bins.append(scp_b)
    rcp_overall += rcp_b
    scp_overall += scp_b

  rcp_overall /= n_bins
  scp_overall /= n_bins

  from iotbx.data_plots import table_data

  # output scp in loggraph format

  title = "Cumulative radiation damage analysis:"
  column_labels = ["BATCH"] + ["S%i" %i for i in range(n_bins)] + ["Rcp(d)"]
  column_formats = ["%8.1f"] + ["%7.4f" for i in range(n_bins+1)]
  graph_names = ["Rcp(d)"]
  graph_columns = [[0,9]]

  table_rcp = table_data(title=title,
                         column_labels=column_labels,
                         column_formats=column_formats,
                         graph_names=graph_names,
                         graph_columns=graph_columns)
  for i in xrange(n_steps):
    row = [i * range_width + range_min] \
      + [rcp_bins[j][i] for j in xrange(len(rcp_bins))] + [rcp_overall[i]]
    table_rcp.add_row(row)

  print table_rcp.format_loggraph()

  # output scp in loggraph format

  title = "Normalised radiation damage analysis:"
  column_labels = ["BATCH"] + ["S%i" %i for i in range(n_bins)] + ["Scp(d)"]
  column_formats = ["%8.1f"] + ["%7.4f" for i in range(n_bins+1)]
  graph_names = ["Scp(d)"]
  graph_columns = [[0,9]]

  table_scp = table_data(title=title,
                         column_labels=column_labels,
                         column_formats=column_formats,
                         graph_names=graph_names,
                         graph_columns=graph_columns)
  for i in xrange(n_steps):
    row = [i * range_width + range_min] \
      + [scp_bins[j][i] for j in xrange(len(scp_bins))] + [scp_overall[i]]
    table_scp.add_row(row)

  print table_scp.format_loggraph()


if __name__ == '__main__':
  import sys
  run(sys.argv[1:])
