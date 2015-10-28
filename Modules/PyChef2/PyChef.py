from __future__ import division

import math
from collections import Mapping
from cctbx.array_family import flex
from iotbx.data_plots import table_data
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


class observations_single_miller_index(object):

  PLUS = 1
  MINUS = -1
  CENTRIC = 0

  def __init__(self, asu_index, flag, irefs=None):
    assert flag in (self.PLUS, self.MINUS, self.CENTRIC)
    self._asu_index = asu_index
    self._flag = flag
    if irefs is None:
      irefs = flex.size_t()
    self._irefs = irefs

  def add_iref(self, iref):
    self._irefs.append(iref)

  @property
  def irefs(self):
    return self._irefs

  @property
  def asu_index(self):
    return self._asu_index

  @property
  def flag(self):
    return self._flag

  def is_plus(self):
    return self._flag == self.PLUS

  def is_minus(self):
    return self._flag == self.MINUS

  def is_centric(self):
    return self._flag == self.CENTRIC


class unmerged_observations(Mapping):

  def __init__(self, unmerged_intensities):
    self._intensities_original_index = unmerged_intensities

    self._observations = {}
    from cctbx import miller, sgtbx
    sg = self._intensities_original_index.space_group()
    sg_type = sg.type()
    asu = sgtbx.reciprocal_space_asu(sg_type)
    anomalous_flag = self._intensities_original_index.anomalous_flag()

    ma = self._intensities_original_index
    original_indices = ma.indices()
    unique_indices = original_indices.deep_copy()
    isym = flex.int(unique_indices.size())

    miller.map_to_asu_isym(sg_type, anomalous_flag, unique_indices, isym)

    for iref in range(len(original_indices)):
      h_orig = original_indices[iref]
      h_uniq = unique_indices[iref]
      h_isym = isym[iref]

      if h_uniq not in self._observations:
        h_eq = miller.sym_equiv_indices(sg, h_uniq)
        asu_which = asu.which(h_uniq)
        assert asu_which != 0
        if h_eq.is_centric():
          flag = observations_single_miller_index.CENTRIC
        elif asu_which == 1:
          flag = observations_single_miller_index.PLUS
        else:
          flag = observations_single_miller_index.MINUS
        self._observations[h_uniq] = observations_single_miller_index(
          h_uniq, flag)

      self._observations[h_uniq].add_iref(iref)

  def __iter__(self):
    return self._observations.iteritems()

  def __getitem__(self, hkl):
    return self._observations[hkl]

  def __len__(self):
    return len(self._observations)

  def __contains__(self, hkl):
    return hkl in self._observations


class statistics(object):

  def __init__(self, intensities, dose, n_bins=8,
               range_min=None, range_max=None, range_width=1):

    self.intensities = intensities
    self.dose = dose
    self.n_bins = n_bins
    self.range_min = range_min
    self.range_max = range_max
    self.range_width = range_width
    assert self.range_width > 0

    if self.range_min is None:
      self.range_min = flex.min(self.dose) - self.range_width
    if self.range_max is None:
      self.range_max = flex.max(self.dose)
    self.n_steps = 2 + int((self.range_max - self.range_min) - self.range_width)

    sel = (self.dose.as_double() <= self.range_max) & (self.dose.as_double() >= self.range_min)
    self.dose = self.dose.select(sel)

    self.intensities = self.intensities.select(sel)
    self.d_star_sq = self.intensities.d_star_sq().data()

    self.observations = unmerged_observations(self.intensities)

  def calc_completeness_vs_dose(self):

    iplus_count = flex.size_t(self.n_steps, 0)
    iminus_count = flex.size_t(self.n_steps, 0)
    ieither_count = flex.size_t(self.n_steps, 0)
    iboth_count = flex.size_t(self.n_steps, 0)

    for h_uniq, observed in self.observations:
      if observed.is_minus():
        continue

      irefs = sorted(observed.irefs)
      dose_min_iplus = self.range_max + self.range_width
      dose_min_iminus = self.range_max + self.range_width

      for i, i_ref in enumerate(irefs):
        dose_i = self.dose[i_ref]
        if observed.is_centric():
          dose_min_iplus = min(dose_i, dose_min_iplus)
          dose_min_iminus = min(dose_i, dose_min_iminus)
        else:
          dose_min_iplus = min(dose_i, dose_min_iplus)

      h_uniq_minus = tuple(-h for h in h_uniq)
      if h_uniq_minus in self.observations:
        observed = self.observations[h_uniq_minus]
        irefs = sorted(observed.irefs)
        for i, i_ref in enumerate(irefs):
          dose_i = self.dose[i_ref]
          dose_min_iminus = min(dose_i, dose_min_iminus)

      start_iplus = int((dose_min_iplus - self.range_min)/self.range_width)
      start_iminus = int((dose_min_iminus - self.range_min)/self.range_width)

      if start_iplus < self.n_steps:
        iplus_count[start_iplus] += 1
      if start_iminus < self.n_steps:
        iminus_count[start_iminus] += 1
      if min(start_iplus, start_iminus) < self.n_steps:
        ieither_count[min(start_iplus, start_iminus)] += 1
      if max(start_iplus, start_iminus) < self.n_steps:
        iboth_count[max(start_iplus, start_iminus)] += 1

    for j in range(1, self.n_steps):
      iplus_count[j] += iplus_count[j - 1]
      iminus_count[j] += iminus_count[j - 1]
      ieither_count[j] += ieither_count[j - 1]
      iboth_count[j] += iboth_count[j - 1]

    return iplus_count, iminus_count, ieither_count, iboth_count

  def calc_rcp_scp(self):

    merged = self.intensities.merge_equivalents().array()
    binner = merged.setup_binner_d_star_sq_step(
      d_star_sq_step=(flex.max(self.d_star_sq)-flex.min(self.d_star_sq)+1e-8)/self.n_bins)
    A = [[0] * self.n_steps for i in xrange(self.n_bins)]
    B = [[0] * self.n_steps for i in xrange(self.n_bins)]
    isigma = [[0] * self.n_steps for i in xrange(self.n_bins)]
    count = [[0] * self.n_steps for i in xrange(self.n_bins)]

    intensities_data = self.intensities.data()
    sigmas = self.intensities.sigmas()

    for h_uniq, observed in self.observations:
      irefs = sorted(observed.irefs)
      if len(irefs) == 1:
        # lone observation, no pairs
        continue
      for i, i_ref in enumerate(irefs):
        dose_i = self.dose[i_ref]
        I_i = intensities_data[i_ref]
        sigi_i = sigmas[i_ref]
        i_bin = binner.get_i_bin(self.d_star_sq[i_ref]) - 1
        for j, j_ref in enumerate(irefs[i+1:]):
          assert abs(self.d_star_sq[j_ref] - self.d_star_sq[i_ref]) < 1e-8
          I_j = intensities_data[j_ref]
          sigi_j = sigmas[i_ref]
          A_part = math.fabs(I_i - I_j)
          B_part = 0.5 * math.fabs(I_i + I_j)
          dose_j = self.dose[j_ref]
          dose_0 = int((max(dose_i, dose_j) - self.range_min)/self.range_width)
          assert dose_0 >= 0
          A[i_bin][dose_0] += A_part
          B[i_bin][dose_0] += B_part
          isigma[i_bin][dose_0] += (I_i/sigi_i) + (I_j/sigi_j)
          count[i_bin][dose_0] += 2

    # now accumulate as a function of time

    for i_bin in xrange(self.n_bins):
      for j in xrange(1, self.n_steps):
        A[i_bin][j] += A[i_bin][j-1]
        B[i_bin][j] += B[i_bin][j-1]
        isigma[i_bin][j] += isigma[i_bin][j-1]
        count[i_bin][j] += count[i_bin][j-1]

    # accumulate as a function of dose and resolution

    rcp_overall = flex.double(self.n_steps, 0)
    rcp_bins = [flex.double(self.n_steps, 0) for i in range(self.n_bins)]
    scp_overall = flex.double(self.n_steps, 0)
    scp_bins = [flex.double(self.n_steps, 0) for i in range(self.n_bins)]

    for j in xrange(self.n_steps):

      for i_bin in xrange(self.n_bins):
        top = A[i_bin][j]
        bottom = B[i_bin][j]

        rcp = 0.0
        scp = 0.

        if bottom > 0:
          rcp = top/bottom
          if count[i_bin][j] > 100:
            isig = isigma[i_bin][j] / count[i_bin][j]
            scp = rcp / (1.1284 / isig)

          rcp_bins[i_bin][j] = rcp
          scp_bins[i_bin][j] = scp

      ot = sum(A[i_bin][j] for i_bin in xrange(self.n_bins))
      ob = sum(B[i_bin][j] for i_bin in xrange(self.n_bins))

      if ob > 0:
        overall = ot/ob
      else:
        overall = 0.
      rcp_overall[j] = overall

      scp_overall[j] = sum(scp_bins[i_bin][j] for i_bin in xrange(self.n_bins))/self.n_bins
    return rcp_bins, rcp_overall, scp_bins, scp_overall

  def calc_rd(self):

    rd_top = flex.double(self.n_steps, 0)
    rd_bottom = flex.double(self.n_steps, 0)

    intensities_data = self.intensities.data()
    sigmas = self.intensities.sigmas()

    for h_uniq, observed in self.observations:
      irefs = sorted(observed.irefs)
      if len(irefs) == 1:
        # lone observation, no pairs
        continue
      for i, i_ref in enumerate(irefs):
        dose_i = self.dose[i_ref]
        I_i = intensities_data[i_ref]
        for j, j_ref in enumerate(irefs[i+1:]):
          assert abs(self.d_star_sq[j_ref] - self.d_star_sq[i_ref]) < 1e-8
          I_j = intensities_data[j_ref]
          dose_j = self.dose[j_ref]
          d_dose = int(
            round(math.fabs(dose_i - dose_j) - self.range_min)/self.range_width)
          rd_top[d_dose] += math.fabs(I_i - I_j)
          rd_bottom[d_dose] += 0.5 * (I_i + I_j)

    rd = flex.double(rd_top[i]/rd_bottom[i] if rd_bottom[i] > 0 else 0
                     for i in xrange(self.n_steps))
    return rd

  def print_completeness_vs_dose(self, iplus_count, iminus_count,
                                 ieither_count, iboth_count):

    anomalous = self.intensities.anomalous_flag()

    title = "Completeness vs. BATCH:"
    graph_names = ["Completeness"]

    if anomalous:
      column_labels = ["BATCH", 'I+', 'I-', 'I', 'dI']
      column_formats = ["%8.1f", "%5.3f", "%5.3f", "%5.3f", "%5.3f"]
      graph_columns = [[0,1,2,3,4]]
    else:
      column_labels = ["BATCH", "I"]
      column_formats = ["%8.1f", "%5.3f"]
      graph_columns = [[0,1]]

    table_completeness = table_data(title=title,
                                    column_labels=column_labels,
                                    column_formats=column_formats,
                                    graph_names=graph_names,
                                    graph_columns=graph_columns)
    for i in xrange(self.n_steps):
      if anomalous:
        row = [i * self.range_width + self.range_min, iplus_count[i],
               iminus_count[i], ieither_count[i], iboth_count[i]]
      else:
        row = [i * self.range_width + self.range_min, ieither_count[i]]
      table_completeness.add_row(row)

    print table_completeness.format_loggraph()

  def print_rcp_vs_dose(self, rcp_bins, rcp_overall):

    title = "Cumulative radiation damage analysis:"
    column_labels = ["BATCH"] + ["S%i" %i for i in range(self.n_bins)] + ["Rcp(d)"]
    column_formats = ["%8.1f"] + ["%7.4f" for i in range(self.n_bins+1)]
    graph_names = ["Rcp(d)"]
    graph_columns = [[0,9]]

    table_rcp = table_data(title=title,
                           column_labels=column_labels,
                           column_formats=column_formats,
                           graph_names=graph_names,
                           graph_columns=graph_columns)
    for i in xrange(self.n_steps):
      row = [i * self.range_width + self.range_min] \
        + [rcp_bins[j][i] for j in xrange(len(rcp_bins))] + [rcp_overall[i]]
      table_rcp.add_row(row)

    print table_rcp.format_loggraph()

  def print_scp_vs_dose(self, scp_bins, scp_overall):

    title = "Normalised radiation damage analysis:"
    column_labels = ["BATCH"] + ["S%i" %i for i in range(self.n_bins)] + ["Scp(d)"]
    column_formats = ["%8.1f"] + ["%7.4f" for i in range(self.n_bins+1)]
    graph_names = ["Scp(d)"]
    graph_columns = [[0,9]]

    table_scp = table_data(title=title,
                           column_labels=column_labels,
                           column_formats=column_formats,
                           graph_names=graph_names,
                           graph_columns=graph_columns)
    for i in xrange(self.n_steps):
      row = [i * self.range_width + self.range_min] \
        + [scp_bins[j][i] for j in xrange(len(scp_bins))] + [scp_overall[i]]
      table_scp.add_row(row)

    print table_scp.format_loggraph()

  def print_rd_vs_dose(self, rd):

    title = "R vs. BATCH difference:"
    column_labels = ["BATCH", "Scp(d)"]
    column_formats = ["%8.1f", "%5.3f"]
    graph_names = ["Rd"]
    graph_columns = [[0,1]]

    table_rd = table_data(title=title,
                           column_labels=column_labels,
                           column_formats=column_formats,
                           graph_names=graph_names,
                           graph_columns=graph_columns)
    for i in xrange(self.n_steps):
      row = [i * self.range_width + self.range_min, rd[i]]
      table_rd.add_row(row)

    print table_rd.format_loggraph()


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

  reader = any_reflection_file(args[0])
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

  range_min = params.range.min
  range_max = params.range.max
  range_width = params.range.width

  if params.anomalous:
    intensities = intensities.as_anomalous_array()
    batches = batches.as_anomalous_array()

  dose = batches.data()

  stats = statistics(intensities, dose, n_bins=params.resolution_bins,
                     range_min=params.range.min, range_max=params.range.max,
                     range_width=params.range.width)

  iplus_count, iminus_count, ieither_count, iboth_count \
    = stats.calc_completeness_vs_dose()
  rcp_bins, rcp_overall, scp_bins, scp_overall = stats.calc_rcp_scp()
  rd = stats.calc_rd()

  stats.print_completeness_vs_dose(
    iplus_count, iminus_count, ieither_count, iboth_count)
  stats.print_rcp_vs_dose(rcp_bins, rcp_overall)
  stats.print_scp_vs_dose(scp_bins, scp_overall)
  stats.print_rd_vs_dose(rd)


if __name__ == '__main__':
  import sys
  run(sys.argv[1:])
