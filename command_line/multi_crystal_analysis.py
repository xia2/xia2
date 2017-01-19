# LIBTBX_SET_DISPATCHER_NAME xia2.multi_crystal_analysis

import sys
import os
import math
import time
import exceptions
import traceback

# Needed to make xia2 imports work correctly
import libtbx.load_env
from xia2.Handlers.Streams import Chatter, Debug

from xia2.Handlers.Files import cleanup
from xia2.Handlers.Citations import Citations
from xia2.Handlers.Environment import Environment, df
from xia2.lib.bits import auto_logfiler

from xia2.XIA2Version import Version

from xia2.Applications.xia2 import check_environment
from xia2.Applications.xia2 import get_command_line, write_citations, help
from xia2.lib.tabulate import tabulate

from scitbx.array_family import flex

# try to get scipy set up right...
from xia2.Modules.MultiCrystalAnalysis import get_scipy
get_scipy()

def multi_crystal_analysis(stop_after=None):
  '''Actually process something...'''

  assert os.path.exists('xia2.json')
  from xia2.Schema.XProject import XProject
  xinfo = XProject.from_json(filename='xia2.json')

  crystals = xinfo.get_crystals()
  for crystal_id, crystal in crystals.iteritems():
    cwd = os.path.abspath(os.curdir)
    working_directory = Environment.generate_directory(
      [crystal.get_name(), 'analysis'])
    os.chdir(working_directory)

    scaler = crystal._get_scaler()

    #epoch_to_si = {}
    epoch_to_batches = {}
    epoch_to_integrated_intensities = {}
    epoch_to_sweep_name = {}
    epoch_to_experiments = {}

    try:
      epochs = scaler._sweep_information.keys()
      for epoch in epochs:
        si = scaler._sweep_information[epoch]
        epoch_to_batches[epoch] = si['batches']
        epoch_to_integrated_intensities[epoch] = si['corrected_intensities']
        epoch_to_sweep_name[epoch] = si['sname']
        intgr = si['integrater']
        epoch_to_experiments[epoch] = intgr.get_integrated_experiments()

    except AttributeError, e:
      epochs = scaler._sweep_handler.get_epochs()
      for epoch in epochs:
        si = scaler._sweep_handler.get_sweep_information(epoch)
        epoch_to_batches[epoch] = si.get_batches()
        epoch_to_integrated_intensities[epoch] = si.get_reflections()
        epoch_to_sweep_name[epoch] = si.get_sweep_name()
        intgr = si.get_integrater()
        epoch_to_experiments[epoch] = intgr.get_integrated_experiments()

    from xia2.Wrappers.Dials.StereographicProjection import StereographicProjection
    sp_json_files = {}
    for hkl in ((1,0,0), (0,1,0), (0,0,1)):
      sp = StereographicProjection()
      auto_logfiler(sp)
      sp.set_working_directory(working_directory)
      for experiments in epoch_to_experiments.values():
        sp.add_experiments(experiments)
      sp.set_hkl(hkl)
      sp.run()
      sp_json_files[hkl] = sp.get_json_filename()

    unmerged_mtz = scaler.get_scaled_reflections('mtz_unmerged').values()[0]
    from iotbx.reflection_file_reader import any_reflection_file
    reader = any_reflection_file(unmerged_mtz)

    from xia2.Wrappers.XIA.PlotMultiplicity import PlotMultiplicity
    mult_json_files = {}
    for axis in ('h', 'k', 'l'):
      pm = PlotMultiplicity()
      auto_logfiler(pm)
      pm.set_working_directory(working_directory)
      pm.set_mtz_filename(unmerged_mtz)
      pm.set_slice_axis(axis)
      pm.set_show_missing(True)
      pm.run()
      mult_json_files[axis] = pm.get_json_filename()

    intensities = None
    batches = None
    assert reader.file_type() == 'ccp4_mtz'
    arrays = reader.as_miller_arrays(merge_equivalents=False)
    for ma in arrays:
      if ma.info().labels == ['BATCH']:
        batches = ma
      elif ma.info().labels == ['I', 'SIGI']:
        intensities = ma
      elif ma.info().labels == ['I(+)', 'SIGI(+)', 'I(-)', 'SIGI(-)']:
        intensities = ma

    from xia2.Wrappers.CCP4.Blend import Blend
    hand_blender = Blend()
    hand_blender.set_working_directory(working_directory)
    auto_logfiler(hand_blender)
    Citations.cite('blend')

    from xia2.Handlers.Environment import which
    Rscript_binary = which('Rscript', debug=False)
    if Rscript_binary is None:
      Chatter.write('Skipping BLEND analysis: Rscript not available')
    else:
      for epoch in epochs:
        hand_blender.add_hklin(epoch_to_integrated_intensities[epoch],
                               label=epoch_to_sweep_name[epoch])
      hand_blender.analysis()
      Chatter.write("Dendrogram saved to: %s" %hand_blender.get_dendrogram_file())
      analysis = hand_blender.get_analysis()
      summary = hand_blender.get_summary()
      clusters = hand_blender.get_clusters()

      linkage_matrix = hand_blender.get_linkage_matrix()
      ddict = hand_blender.plot_dendrogram()

      rows = []
      headers = ['Cluster', 'Datasets', 'Multiplicity', 'Completeness', 'LCV', 'aLCV']
      completeness = flex.double()
      for i, cluster in clusters.iteritems():
        sel_cluster = flex.bool(batches.size(), False)
        for j in cluster['dataset_ids']:
          batch_start, batch_end = epoch_to_batches[epochs[j-1]]
          sel_cluster |= (
            (batches.data() >= batch_start) & (batches.data() <= batch_end))
        intensities_cluster = intensities.select(sel_cluster)
        merging = intensities_cluster.merge_equivalents()
        merged_intensities = merging.array()
        multiplicities = merging.redundancies()
        completeness.append(merged_intensities.completeness())
        dataset_ids = cluster['dataset_ids']

        rows.append(
          ['%i' %i, ' '.join(['%i'] * len(dataset_ids)) %tuple(dataset_ids),
           '%.1f' %flex.mean(multiplicities.data().as_double()),
           '%.2f' %completeness[-1],
           '%.2f' %cluster['lcv'], '%.2f' %cluster['alcv']])

      # sort table by completeness
      perm = flex.sort_permutation(completeness)
      rows = [rows[i] for i in perm]

      print
      print 'Unit cell clustering summary:'
      print tabulate(rows, headers, tablefmt='rst')
      print

      blend_html = tabulate(rows, headers, tablefmt='html').replace(
        '<table>', '<table class="table table-hover table-condensed">').replace(
    '<td>', '<td style="text-align: right;">')

  # XXX what about multiple wavelengths?
  with open('batches.phil', 'wb') as f:
    try:
      for epoch, si in scaler._sweep_information.iteritems():
        print >> f, "batch {"
        print >> f, "  id=%s" %si['sname']
        print >> f, "  range=%i,%i" %tuple(si['batches'])
        print >> f, "}"
    except AttributeError, e:
      for epoch in scaler._sweep_handler.get_epochs():
        si = scaler._sweep_handler.get_sweep_information(epoch)
        print >> f, "batch {"
        print >> f, "  id=%s" %si.get_sweep_name()
        print >> f, "  range=%i,%i" %tuple(si.get_batches())
        print >> f, "}"

  from xia2.Wrappers.XIA.MultiCrystalAnalysis import MultiCrystalAnalysis
  mca = MultiCrystalAnalysis()
  auto_logfiler(mca, extra="MultiCrystalAnalysis")
  mca.add_command_line_args(
    [scaler.get_scaled_reflections(format="sca_unmerged").values()[0],
     "unit_cell=%s %s %s %s %s %s" %tuple(scaler.get_scaler_cell()),
     "batches.phil"])
  mca.set_working_directory(working_directory)
  mca.run()

  intensity_clusters = mca.get_clusters()
  rows = []
  headers = ['Cluster', 'Datasets', 'Multiplicity', 'Completeness', 'Height']
  completeness = flex.double()
  for i, cluster in intensity_clusters.iteritems():
    sel_cluster = flex.bool(batches.size(), False)
    for j in cluster['datasets']:
      batch_start, batch_end = epoch_to_batches[epochs[j-1]]
      sel_cluster |= (
        (batches.data() >= batch_start) & (batches.data() <= batch_end))
    intensities_cluster = intensities.select(sel_cluster)
    merging = intensities_cluster.merge_equivalents()
    merged_intensities = merging.array()
    multiplicities = merging.redundancies()
    completeness.append(merged_intensities.completeness())
    dataset_ids = cluster['datasets']

    rows.append(
      ['%i' %int(i), ' '.join(['%i'] * len(dataset_ids)) %tuple(dataset_ids),
       '%.1f' %flex.mean(multiplicities.data().as_double()),
       '%.2f' %completeness[-1],
       '%.2f' %cluster['height']])

  # sort table by completeness
  perm = flex.sort_permutation(completeness)
  rows = [rows[i] for i in perm]

  print 'Intensity clustering summary:'
  print tabulate(rows, headers, tablefmt='rst')
  print

  intensity_clustering_html = tabulate(rows, headers, tablefmt='html').replace(
    '<table>', '<table class="table table-hover table-condensed">').replace(
    '<td>', '<td style="text-align: right;">')

  import json

  json_data = {}
  if ddict is not None:
    from xia2.Modules.MultiCrystalAnalysis import scipy_dendrogram_to_plotly_json
    json_data['blend_dendrogram'] = scipy_dendrogram_to_plotly_json(ddict)
  else:
    json_data['blend_dendrogram'] = {'data': [], 'layout': {}}

  json_data['intensity_clustering'] = mca.get_dict()
  del json_data['intensity_clustering']['clusters']

  for hkl in ((1,0,0), (0,1,0), (0,0,1)):
    with open(sp_json_files[hkl], 'rb') as f:
      json_data['stereographic_projection_%s%s%s' %hkl] = json.load(f)

  for axis in ('h', 'k', 'l'):
    with open(mult_json_files[axis], 'rb') as f:
      json_data['multiplicity_%s' %axis] = json.load(f)

  json_str = json.dumps(json_data, indent=2)

  javascript = ['var graphs = %s' %(json_str)]
  javascript.append(
    'Plotly.newPlot(blend_dendrogram, graphs.blend_dendrogram.data, graphs.blend_dendrogram.layout);')
  javascript.append(
    'Plotly.newPlot(intensity_clustering, graphs.intensity_clustering.data, graphs.intensity_clustering.layout);')
  for hkl in ((1,0,0), (0,1,0), (0,0,1)):
    javascript.append(
      'Plotly.newPlot(stereographic_projection_%(hkl)s, graphs.stereographic_projection_%(hkl)s.data, graphs.stereographic_projection_%(hkl)s.layout);' %(
      {'hkl': "%s%s%s" %hkl}))
  for axis in ('h', 'k', 'l'):
    javascript.append(
      'Plotly.newPlot(multiplicity_%(axis)s, graphs.multiplicity_%(axis)s.data, graphs.multiplicity_%(axis)s.layout);' %(
      {'axis': axis}))

  html_header = '''
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
  margin-left: 5%;
  margin-right: 5%;
}

.plot {
  float: left;
  width: 1200px;
  height: 800px;
  margin-bottom: 20px;
}

.square_plot {
  float: left;
  width: 800px;
  height: 800px;
  margin-bottom: 20px;
}

</style>

</head>

'''

  html_body = '''

<body>

<div class="page-header">
  <h1>Multi-crystal analysis report</h1>
</div>

<div class="panel-group">

  <div class="panel panel-default">
    <div class="panel-heading" data-toggle="collapse" href="#collapse_multiplicity">
      <h4 class="panel-title">
        <a>Multiplicity plots</a>
      </h4>
    </div>
    <div id="collapse_multiplicity" class="panel-collapse collapse">
      <div class="panel-body">
        <div class="col-xs-12 col-sm-12 col-md-12 square_plot" id="multiplicity_h"></div>
        <div class="col-xs-12 col-sm-12 col-md-12 square_plot" id="multiplicity_k"></div>
        <div class="col-xs-12 col-sm-12 col-md-12 square_plot" id="multiplicity_l"></div>
      </div>
    </div>
  </div>

  <div class="panel panel-default">
    <div class="panel-heading" data-toggle="collapse" href="#collapse_stereographic_projection">
      <h4 class="panel-title">
        <a>Stereographic projections</a>
      </h4>
    </div>
    <div id="collapse_stereographic_projection" class="panel-collapse collapse">
      <div class="panel-body">
        <div class="col-xs-12 col-sm-12 col-md-12 square_plot" id="stereographic_projection_100"></div>
        <div class="col-xs-12 col-sm-12 col-md-12 square_plot" id="stereographic_projection_010"></div>
        <div class="col-xs-12 col-sm-12 col-md-12 square_plot" id="stereographic_projection_001"></div>
      </div>
    </div>
  </div>

  <div class="panel panel-default">
    <div class="panel-heading" data-toggle="collapse" href="#collapse_cell">
      <h4 class="panel-title">
        <a>Unit cell clustering</a>
      </h4>
    </div>
    <div id="collapse_cell" class="panel-collapse collapse">
      <div class="panel-body">
        <div class="col-xs-12 col-sm-12 col-md-12 plot" id="blend_dendrogram"></div>
        <div class="table-responsive" style="width: 800px">
          %(blend_html)s
        </div>
      </div>
    </div>
  </div>

  <div class="panel panel-default">
    <div class="panel-heading" data-toggle="collapse" href="#collapse_intensity">
      <h4 class="panel-title">
        <a>Intensity clustering</a>
      </h4>
    </div>
    <div id="collapse_intensity" class="panel-collapse collapse">
      <div class="panel-body">
        <div class="col-xs-12 col-sm-12 col-md-12 plot" id="intensity_clustering"></div>
        <div class="table-responsive" style="width: 800px">
          %(intensity_clustering_html)s
        </div>
      </div>
    </div>
  </div>
</div>

<script>
%(script)s
</script>
</body>
    ''' %{'script': '\n'.join(javascript),
          'blend_html': blend_html,
          'intensity_clustering_html': intensity_clustering_html}

  html = '\n'.join([html_header, html_body])

  print "Writing html report to: %s" %'multi-crystal-report.html'
  with open('multi-crystal-report.html', 'wb') as f:
    print >> f, html.encode('ascii', 'xmlcharrefreplace')


  write_citations()

  Environment.cleanup()

  return

def run():
  if os.path.exists('xia2-working.phil'):
    sys.argv.append('xia2-working.phil')
  try:
    check_environment()
  except exceptions.Exception, e:
    traceback.print_exc(file = open('xia2.error', 'w'))
    Chatter.write('Status: error "%s"' % str(e))

  if len(sys.argv) < 2 or '-help' in sys.argv:
    help()
    sys.exit()

  wd = os.getcwd()

  try:
    multi_crystal_analysis()
    Chatter.write('Status: normal termination')

  except exceptions.Exception, e:
    traceback.print_exc(file = open(os.path.join(wd, 'xia2.error'), 'w'))
    Chatter.write('Status: error "%s"' % str(e))
    Chatter.write(
      'Please send the contents of xia2.txt, xia2.error and xia2-debug.txt to:')
    Chatter.write('xia2.support@gmail.com')
    sys.exit(1)

if __name__ == '__main__':
  run()
