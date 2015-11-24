# LIBTBX_SET_DISPATCHER_NAME dev.xia2.analysis

from __future__ import division
from cctbx.array_family import flex
import math


from xia2.Modules.Analysis import *

def run(args):
  from iotbx.reflection_file_reader import any_reflection_file

  from xia2.Modules.Analysis import phil_scope
  interp = phil_scope.command_line_argument_interpreter()
  params, unhandled = interp.process_and_fetch(
    args, custom_processor='collect_remaining')
  params = params.extract()
  n_bins = params.resolution_bins

  args = unhandled

  intensities = None
  batches = None
  scales = None

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
    elif ma.info().labels == ['SCALEUSED']:
      scales = ma

  assert intensities is not None
  assert batches is not None
  mtz_object = reader.file_content()

  indices = mtz_object.extract_original_index_miller_indices()
  intensities = intensities.customized_copy(
    indices=indices, info=intensities.info())
  batches = batches.customized_copy(indices=indices, info=batches.info())

  from iotbx import merging_statistics
  merging_stats = merging_statistics.dataset_statistics(
    intensities, n_bins=n_bins)
  #merging_stats.show()
  #merging_stats.show_estimated_cutoffs()

  headers = ['d_max', 'd_min', 'N(obs)', 'N(unique)', 'Multiplicity', 'Completeness',
             'Mean(I)', 'Mean(I/sigma)', 'Rmerge', 'Rmeas', 'Rpim', 'CC1/2', 'CCano']
  rows = []
  for bin_stats in merging_stats.bins:
    row = ['%.2f' %bin_stats.d_max, '%.2f' %bin_stats.d_min,
           bin_stats.n_obs, bin_stats.n_uniq, '%.2f' %bin_stats.mean_redundancy,
           '%.2f' %(100*bin_stats.completeness), '%.1f' %bin_stats.i_mean,
           '%.1f' %bin_stats.i_over_sigma_mean, '%.3f' %bin_stats.r_merge,
           '%.3f' %bin_stats.r_meas, '%.3f' %bin_stats.r_pim,
           '%.3f' %bin_stats.cc_one_half, '%.3f' %bin_stats.cc_anom]
    rows.append(row)

  from xia2.lib.tabulate import tabulate
  merging_stats_table_html = tabulate(rows, headers, tablefmt='html')

  if params.anomalous:
    intensities = intensities.as_anomalous_array()
    batches = batches.as_anomalous_array()

  sc_vs_b = scales_vs_batch(scales, batches)
  rmerge_vs_b = rmerge_vs_batch(intensities, batches)

  intensities.setup_binner(n_bins=n_bins)
  #cc_one_half = intensities.cc_one_half(use_binning=True)
  #i_over_sig_i = intensities.i_over_sig_i(use_binning=True)

  merged_intensities = intensities.merge_equivalents().array()
  from mmtbx.scaling import twin_analyses
  twin_analysis = twin_analyses.twin_analyses(miller_array=merged_intensities)

  nz_test = twin_analysis.nz_test

  from mmtbx.scaling import data_statistics
  wilson_scaling = data_statistics.wilson_scaling(
    miller_array=merged_intensities, n_residues=200) # XXX default n_residues?

  acentric = intensities.select_acentric()
  centric = intensities.select_centric()
  acentric.setup_binner(n_bins=n_bins)
  centric.setup_binner(n_bins=n_bins)
  second_moments_acentric = acentric.second_moment_of_intensities(use_binning=True)
  second_moments_centric = centric.second_moment_of_intensities(use_binning=True)

  d_star_sq_bins = [
    (1/bin_stats.d_min**2) for bin_stats in merging_stats.bins]
  i_over_sig_i_bins = [
    bin_stats.i_over_sigma_mean for bin_stats in merging_stats.bins]
  cc_one_half_bins = [
    bin_stats.cc_one_half for bin_stats in merging_stats.bins]
  cc_anom_bins = [
    bin_stats.cc_anom for bin_stats in merging_stats.bins]

  from xia2.Modules.PyChef2 import PyChef
  pychef_stats = PyChef.Statistics(intensities, batches.data())

  pychef_dict = pychef_stats.to_dict()

  json_data = {

    'multiplicities': {
      'data': [
        {
          'x': merging_stats.overall.redundancies.keys(),
          'y': merging_stats.overall.redundancies.values(),
          'type': 'bar',
          'name': 'Multiplicities',
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
      },
    },

    'scale_rmerge_vs_batch': {
      'data': [
        {
          'x': sc_vs_b.batches,
          'y': sc_vs_b.data,
          'type': 'scatter',
          'name': 'Scale',
        },
        {
          'x': rmerge_vs_b.batches,
          'y': rmerge_vs_b.data,
          'yaxis': 'y2',
          'type': 'scatter',
          'name': 'Rmerge',
        },
      ],
      'layout': {
        'title': 'Scale and Rmerge vs Batch',
        'xaxis': {'title': 'Batch'},
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
        },
        {
          'x': d_star_sq_bins, # d_star_sq
          'y': cc_anom_bins,
          'type': 'scatter',
          'name': 'CC-anom',
        },
      ],
      'layout':{
        'title': 'CC-half vs resolution',
        'xaxis': {'title': 'sin theta / lambda'},
        'yaxis': {
          'title': 'CC-half',
          'rangemode': 'tozero',
          'range': [0, 1]
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
        'xaxis': {'title': 'sin theta / lambda'},
        'yaxis': {
          'title': '<I/sig(I)>',
          'rangemode': 'tozero'
        },
      }
    },

    'second_moments': {
      'data': [
        {
          'x': list(second_moments_acentric.binner.bin_centers(2)), # d_star_sq
          'y': second_moments_acentric.data[1:-1],
          'type': 'scatter',
          'name': '<I^2> acentric',
        },
        {
        'x': list(second_moments_centric.binner.bin_centers(2)), # d_star_sq
        'y': second_moments_centric.data[1:-1],
        'type': 'scatter',
        'name': '<I^2> centric',
        },
      ],
      'layout': {
        'title': 'Second moment of I',
        'xaxis': {'title': 'sin theta / lambda'},
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
        },
        {
          'x': list(nz_test.z),
          'y': list(nz_test.c_obs),
          'type': 'scatter',
          'name': 'Centric observed',
        },
        {
          'x': list(nz_test.z),
          'y': list(nz_test.ac_untwinned),
          'type': 'scatter',
          'name': 'Acentric untwinned',
        },
        {
          'x': list(nz_test.z),
          'y': list(nz_test.c_untwinned),
          'type': 'scatter',
          'name': 'Centric untwinned',
        },
      ],
      'layout': {
        'title': 'Cumulative intensity distribution',
        'xaxis': {'title': 'z'},
        'yaxis': {
          'title': 'P(Z <= Z)',
          'rangemode': 'tozero'
        },
      }
    },

    'wilson_intensity_plot': {
      'data': [
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
        },
      ],
      'layout': {
        'title': 'Wilson intensity plot',
        'xaxis': {'title': 'sin theta / lambda'},
        'yaxis': {
          'title': 'Mean(I)',
          'rangemode': 'tozero',
        },
      },
    },

  }

  json_data.update(pychef_dict)

  import json
  javascript = """
var graphs = %s

Plotly.newPlot(
  'scale_rmerge', graphs.scale_rmerge_vs_batch.data,
  graphs.scale_rmerge_vs_batch.layout);
Plotly.newPlot(
  'multiplicities', graphs.multiplicities.data, graphs.multiplicities.layout);
Plotly.newPlot(
  'cc_one_half', graphs.cc_one_half.data, graphs.cc_one_half.layout);
Plotly.newPlot(
  'mean_i_over_sig_i', graphs.i_over_sig_i.data,
  graphs.i_over_sig_i.layout);
Plotly.newPlot(
  'second_moments', graphs.second_moments.data,
  graphs.second_moments.layout);
Plotly.newPlot(
  'cumulative_intensity', graphs.cumulative_intensity_distribution.data,
  graphs.cumulative_intensity_distribution.layout);
Plotly.newPlot(
  'wilson_plot', graphs.wilson_intensity_plot.data,
  graphs.wilson_intensity_plot.layout);
Plotly.newPlot(
  'completeness', graphs.completeness_vs_batch.data,
  graphs.completeness_vs_batch.layout);
Plotly.newPlot('rcp', graphs.rcp_vs_batch.data, graphs.rcp_vs_batch.layout);
Plotly.newPlot('scp', graphs.scp_vs_batch.data, graphs.scp_vs_batch.layout);
Plotly.newPlot(
  'rd', graphs.rd_vs_batch_difference.data,
  graphs.rd_vs_batch_difference.layout);

""" %(json.dumps(json_data, indent=2))

  html = """
<head>
  <!-- Plotly.js -->
   <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
   <script type='text/javascript' src='https://cdn.mathjax.org/mathjax/latest/MathJax.js?config=TeX-AMS-MML_HTMLorMML%%2CSafe.js&ver=4.1'></script>
</head>

<body>
  <div id="merging_stats">%s</div>
  <div id="scale_rmerge" style="width: 600px; height: 400px;"></div>
  <div id="multiplicities" style="width: 600px; height: 400px;"></div>
  <div id="cc_one_half" style="width: 600px; height: 400px;"></div>
  <div id="mean_i_over_sig_i" style="width: 600px; height: 400px;"></div>
  <div id="second_moments" style="width: 600px; height: 400px;"></div>
  <div id="cumulative_intensity" style="width: 600px; height: 400px;"></div>
  <div id="wilson_plot" style="width: 600px; height: 400px;"></div>
  <div id="completeness" style="width: 600px; height: 400px;"></div>
  <div id="rcp" style="width: 600px; height: 400px;"></div>
  <div id="scp" style="width: 600px; height: 400px;"></div>
  <div id="rd" style="width: 600px; height: 400px;"></div>
  <script>
  %s
  </script>
</body>

""" %(merging_stats_table_html, javascript)

  with open('xia2-report.json', 'wb') as f:
    print >> f, json.dumps(json_data, indent=2)

  with open('xia2-report.html', 'wb') as f:
    print >> f, html

  return


if __name__ == '__main__':
  import sys
  run(sys.argv[1:])
