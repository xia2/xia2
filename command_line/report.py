# -*- coding: utf-8 -*-

from __future__ import absolute_import, division
from cctbx.array_family import flex
import os
from cStringIO import StringIO

from libtbx.containers import OrderedDict

from xia2.Modules.Analysis import *

from mmtbx.scaling import printed_output
class xtriage_output(printed_output):

  def __init__(self, out):
    super(xtriage_output, self).__init__(out)
    self.gui_output = True
    self._out_orig = self.out
    self.out = StringIO()
    self._sub_header_to_out = {}

  def show_big_header (self, text) : pass

  def show_header (self, text) :
    self._out_orig.write(self.out.getvalue())
    self.out = StringIO()
    super(xtriage_output, self).show_header(text)

  def show_sub_header (self, title) :
    self._out_orig.write(self.out.getvalue())
    self.out = StringIO()
    self._current_sub_header = title
    assert title not in self._sub_header_to_out
    self._sub_header_to_out[title] = self.out

  def flush(self):
    self._out_orig.write(self.out.getvalue())
    self.out.flush()
    self._out_orig.flush()

def run(args):
  from iotbx.reflection_file_reader import any_reflection_file

  from xia2.Modules.Analysis import phil_scope
  interp = phil_scope.command_line_argument_interpreter()
  params, unhandled = interp.process_and_fetch(
    args, custom_processor='collect_remaining')
  params = params.extract()
  n_bins = params.resolution_bins
  cc_half_significance_level = params.cc_half_significance_level
  cc_half_method = params.cc_half_method

  args = unhandled

  intensities = None
  batches = None
  scales = None
  dose = None

  unmerged_mtz = args[0]
  reader = any_reflection_file(unmerged_mtz)
  assert reader.file_type() == 'ccp4_mtz'
  arrays = reader.as_miller_arrays(merge_equivalents=False)
  for ma in arrays:
    if ma.info().labels == ['BATCH']:
      batches = ma
    elif ma.info().labels == ['DOSE']:
      dose = ma
    elif ma.info().labels == ['I', 'SIGI']:
      intensities = ma
    elif ma.info().labels == ['I(+)', 'SIGI(+)', 'I(-)', 'SIGI(-)']:
      intensities = ma
    elif ma.info().labels == ['SCALEUSED']:
      scales = ma

  assert intensities is not None
  assert batches is not None
  mtz_object = reader.file_content()

  indices = mtz_object.extract_original_index_miller_indices()
  intensities = intensities.customized_copy(
    indices=indices, info=intensities.info())
  batches = batches.customized_copy(indices=indices, info=batches.info())

  from xia2.Wrappers.XIA.PlotMultiplicity import PlotMultiplicity
  mult_json_files = {}
  for axis in ('h', 'k', 'l'):
    pm = PlotMultiplicity()
    pm.set_mtz_filename(unmerged_mtz)
    pm.set_slice_axis(axis)
    pm.set_show_missing(True)
    pm.run()
    mult_json_files[axis] = pm.get_json_filename()

  from iotbx import merging_statistics
  merging_stats = merging_statistics.dataset_statistics(
    intensities, n_bins=n_bins,
    cc_one_half_significance_level=cc_half_significance_level,
    assert_is_not_unique_set_under_symmetry=False)

  intensities_anom = intensities.as_anomalous_array()
  intensities_anom = intensities_anom.map_to_asu().customized_copy(info=intensities.info())
  merging_stats_anom = merging_statistics.dataset_statistics(
    intensities_anom, n_bins=n_bins, anomalous=True,
    cc_one_half_significance_level=cc_half_significance_level,
    assert_is_not_unique_set_under_symmetry=False)

  merging = intensities.merge_equivalents()
  multiplicities = merging.redundancies().complete_array(new_data_value=0)
  mult_acentric = multiplicities.select_acentric().data()
  mult_centric = multiplicities.select_centric().data()

  multiplicities_acentric = {}
  multiplicities_centric = {}

  for x in sorted(set(mult_acentric)):
    multiplicities_acentric[x] = mult_acentric.count(x)
  for x in sorted(set(mult_centric)):
    multiplicities_centric[x] = mult_centric.count(x)

  headers = [u'Resolution (Å)', 'N(obs)', 'N(unique)', 'Multiplicity', 'Completeness',
             'Mean(I)', 'Mean(I/sigma)', 'Rmerge', 'Rmeas', 'Rpim', 'CC1/2']
  if not intensities.space_group().is_centric():
    headers.append('CCano')
  rows = []
  for bin_stats in merging_stats.bins:
    row = ['%.2f - %.2f' %(bin_stats.d_max, bin_stats.d_min),
           bin_stats.n_obs, bin_stats.n_uniq, '%.2f' %bin_stats.mean_redundancy,
           '%.2f' %(100*bin_stats.completeness), '%.1f' %bin_stats.i_mean,
           '%.1f' %bin_stats.i_over_sigma_mean, '%.3f' %bin_stats.r_merge,
           '%.3f' %bin_stats.r_meas, '%.3f' %bin_stats.r_pim]
    if cc_half_method == 'sigma_tau':
      row.append(
        '%.3f%s' %(bin_stats.cc_one_half_sigma_tau,
                   '*' if bin_stats.cc_one_half_sigma_tau_significance else ''))
    else:
      row.append(
        '%.3f%s' %(bin_stats.cc_one_half,
                   '*' if bin_stats.cc_one_half_significance else ''))

    if not intensities.space_group().is_centric():
      row.append(
        '%.3f%s' %(bin_stats.cc_anom, '*' if bin_stats.cc_anom_significance else ''))
    rows.append(row)

  merging_stats_table = [headers]
  merging_stats_table.extend(rows)

  unit_cell_params = intensities.unit_cell().parameters()

  headers = ['', 'Overall', 'Low resolution', 'High resolution']

  stats = (merging_stats.overall, merging_stats.bins[0], merging_stats.bins[-1])

  rows = [
    [u'Resolution (Å)'] + [
      '%.2f - %.2f' %(s.d_max, s.d_min) for s in stats],
    ['Observations'] + ['%i' %s.n_obs for s in stats],
    ['Unique reflections'] + ['%i' %s.n_uniq for s in stats],
    ['Multiplicity'] + ['%.1f' %s.mean_redundancy for s in stats],
    ['Completeness'] + ['%.2f%%' %(s.completeness * 100) for s in stats],
    #['Mean intensity'] + ['%.1f' %s.i_mean for s in stats],
    ['Mean I/sigma(I)'] + ['%.1f' %s.i_over_sigma_mean for s in stats],
    ['Rmerge'] + ['%.3f' %s.r_merge for s in stats],
    ['Rmeas'] + ['%.3f' %s.r_meas for s in stats],
    ['Rpim'] + ['%.3f' %s.r_pim for s in stats],
  ]

  if cc_half_method == 'sigma_tau':
    rows.append(['CC1/2'] + ['%.3f' %s.cc_one_half_sigma_tau for s in stats])
  else:
    rows.append(['CC1/2'] + ['%.3f' %s.cc_one_half for s in stats])
  rows = [[u'<strong>%s</strong>' %r[0]] + r[1:] for r in rows]

  overall_stats_table = [headers]
  overall_stats_table.extend(rows)

  symmetry_table_html = """
  <p>
    <b>Filename:</b> %s
    <br>
    <b>Unit cell:</b> %s
    <br>
    <b>Space group:</b> %s
  </p>
""" %(os.path.abspath(reader.file_name()),
      intensities.space_group_info().symbol_and_number(),
      str(intensities.unit_cell()))

  if params.anomalous:
    intensities = intensities.as_anomalous_array()
    batches = batches.as_anomalous_array()

  from xia2.Modules.PyChef2.PyChef import remove_batch_gaps
  new_batch_data = remove_batch_gaps(batches.data())
  new_batches = batches.customized_copy(data=new_batch_data)
  sc_vs_b = scales_vs_batch(scales, new_batches)
  rmerge_vs_b = rmerge_vs_batch(intensities, new_batches)

  intensities.setup_binner(n_bins=n_bins)

  merged_intensities = intensities.merge_equivalents().array()

  xtriage_success = []
  xtriage_warnings = []
  xtriage_danger = []
  if not intensities.space_group().is_centric():
    s = StringIO()
    pout = printed_output(out=s)
    from mmtbx.scaling.xtriage import xtriage_analyses
    from mmtbx.scaling.xtriage import master_params as xtriage_master_params
    xtriage_params = xtriage_master_params.fetch(sources=[]).extract()
    xtriage_params.scaling.input.xray_data.skip_sanity_checks = True
    xanalysis = xtriage_analyses(
      miller_obs=merged_intensities,
      unmerged_obs=intensities, text_out=pout,
      params=xtriage_params,
      )
    with open('xtriage.log', 'wb') as f:
      print >> f, s.getvalue()
    xs = StringIO()
    xout = xtriage_output(xs)
    xanalysis.show(out=xout)
    xout.flush()
    sub_header_to_out = xout._sub_header_to_out
    issues = xanalysis.summarize_issues()
    issues.show()
    nz_test = xanalysis.twin_results.nz_test
    l_test = xanalysis.twin_results.l_test

    wilson_scaling = xanalysis.wilson_scaling
    i = 0
    for issue in issues._issues:
        i += 1
        level, text, sub_header = issue
        summary = sub_header_to_out.get(sub_header, StringIO()).getvalue()
        summary = summary.replace('<', '&lt;').replace('>', '&gt;')
        d = {
          'level': level,
          'text': text,
          'summary': summary,
          'header': sub_header,
        }
        if level == 0: xtriage_success.append(d)
        elif level == 1: xtriage_warnings.append(d)
        elif level == 2: xtriage_danger.append(d)

  acentric = merged_intensities.select_acentric()
  centric = merged_intensities.select_centric()
  if acentric.size():
    acentric.setup_binner(n_bins=n_bins)
    second_moments_acentric = acentric.second_moment_of_intensities(use_binning=True)
  if centric.size():
    centric.setup_binner(n_bins=n_bins)
    second_moments_centric = centric.second_moment_of_intensities(use_binning=True)

  d_star_sq_bins = [
    (1/bin_stats.d_min**2) for bin_stats in merging_stats.bins]
  i_over_sig_i_bins = [
    bin_stats.i_over_sigma_mean for bin_stats in merging_stats.bins]
  if cc_half_method == 'sigma_tau':
    cc_one_half_bins = [
      bin_stats.cc_one_half_sigma_tau for bin_stats in merging_stats.bins]
    cc_one_half_critical_value_bins = [
      bin_stats.cc_one_half_sigma_tau_critical_value for bin_stats in merging_stats.bins]
  else:
    cc_one_half_bins = [
      bin_stats.cc_one_half for bin_stats in merging_stats.bins]
    cc_one_half_critical_value_bins = [
      bin_stats.cc_one_half_critical_value for bin_stats in merging_stats.bins]
  cc_anom_bins = [
    bin_stats.cc_anom for bin_stats in merging_stats.bins]
  cc_anom_critical_value_bins = [
    bin_stats.cc_anom_critical_value for bin_stats in merging_stats.bins]

  completeness_bins = [
    bin_stats.completeness for bin_stats in merging_stats.bins]
  anom_completeness_bins = [
    bin_stats.anom_completeness for bin_stats in merging_stats_anom.bins]
  multiplicity_bins = [
    bin_stats.mean_redundancy for bin_stats in merging_stats.bins]
  anom_multiplicity_bins = [
    bin_stats.mean_redundancy for bin_stats in merging_stats_anom.bins]

  from xia2.Modules.PyChef2 import PyChef
  if params.chef_min_completeness:
    d_min = PyChef.resolution_limit(
      mtz_file=args[0], min_completeness=params.chef_min_completeness, n_bins=8)
    print 'Estimated d_min for CHEF analysis: %.2f' %d_min
    sel = flex.bool(intensities.size(), True)
    d_spacings = intensities.d_spacings().data()
    sel &= d_spacings >= d_min
    intensities = intensities.select(sel)
    batches = batches.select(sel)
    if dose is not None:
      dose = dose.select(sel)

  if dose is None:
    dose = PyChef.batches_to_dose(batches.data(), params.dose)
  else:
    dose = dose.data()
  pychef_stats = PyChef.Statistics(intensities, dose)

  pychef_dict = pychef_stats.to_dict()

  def d_star_sq_to_d_ticks(d_star_sq, nticks):
    from cctbx import uctbx
    d_spacings = uctbx.d_star_sq_as_d(flex.double(d_star_sq))
    min_d_star_sq = min(d_star_sq)
    dstep = (max(d_star_sq) - min_d_star_sq)/nticks
    tickvals = list(min_d_star_sq + (i*dstep) for i in range(nticks))
    ticktext = ['%.2f' %(uctbx.d_star_sq_as_d(dsq)) for dsq in tickvals]
    return tickvals, ticktext

  tickvals, ticktext = d_star_sq_to_d_ticks(d_star_sq_bins, nticks=5)
  if not intensities.space_group().is_centric():
    tickvals_wilson, ticktext_wilson = d_star_sq_to_d_ticks(
      wilson_scaling.d_star_sq, nticks=5)
  second_moment_d_star_sq = []
  if acentric.size():
    second_moment_d_star_sq.extend(second_moments_acentric.binner.bin_centers(2))
  if centric.size():
    second_moment_d_star_sq.extend(second_moments_centric.binner.bin_centers(2))
  tickvals_2nd_moment, ticktext_2nd_moment = d_star_sq_to_d_ticks(
    second_moment_d_star_sq, nticks=5)

  json_data = {

    'completeness': {
      'data': [
        {
          'x': d_star_sq_bins,
          'y': completeness_bins,
          'type': 'scatter',
          'name': 'Completeness',
        },
        ({
          'x': d_star_sq_bins,
          'y': anom_completeness_bins,
          'type': 'scatter',
          'name': 'Anomalous completeness',
        } if not intensities.space_group().is_centric() else {}),
      ],
      'layout':{
        'title': 'Completeness vs resolution',
        'xaxis': {
          'title': u'Resolution (Å)',
          'tickvals': tickvals,
          'ticktext': ticktext,
        },
        'yaxis': {
          'title': 'Completeness',
        },
      },
    },

    'multiplicity_vs_resolution': {
      'data': [
        {
          'x': d_star_sq_bins,
          'y': multiplicity_bins,
          'type': 'scatter',
          'name': 'Multiplicity',
        },
        ({
          'x': d_star_sq_bins,
          'y': anom_multiplicity_bins,
          'type': 'scatter',
          'name': 'Anomalous multiplicity',
        } if not intensities.space_group().is_centric() else {}),
      ],
      'layout':{
        'title': 'Multiplicity vs resolution',
        'xaxis': {
          'title': u'Resolution (Å)',
          'tickvals': tickvals,
          'ticktext': ticktext,
        },
        'yaxis': {
          'title': 'Multiplicity',
        },
      },
    },

    'multiplicities': {
      'data': [
        {
          'x': multiplicities_acentric.keys(),
          'y': multiplicities_acentric.values(),
          'type': 'bar',
          'name': 'Acentric',
          'opacity': 0.75,
        },
        {
          'x': multiplicities_centric.keys(),
          'y': multiplicities_centric.values(),
          'type': 'bar',
          'name': 'Centric',
          'opacity': 0.75,
        },
      ],
      'layout': {
        'title': 'Distribution of multiplicities',
        'xaxis': {'title': 'Multiplicity'},
        'yaxis': {
          'title': 'Frequency',
          #'rangemode': 'tozero'
        },
        'bargap': 0,
        'barmode': 'overlay',
      },
    },

    'scale_rmerge_vs_batch': {
      'data': [
        {
          'x': sc_vs_b.batches,
          'y': sc_vs_b.data,
          'type': 'scatter',
          'name': 'Scale',
          'opacity': 0.75,
        },
        {
          'x': rmerge_vs_b.batches,
          'y': rmerge_vs_b.data,
          'yaxis': 'y2',
          'type': 'scatter',
          'name': 'Rmerge',
          'opacity': 0.75,
        },
      ],
      'layout': {
        'title': 'Scale and Rmerge vs batch',
        'xaxis': {'title': 'N'},
        'yaxis': {
          'title': 'Scale',
          'rangemode': 'tozero'
        },
        'yaxis2': {
          'title': 'Rmerge',
          'overlaying': 'y',
          'side': 'right',
          'rangemode': 'tozero'
        }
      },
    },

    'cc_one_half': {
      'data': [
        {
          'x': d_star_sq_bins, # d_star_sq
          'y': cc_one_half_bins,
          'type': 'scatter',
          'name': 'CC-half',
          'mode': 'lines',
          'line': {
            'color': 'rgb(31, 119, 180)',
          },
        },
        {
          'x': d_star_sq_bins, # d_star_sq
          'y': cc_one_half_critical_value_bins,
          'type': 'scatter',
          'name': 'CC-half critical value (p=0.01)',
          'line': {
            'color': 'rgb(31, 119, 180)',
            'dash': 'dot',
          },
        },
        ({
          'x': d_star_sq_bins, # d_star_sq
          'y': cc_anom_bins,
          'type': 'scatter',
          'name': 'CC-anom',
          'mode': 'lines',
          'line': {
            'color': 'rgb(255, 127, 14)',
          },
        } if not intensities.space_group().is_centric() else {}),
        ({
          'x': d_star_sq_bins, # d_star_sq
          'y': cc_anom_critical_value_bins,
          'type': 'scatter',
          'name': 'CC-anom critical value (p=0.01)',
          'mode': 'lines',
          'line': {
            'color': 'rgb(255, 127, 14)',
            'dash': 'dot',
          },
        } if not intensities.space_group().is_centric() else {}),
      ],
      'layout':{
        'title': 'CC-half vs resolution',
        'xaxis': {
          'title': u'Resolution (Å)',
          'tickvals': tickvals,
          'ticktext': ticktext,
        },
        'yaxis': {
          'title': 'CC-half',
          'range': [min(cc_one_half_bins + cc_anom_bins + [0]), 1]
          },
        },
    },

    'i_over_sig_i': {
      'data': [{
        'x': d_star_sq_bins, # d_star_sq
        'y': i_over_sig_i_bins,
        'type': 'scatter',
        'name': 'Scales vs batch',
      }],
      'layout': {
        'title': '<I/sig(I)> vs resolution',
        'xaxis': {
          'title': u'Resolution (Å)',
          'tickvals': tickvals,
          'ticktext': ticktext,
        },
        'yaxis': {
          'title': '<I/sig(I)>',
          'rangemode': 'tozero'
        },
      }
    },

    'second_moments': {
      'data': [
        ({
          'x': list(second_moments_acentric.binner.bin_centers(2)), # d_star_sq
          'y': second_moments_acentric.data[1:-1],
          'type': 'scatter',
          'name': '<I^2> acentric',
        } if acentric.size() else {}),
        ({
          'x': list(second_moments_centric.binner.bin_centers(2)), # d_star_sq
          'y': second_moments_centric.data[1:-1],
          'type': 'scatter',
          'name': '<I^2> centric',
          } if centric.size() else {})
      ],
      'layout': {
        'title': 'Second moment of I',
        'xaxis': {
          'title': u'Resolution (Å)',
          'tickvals': tickvals_2nd_moment,
          'ticktext': ticktext_2nd_moment,
        },
        'yaxis': {
          'title': '<I^2>',
          'rangemode': 'tozero'
        },
      }
    },

    'cumulative_intensity_distribution': {
      'data': [
        {
          'x': list(nz_test.z),
          'y': list(nz_test.ac_obs),
          'type': 'scatter',
          'name': 'Acentric observed',
          'mode': 'lines',
          'line': {
            'color': 'rgb(31, 119, 180)',
          },
        },
        {
          'x': list(nz_test.z),
          'y': list(nz_test.c_obs),
          'type': 'scatter',
          'name': 'Centric observed',
          'mode': 'lines',
          'line': {
            'color': 'rgb(255, 127, 14)',
          },
        },
        {
          'x': list(nz_test.z),
          'y': list(nz_test.ac_untwinned),
          'type': 'scatter',
          'name': 'Acentric theory',
          'mode': 'lines',
          'line': {
            'color': 'rgb(31, 119, 180)',
            'dash': 'dot',
          },
          'opacity': 0.8,
        },
        {
          'x': list(nz_test.z),
          'y': list(nz_test.c_untwinned),
          'type': 'scatter',
          'name': 'Centric theory',
          'mode': 'lines',
          'line': {
            'color': 'rgb(255, 127, 14)',
            'dash': 'dot',
          },
          'opacity': 0.8,
        },
      ],
      'layout': {
        'title': 'Cumulative intensity distribution',
        'xaxis': {
          'title': 'z',
          'range': (0, 1),
        },
        'yaxis': {
          'title': 'P(Z <= Z)',
          'range': (0, 1),
        },
      }
    } if not intensities.space_group().is_centric() else {},

    'l_test': {
      'data': [
        {
          'x': list(l_test.l_values),
          'y': list(l_test.l_cumul_untwinned),
          'type': 'scatter',
          'name': 'Untwinned',
          'mode': 'lines',
          'line': {
            'color': 'rgb(31, 119, 180)',
            'dash': 'dashdot',
          },
        },
        {
          'x': list(l_test.l_values),
          'y': list(l_test.l_cumul_perfect_twin),
          'type': 'scatter',
          'name': 'Perfect twin',
          'mode': 'lines',
          'line': {
            'color': 'rgb(31, 119, 180)',
            'dash': 'dot',
          },
          'opacity': 0.8,
        },
        {
          'x': list(l_test.l_values),
          'y': list(l_test.l_cumul),
          'type': 'scatter',
          'name': 'Observed',
          'mode': 'lines',
          'line': {
            'color': 'rgb(255, 127, 14)',
          },
        },
      ],
      'layout': {
        'title': 'L test (Padilla and Yeates)',
        'xaxis': {
          'title': '|l|',
          'range': (0, 1),
        },
        'yaxis': {
          'title': 'P(L >= l)',
          'range': (0, 1),
        },
      }
    } if not intensities.space_group().is_centric() else {},

    'wilson_intensity_plot': {
      'data': ([
        {
          'x': list(wilson_scaling.d_star_sq),
          'y': list(wilson_scaling.mean_I_obs_data),
          'type': 'scatter',
          'name': 'Observed',
        },
        {
          'x': list(wilson_scaling.d_star_sq),
          'y': list(wilson_scaling.mean_I_obs_theory),
          'type': 'scatter',
          'name': 'Expected',
        },
        {
          'x': list(wilson_scaling.d_star_sq),
          'y': list(wilson_scaling.mean_I_normalisation),
          'type': 'scatter',
          'name': 'Smoothed',
        }]),
      'layout': {
        'title': 'Wilson intensity plot',
        'xaxis': {
          'title': u'Resolution (Å)',
          'tickvals': tickvals_wilson,
          'ticktext': ticktext_wilson,
        },
        'yaxis': {
          'type': 'log',
          'title': 'Mean(I)',
          'rangemode': 'tozero',
        },
      },
    } if not intensities.space_group().is_centric() else {},
  }

  json_data.update(pychef_dict)

  import json

  resolution_graphs = OrderedDict(
    (k, json.dumps(json_data[k])) for k in
    ('cc_one_half', 'i_over_sig_i', 'second_moments', 'wilson_intensity_plot',
     'completeness', 'multiplicity_vs_resolution'))

  batch_graphs = OrderedDict(
    (k, json.dumps(json_data[k])) for k in
    ('scale_rmerge_vs_batch', 'completeness_vs_dose',
     'rcp_vs_dose', 'scp_vs_dose', 'rd_vs_batch_difference'))

  misc_graphs = OrderedDict(
    (k, json.dumps(json_data[k])) for k in
    ('cumulative_intensity_distribution', 'l_test', 'multiplicities'))

  misc_graphs.update(OrderedDict(
    ('multiplicity_%s' %axis, open(mult_json_files[axis], 'rb').read())
    for axis in ('h', 'k', 'l')))

  styles = {}
  for axis in ('h', 'k', 'l'):
    styles['multiplicity_%s' %axis] = 'square-plot'

  from jinja2 import Environment, ChoiceLoader, PackageLoader
  loader = ChoiceLoader([PackageLoader('xia2', 'templates'),
                         PackageLoader('dials', 'templates')])
  env = Environment(loader=loader)

  template = env.get_template('report.html')
  html = template.render(page_title='xia2 report',
                         filename=os.path.abspath(reader.file_name()),
                         space_group=intensities.space_group_info().symbol_and_number(),
                         unit_cell=str(intensities.unit_cell()),
                         xtriage_success=xtriage_success,
                         xtriage_warnings=xtriage_warnings,
                         xtriage_danger=xtriage_danger,
                         overall_stats_table=overall_stats_table,
                         merging_stats_table=merging_stats_table,
                         cc_half_significance_level=cc_half_significance_level,
                         resolution_graphs=resolution_graphs,
                         batch_graphs=batch_graphs,
                         misc_graphs=misc_graphs,
                         styles=styles)

  json_str = json.dumps(json_data)
  with open('xia2-report.json', 'wb') as f:
    print >> f, json_str

  with open('xia2-report.html', 'wb') as f:
    print >> f, html.encode('ascii', 'xmlcharrefreplace')

  return


if __name__ == '__main__':
  import sys
  run(sys.argv[1:])
