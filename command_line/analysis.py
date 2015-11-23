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

  json_data = {
    'scales_vs_batch': {
      'x': sc_vs_b.batches,
      'y': sc_vs_b.data,
      'type': 'scatter',
      'name': 'Scales vs batch',
    },
    'rmerge_vs_batch': {
      'x': rmerge_vs_b.batches,
      'y': rmerge_vs_b.data,
      'type': 'scatter',
      'name': 'Rmerge vs batch',
    },
    'cc_one_half': {
      'x': list(cc_one_half.binner.bin_centers(2)), # d_star_sq
      'y': cc_one_half.data[1:-1],
      'type': 'scatter',
      'name': 'Scales vs batch',
    },
    'i_over_sig_i': {
      'x': list(i_over_sig_i.binner.bin_centers(2)), # d_star_sq
      'y': i_over_sig_i.data[1:-1],
      'type': 'scatter',
      'name': 'Scales vs batch',
    },
    'second_moments_acentric': {
      'x': list(second_moments_acentric.binner.bin_centers(2)), # d_star_sq
      'y': second_moments_acentric.data[1:-1],
      'type': 'scatter',
      'name': '<I^2> acentric',
    },
    'second_moments_centric': {
      'x': list(second_moments_centric.binner.bin_centers(2)), # d_star_sq
      'y': second_moments_centric.data[1:-1],
      'type': 'scatter',
      'name': '<I^2> centric',
    },
    'nz_test_acentric_obs': {
      'x': list(nz_test.z),
      'y': list(nz_test.ac_obs),
      'type': 'scatter',
      'name': 'Acentric observed',
    },
    'nz_test_centric_obs': {
      'x': list(nz_test.z),
      'y': list(nz_test.c_obs),
      'type': 'scatter',
      'name': 'Centric observed',
    },
    'nz_test_acentric_untwinned': {
      'x': list(nz_test.z),
      'y': list(nz_test.ac_untwinned),
      'type': 'scatter',
      'name': 'Acentric untwinned',
    },
    'nz_test_centric_untwinned': {
      'x': list(nz_test.z),
      'y': list(nz_test.c_untwinned),
      'type': 'scatter',
      'name': 'Centric untwinned',
    },
    'wilson_mean_I_obs_data': {
      'x': list(wilson_scaling.d_star_sq),
      'y': list(wilson_scaling.mean_I_obs_data),
      'type': 'scatter',
      'name': '<I> via binning',
    },
    'wilson_mean_I_obs_theory': {
      'x': list(wilson_scaling.d_star_sq),
      'y': list(wilson_scaling.mean_I_obs_theory),
      'type': 'scatter',
      'name': '<I> expected',
    },
    'wilson_mean_I_normalisation': {
      'x': list(wilson_scaling.d_star_sq),
      'y': list(wilson_scaling.mean_I_normalisation),
      'type': 'scatter',
      'name': '<I> smooth approximation',
    },

  }

  import json

  javascript = """
var jsonObject = %s

jsonObject.rmerge_vs_batch.yaxis = 'y2';

var layout_scale_rmerge = {
  title: 'Scale and Rmerge vs Batch',
  xaxis: {title: 'Batch'},
  yaxis: {
    title: 'Scale',
    rangemode: 'tozero'
  },
  yaxis2: {
    title: 'Rmerge',
    //titlefont: {color: 'rgb(148, 103, 189)'},
    //tickfont: {color: 'rgb(148, 103, 189)'},
    overlaying: 'y',
    side: 'right',
    rangemode: 'tozero'
  }
};

var layout_cc_one_half  = {
  title: 'CC-half vs resolution',
  xaxis: {title: 'd_star_sq'},
  yaxis: {
    title: 'CC-half',
    rangemode: 'tozero',
    range: [0, 1]
  },
};

var layout_mean_i_over_sig_i = {
  title: '<I/sig(I)> vs resolution',
  xaxis: {title: 'd_star_sq'},
  yaxis: {
    title: '<I/sig(i)>',
    rangemode: 'tozero'
  },
};

var layout_second_moments = {
  title: 'Second moment of I',
  xaxis: {title: 'd_star_sq'},
  yaxis: {
    title: '<I^2>',
    rangemode: 'tozero'
  },
};

var layout_cumulative_intensity = {
  title: 'Cumulative intensity distribution',
  xaxis: {title: 'z'},
  yaxis: {
    title: 'P(Z <= Z)',
    rangemode: 'tozero'
  },
};

var layout_wilson_plot = {
  title: 'Wilson intensity plot',
  xaxis: {title: 'Resolution'},
  yaxis: {
    title: '<I>',
    rangemode: 'tozero'
  },
};

var data_scale_rmerge = [jsonObject.scales_vs_batch, jsonObject.rmerge_vs_batch];
var data_cc_one_half = [jsonObject.cc_one_half];
var data_mean_i_over_sig_i = [jsonObject.i_over_sig_i];
var data_cumulative_intensity = [
  jsonObject.nz_test_acentric_obs, jsonObject.nz_test_centric_obs,
  jsonObject.nz_test_acentric_untwinned, jsonObject.nz_test_centric_untwinned
];
var data_wilson_plot = [
  jsonObject.wilson_mean_I_normalisation, jsonObject.wilson_mean_I_obs_data,
  jsonObject.wilson_mean_I_obs_theory
];
var data_second_moments = [jsonObject.second_moments_acentric, jsonObject.second_moments_centric];


Plotly.newPlot('scale_rmerge', data_scale_rmerge, layout_scale_rmerge);
Plotly.newPlot('cc_one_half ', data_cc_one_half , layout_cc_one_half );
Plotly.newPlot('mean_i_over_sig_i', data_mean_i_over_sig_i, layout_mean_i_over_sig_i);
Plotly.newPlot('second_moments', data_second_moments, layout_second_moments);
Plotly.newPlot('cumulative_intensity', data_cumulative_intensity, layout_cumulative_intensity);
Plotly.newPlot('wilson_plot', data_wilson_plot, layout_wilson_plot);

""" %(json.dumps(json_data, indent=2))

  html = """
<head>
  <!-- Plotly.js -->
   <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
</head>

<body>
  <div id="scale_rmerge" style="width: 600px; height: 400px;"></div>
  <div id="cc_one_half " style="width: 600px; height: 400px;"></div>
  <div id="mean_i_over_sig_i" style="width: 600px; height: 400px;"></div>
  <div id="second_moments" style="width: 600px; height: 400px;"></div>
  <div id="cumulative_intensity" style="width: 600px; height: 400px;"></div>
  <div id="wilson_plot" style="width: 600px; height: 400px;"></div>
  <script>
  %s
  </script>
</body>

""" %javascript

  print html
  print

  return

  #var jsonObject = {"keys": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26], "data": {"Mean scale factor": [1.0553385803332695, 1.0498718593015248, 1.0484244232653173, 1.0485806755228786, 1.0509623794879728, 1.0524284719592996, 1.0560513216120595, 1.0616094748962102, 1.0635865819865258, 1.0647706492757472, 1.070631959632859, 1.0761241659119323, 1.084048362359768, 1.091362368267366, 1.0925923331336138, 1.10134503981913, 1.1143265664577484, 1.120449450091168, 1.1278913484113282, 1.136045604735404, 1.132989675596808, 1.1346322589555744, 1.1411085876854024, 1.1403497522003985, 1.1561064077492675, 1.1789623670910128]}}

  #var chart = c3.generate({
    #data: {
      #json: jsonObject.data
      #},
    #axis: {
      #x: {
        #type: 'category',
        #categories: jsonObject.keys
      #}
    #}
  #});

  #print json.dumps(scales_vs_batch_data, indent=2)
  #print
  #print json.dumps(rmerge_vs_batch_data, indent=2)
  #print
  #print json.dumps(json_data, indent=2)


  from matplotlib import pyplot
  pyplot.plot(sc_vs_b.batches, sc_vs_b.data)
  ylim = pyplot.ylim()
  pyplot.ylim(0, ylim[1])
  pyplot.xlabel("Batch")
  pyplot.ylabel("Mean scale factor")
  pyplot.show()
  pyplot.clf()

  pyplot.plot(rmerge_vs_b.batches, rmerge_vs_b.data)
  ylim = pyplot.ylim()
  pyplot.ylim(0, ylim[1])
  pyplot.xlabel("Batch")
  pyplot.ylabel("Rmerge")
  pyplot.show()
  pyplot.clf()




  if len(params.batch):
    dose = flex.double(batches.size(), -1)
    batch_data = batches.data()
    for batch in params.batch:
      start = batch.dose_start
      step = batch.dose_step
      for i in range(batch.range[0], batch.range[1]+1):
        # inclusive range
        dose.set_selected(batch_data == i, start + step * (i-batch.range[0]))
  else:
    dose = batches.data()

  sel = dose > -1
  intensities = intensities.select(sel)
  dose = dose.select(sel)

  #if params.d_min or params.d_max:
    #sel = flex.bool(intensities.size(), True)
    #d_spacings = intensities.d_spacings().data()
    #if params.d_min:
      #sel &= d_spacings >= params.d_min
    #if params.d_max:
      #sel &= d_spacings <= params.d_max
    #intensities = intensities.select(sel)
    #dose = dose.select(sel)

  #stats = Statistics(intensities, dose, n_bins=params.resolution_bins,
                     #range_min=params.range.min, range_max=params.range.max,
                     #range_width=params.range.width)

  #stats.print_completeness_vs_dose()
  #stats.print_rcp_vs_dose()
  #stats.print_scp_vs_dose()
  #stats.print_rd_vs_dose()


if __name__ == '__main__':
  import sys
  run(sys.argv[1:])
