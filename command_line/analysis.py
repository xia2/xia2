from __future__ import division
from cctbx.array_family import flex
import math


# LIBTBX_SET_DISPATCHER_NAME dev.xia2.analysis

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
  intensities = intensities.customized_copy(indices=indices)
  batches = batches.customized_copy(indices=indices)

  range_min = params.range.min
  range_max = params.range.max
  range_width = params.range.width

  if params.anomalous:
    intensities = intensities.as_anomalous_array()
    batches = batches.as_anomalous_array()

  sc_vs_b = scales_vs_batch(scales, batches)
  rmerge_vs_b = rmerge_vs_batch(intensities, batches)

  intensities.setup_binner(reflections_per_bin=500)
  cc_one_half = intensities.cc_one_half(use_binning=True)
  i_over_sig_i = intensities.i_over_sig_i(use_binning=True)

  from mmtbx.scaling import twin_analyses
  twin_analysis = twin_analyses.twin_analyses(
    miller_array=intensities.merge_equivalents().array())

  nz_test = twin_analysis.nz_test

  from mmtbx.scaling import data_statistics
  wilson_scaling = data_statistics.wilson_scaling(
    miller_array=intensities, n_residues=200) # XXX default n_residues?

  acentric = intensities.select_acentric()
  centric = intensities.select_centric()
  acentric.setup_binner(n_bins=20)
  centric.setup_binner(n_bins=20)
  second_moments_acentric = acentric.second_moment_of_intensities(use_binning=True)
  second_moments_centric = centric.second_moment_of_intensities(use_binning=True)

  from xia2.Modules.PyChef2 import PyChef
  pychef_stats = PyChef.Statistics(intensities, batches.data())

  pychef_dict = pychef_stats.to_dict()

  json_data = {

    'scale_rmerge_vs_batch': {
      'data': [
        {
          'x': sc_vs_b.batches,
          'y': sc_vs_b.data,
          'type': 'scatter',
          'name': 'Scales vs batch',
        },
        {
          'x': rmerge_vs_b.batches,
          'y': rmerge_vs_b.data,
          'yaxis': 'y2',
          'type': 'scatter',
          'name': 'Rmerge vs batch',
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
      'data': [{
        'x': list(cc_one_half.binner.bin_centers(2)), # d_star_sq
        'y': cc_one_half.data[1:-1],
        'type': 'scatter',
        'name': 'Scales vs batch',
      }],
      'layout':{
        'title': 'CC-half vs resolution',
        'xaxis': {'title': 'd_star_sq'},
        'yaxis': {
          'title': 'CC-half',
          'rangemode': 'tozero',
          'range': [0, 1]
          },
        },
    },

    'i_over_sig_i': {
      'data': [{
        'x': list(i_over_sig_i.binner.bin_centers(2)), # d_star_sq
        'y': i_over_sig_i.data[1:-1],
        'type': 'scatter',
        'name': 'Scales vs batch',
      }],
      'layout': {
        'title': '<I/sig(I)> vs resolution',
        'xaxis': {'title': 'd_star_sq'},
        'yaxis': {
          'title': '<I/sig(i)>',
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
        'xaxis': {'title': 'd_star_sq'},
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
          'name': '<I> via binning',
        },
        {
          'x': list(wilson_scaling.d_star_sq),
          'y': list(wilson_scaling.mean_I_obs_theory),
          'type': 'scatter',
          'name': '<I> expected',
        },
        {
          'x': list(wilson_scaling.d_star_sq),
          'y': list(wilson_scaling.mean_I_normalisation),
          'type': 'scatter',
          'name': '<I> smooth approximation',
        },
      ],
      'layout': {
        'title': 'Wilson intensity plot',
        'xaxis': {'title': 'Resolution'},
        'yaxis': {
          'title': '<I>',
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
</head>

<body>
  <div id="scale_rmerge" style="width: 600px; height: 400px;"></div>
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

""" %javascript

  with open('xia2-summary.json', 'wb') as f:
    print >> f, json.dumps(json_data, indent=2)

  with open('xia2-summary.html', 'wb') as f:
    print >> f, html

  return


if __name__ == '__main__':
  import sys
  run(sys.argv[1:])
