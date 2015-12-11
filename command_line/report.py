# -*- coding: utf-8 -*-

from __future__ import division
from cctbx.array_family import flex
import math
import os


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
  dose = None

  reader = any_reflection_file(args[0])
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

  from iotbx import merging_statistics
  merging_stats = merging_statistics.dataset_statistics(
    intensities, n_bins=n_bins)

  merging_acentric = intensities.select_acentric().merge_equivalents()
  merging_centric = intensities.select_centric().merge_equivalents()

  multiplicities_acentric = {}
  multiplicities_centric = {}

  for x in sorted(set(merging_acentric.redundancies().data())):
    multiplicities_acentric[x] = merging_acentric.redundancies().data().count(x)
  for x in sorted(set(merging_centric.redundancies().data())):
    multiplicities_centric[x] = merging_centric.redundancies().data().count(x)

  headers = [u'Resolution (Å)', 'N(obs)', 'N(unique)', 'Multiplicity', 'Completeness',
             'Mean(I)', 'Mean(I/sigma)', 'Rmerge', 'Rmeas', 'Rpim', 'CC1/2', 'CCano']
  rows = []
  for bin_stats in merging_stats.bins:
    row = ['%.2f - %.2f' %(bin_stats.d_max, bin_stats.d_min),
           bin_stats.n_obs, bin_stats.n_uniq, '%.2f' %bin_stats.mean_redundancy,
           '%.2f' %(100*bin_stats.completeness), '%.1f' %bin_stats.i_mean,
           '%.1f' %bin_stats.i_over_sigma_mean, '%.3f' %bin_stats.r_merge,
           '%.3f' %bin_stats.r_meas, '%.3f' %bin_stats.r_pim,
           '%.3f' %bin_stats.cc_one_half, '%.3f' %bin_stats.cc_anom]
    rows.append(row)

  from xia2.lib.tabulate import tabulate
  merging_stats_table_html = tabulate(rows, headers, tablefmt='html')
  merging_stats_table_html = merging_stats_table_html.replace(
    '<table>', '<table class="table table-hover table-condensed">')

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
    ['CC1/2'] + ['%.3f' %s.cc_one_half for s in stats],
  ]
  rows = [[u'<strong>%s</strong>' %r[0]] + r[1:] for r in rows]

  overall_stats_table_html = tabulate(rows, headers, tablefmt='html')
  overall_stats_table_html = overall_stats_table_html.replace(
    '<table>', '<table class="table table-hover table-condensed">')

  #headers = ['Crystal symmetry', '']
  #rows = [
    #[u'Unit cell: a (Å)', '%.3f' %unit_cell_params[0]],
    #[u'b (Å)', '%.3f' %unit_cell_params[1]],
    #[u'c (Å)', '%.3f' %unit_cell_params[2]],
    #[u'α (°)', '%.3f' %unit_cell_params[3]],
    #[u'β (°)', '%.3f' %unit_cell_params[4]],
    #[u'γ (°)', '%.3f' %unit_cell_params[5]],
    #['Space group', intensities.space_group_info().symbol_and_number()],
  #]

  #symmetry_table_html = tabulate(rows, headers, tablefmt='html')
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
  from mmtbx.scaling import twin_analyses
  normalised_intensities = twin_analyses.wilson_normalised_intensities(
    miller_array=merged_intensities)
  nz_test = twin_analyses.n_z_test(
    normalised_acentric=normalised_intensities.acentric,
    normalised_centric=normalised_intensities.centric)

  from mmtbx.scaling import data_statistics
  if not intensities.space_group().is_centric():
    wilson_scaling = data_statistics.wilson_scaling(
      miller_array=merged_intensities, n_residues=200) # XXX default n_residues?

  acentric = intensities.select_acentric()
  centric = intensities.select_centric()
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
  cc_one_half_bins = [
    bin_stats.cc_one_half for bin_stats in merging_stats.bins]
  cc_anom_bins = [
    bin_stats.cc_anom for bin_stats in merging_stats.bins]

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
        },
        ({
          'x': d_star_sq_bins, # d_star_sq
          'y': cc_anom_bins,
          'type': 'scatter',
          'name': 'CC-anom',
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
        'xaxis': {'title': 'z'},
        'yaxis': {
          'title': 'P(Z <= Z)',
          'rangemode': 'tozero'
        },
      }
    },

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
        }] if not intensities.space_group().is_centric() else []),
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
    },
  }

  json_data.update(pychef_dict)

  import json
  json_str = json.dumps(json_data)

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
  'completeness', graphs.completeness_vs_dose.data,
  graphs.completeness_vs_dose.layout);
Plotly.newPlot('rcp', graphs.rcp_vs_dose.data, graphs.rcp_vs_dose.layout);
Plotly.newPlot('scp', graphs.scp_vs_dose.data, graphs.scp_vs_dose.layout);
Plotly.newPlot(
  'rd', graphs.rd_vs_batch_difference.data,
  graphs.rd_vs_batch_difference.layout);

""" %(json_str)

  html = """
<head>

<!-- Plotly.js -->
<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>

<meta name="viewport" content="width=device-width, initial-scale=1" charset="UTF-8">
<link rel="stylesheet" href="http://maxcdn.bootstrapcdn.com/bootstrap/3.3.5/css/bootstrap.min.css">
<script src="https://ajax.googleapis.com/ajax/libs/jquery/1.11.3/jquery.min.js"></script>
<script src="http://maxcdn.bootstrapcdn.com/bootstrap/3.3.5/js/bootstrap.min.js"></script>

<style type="text/css">

body {
  /*font-family: Helmet, Freesans, Helvetica, Arial, sans-serif;*/
  margin: 8px;
  min-width: 240px;
  margin-left: 5%%;
  margin-right: 5%%;
}

.plot {
  float: left;
  width: 600px;
  height: 400px;
  margin-bottom: 20px;
}

</style>

</head>

<body>

<div class="page-header">
  <h1>xia2 report</h1>
</div>

<div >
  <h2>Merging statistics</h2>
  %s
  <div class="panel-group">
    <div class="panel panel-default">
      <div class="panel-heading" data-toggle="collapse" href="#collapse1">
        <h4 class="panel-title">
          <a>Overall</a>
        </h4>
      </div>
      <div id="collapse1" class="panel-collapse collapse in">
        <div class="panel-body">
          <div class="table-responsive" style="width: 800px">
            %s
          </div>
        </div>
        <!-- <div class="panel-footer"></div> -->
      </div>
    </div>
    <div class="panel panel-default">
      <div class="panel-heading" data-toggle="collapse" href="#collapse2">
        <h4 class="panel-title">
          <a>Resolution shells</a>
        </h4>
      </div>
      <div id="collapse2" class="panel-collapse collapse">
        <div class="panel-body">
          <div class="table-responsive">
            %s
          </div>
        </div>
        <!-- <div class="panel-footer"></div> -->
      </div>
    </div>
  </div>
</div>

<div >
  <h2>Analysis plots</h2>
  <div class="panel-group">
    <div class="panel panel-default">
      <div class="panel-heading" data-toggle="collapse" href="#collapse3">
        <h4 class="panel-title">
          <a>Analysis by resolution</a>
        </h4>
      </div>
      <div id="collapse3" class="panel-collapse collapse">
        <div class="panel-body">

          <div class="container-fluid">
            <div class="col-xs-6 col-sm-6 col-md-4 plot" id="cc_one_half"></div>
            <div class="col-xs-6 col-sm-6 col-md-4 plot" id="mean_i_over_sig_i"></div>
            <div class="col-xs-6 col-sm-6 col-md-4 plot" id="second_moments"></div>
            <div class="col-xs-6 col-sm-6 col-md-4 plot" id="wilson_plot"></div>
          </div>

        </div>
        <!-- <div class="panel-footer"></div> -->
      </div>
    </div>
    <div class="panel panel-default">
      <div class="panel-heading" data-toggle="collapse" href="#collapse4">
        <h4 class="panel-title">
          <a>Analysis by batch</a>
        </h4>
      </div>
      <div id="collapse4" class="panel-collapse collapse">
        <div class="panel-body">

          <div class="container-fluid">
            <div class="col-xs-6 col-sm-6 col-md-4 plot" id="scale_rmerge"></div>
            <div class="col-xs-6 col-sm-6 col-md-4 plot" id="completeness"></div>
            <div class="col-xs-6 col-sm-6 col-md-4 plot" id="rcp"></div>
            <div class="col-xs-6 col-sm-6 col-md-4 plot" id="scp"></div>
            <div class="col-xs-6 col-sm-6 col-md-4 plot" id="rd"></div>
          </div>

        </div>
        <!-- <div class="panel-footer"></div> -->
      </div>
    </div>
    <div class="panel panel-default">
      <div class="panel-heading" data-toggle="collapse" href="#collapse5">
        <h4 class="panel-title">
          <a>Miscellaneous</a>
        </h4>
      </div>
      <div id="collapse5" class="panel-collapse collapse">
        <div class="panel-body">

          <div class="container-fluid">
            <div class="col-xs-6 col-sm-6 col-md-4 plot" id="multiplicities"></div>
            <div class="col-xs-6 col-sm-6 col-md-4 plot" id="cumulative_intensity"></div>
          </div>

        </div>
        <!-- <div class="panel-footer"></div> -->
      </div>
    </div>
  </div>
</div>

<script>
%s
</script>
</body>

""" %(symmetry_table_html, overall_stats_table_html, merging_stats_table_html, javascript)

  with open('xia2-report.json', 'wb') as f:
    print >> f, json_str

  with open('xia2-report.html', 'wb') as f:
    print >> f, html.encode('ascii', 'xmlcharrefreplace')

  return


if __name__ == '__main__':
  import sys
  run(sys.argv[1:])
