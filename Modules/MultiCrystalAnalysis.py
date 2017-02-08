from __future__ import absolute_import, division
import os
import sys

import iotbx.phil
from libtbx.phil import command_line
from scitbx.array_family import flex
from libtbx.containers import OrderedDict
from cctbx import crystal, miller, sgtbx, uctbx

from xia2.Handlers.Streams import Chatter, Debug

def get_scipy():
  # make sure we can get scipy, if not try failing over to version in CCP4
  try:
    import scipy.cluster
    found = True
  except ImportError, e:
    found = False

  if not found and 'CCP4' in os.environ:
    sys.path.append(os.path.join(os.environ['CCP4'], 'lib', 'python2.7',
                                 'site-packages'))
    try:
      import scipy.cluster
      found = True
    except ImportError, e:
      found = False

  if not found:
    from libtbx.utils import Sorry
    raise Sorry('%s depends on scipy.cluster, not available' % sys.argv[0])

get_scipy()

batch_phil_scope = """\
batch
  .multiple = True
{
  id = None
    .type = str
  range = None
    .type = ints(size=2, value_min=0)
}
"""

master_phil_scope = iotbx.phil.parse("""\
unit_cell = None
  .type = unit_cell
n_bins = 20
  .type = int(value_min=1)
d_min = None
  .type = float(value_min=0)
%s
""" %batch_phil_scope)


try:
  import matplotlib
  # http://matplotlib.org/faq/howto_faq.html#generate-images-without-having-a-window-appear
  matplotlib.use('Agg') # use a non-interactive backend
  from matplotlib import pyplot
except ImportError:
  raise Sorry("matplotlib must be installed to generate a plot.")



class separate_unmerged(object):

  def __init__(self, unmerged_intensities, batches_all, id_to_batches=None):

    intensities = OrderedDict()
    batches = OrderedDict()

    if id_to_batches is None:
      run_id_to_batch_id = None
      run_id = 0
      unique_batches = sorted(set(batches_all.data()))
      last_batch = None
      run_start = unique_batches[0]
      for i, batch in enumerate(unique_batches):
        if last_batch is not None and batch > (last_batch + 1) or (i+1) == len(unique_batches):
          batch_sel = (batches_all.data() >= run_start) & (batches_all.data() <= last_batch)
          batches[run_id] = batches_all.select(batch_sel)
          intensities[run_id] = unmerged_intensities.select(batch_sel)
          Debug.write("run %i batch %i to %i" %(run_id+1, run_start, last_batch))
          run_id += 1
          run_start = batch
        last_batch = batch

    else:
      run_id_to_batch_id = OrderedDict()
      run_id = 0
      for batch_id, batch_range in id_to_batches.iteritems():
        run_id_to_batch_id[run_id] = batch_id
        run_start, last_batch = batch_range
        batch_sel = (batches_all.data() >= run_start) & (batches_all.data() <= last_batch)
        batches[run_id] = batches_all.select(batch_sel)
        intensities[run_id] = unmerged_intensities.select(batch_sel)
        Debug.write("run %i batch %i to %i" %(run_id+1, run_start, last_batch))
        run_id += 1

    self.run_id_to_batch_id = run_id_to_batch_id
    self.intensities = intensities
    self.batches = batches


class multi_crystal_analysis(object):

  def __init__(self, unmerged_intensities, batches_all, n_bins=20, d_min=None,
               id_to_batches=None):

    sel = unmerged_intensities.sigmas() > 0
    unmerged_intensities = unmerged_intensities.select(sel)
    batches_all = batches_all.select(sel)

    unmerged_intensities.setup_binner(n_bins=n_bins)
    unmerged_intensities.show_summary()
    self.unmerged_intensities = unmerged_intensities
    self.merged_intensities = unmerged_intensities.merge_equivalents().array()

    separate = separate_unmerged(
      unmerged_intensities, batches_all, id_to_batches=id_to_batches)
    self.intensities = separate.intensities
    self.batches = separate.batches
    run_id_to_batch_id = separate.run_id_to_batch_id
    self.individual_merged_intensities = OrderedDict()
    for k in self.intensities.keys():
      self.intensities[k] = self.intensities[k].resolution_filter(d_min=d_min)
      self.batches[k] = self.batches[k].resolution_filter(d_min=d_min)
      self.individual_merged_intensities[k] = self.intensities[k].merge_equivalents().array()

    if run_id_to_batch_id is not None:
      labels = run_id_to_batch_id.values()
    else:
      labels = None
    racc = self.relative_anomalous_cc()
    if racc is not None:
      self.plot_relative_anomalous_cc(racc, labels=labels)
    correlation_matrix, linkage_matrix = self.compute_correlation_coefficient_matrix()

    self._cluster_dict = self.to_dict(correlation_matrix, linkage_matrix)

    self.plot_cc_matrix(correlation_matrix, linkage_matrix, labels=labels)

    self.write_output()

  def to_dict(self, correlation_matrix, linkage_matrix):

    from scipy.cluster import hierarchy
    tree = hierarchy.to_tree(linkage_matrix, rd=False)
    leaves_list = hierarchy.leaves_list(linkage_matrix)

    d = {}

    # http://w3facility.org/question/scipy-dendrogram-to-json-for-d3-js-tree-visualisation/
    # https://gist.github.com/mdml/7537455

    def add_node(node):
      if node.is_leaf(): return
      cluster_id = node.get_id() - len(linkage_matrix) - 1
      row = linkage_matrix[cluster_id]
      d[cluster_id+1] = {
        'datasets': [i+1 for i in sorted(node.pre_order())],
        'height': row[2],
      }

      # Recursively add the current node's children
      if node.left: add_node(node.left)
      if node.right: add_node(node.right)

    add_node(tree)

    return d

  def relative_anomalous_cc(self):
    if self.unmerged_intensities.anomalous_flag():
      d_min = min([ma.d_min() for ma in self.intensities.values()])
      racc = flex.double()
      full_set_anom_diffs = self.merged_intensities.anomalous_differences()
      for i_wedge in self.individual_merged_intensities.keys():
        ma_i = self.individual_merged_intensities[i_wedge].resolution_filter(d_min=d_min)
        anom_i = ma_i.anomalous_differences()
        anom_cc = anom_i.correlation(full_set_anom_diffs, assert_is_similar_symmetry=False).coefficient()
        racc.append(anom_cc)
      return racc

  def plot_relative_anomalous_cc(self, racc, labels=None):
    perm = flex.sort_permutation(racc)
    fig = pyplot.figure(dpi=1200, figsize=(16,12))
    pyplot.bar(range(len(racc)), list(racc.select(perm)))
    if labels is None:
      labels = ["%.0f" %(j+1) for j in perm]
    assert len(labels) == len(racc)
    pyplot.xticks([i+0.5 for i in range(len(racc))], labels)
    locs, labels = pyplot.xticks()
    pyplot.setp(labels, rotation=70)
    pyplot.xlabel("Dataset")
    pyplot.ylabel("Relative anomalous correlation coefficient")
    fig.savefig("racc.png")

  def compute_correlation_coefficient_matrix(self):
    from scipy.cluster import hierarchy
    import scipy.spatial.distance as ssd

    correlation_matrix = flex.double(
      flex.grid(len(self.intensities), len(self.intensities)))

    d_min = min([ma.d_min() for ma in self.intensities.values()])

    for i_wedge in self.individual_merged_intensities.keys():
      for j_wedge in self.individual_merged_intensities.keys():
        if j_wedge < i_wedge: continue
        ma_i = self.individual_merged_intensities[i_wedge].resolution_filter(d_min=d_min)
        ma_j = self.individual_merged_intensities[j_wedge].resolution_filter(d_min=d_min)
        cc_ij = ma_i.correlation(ma_j).coefficient()
        correlation_matrix[(i_wedge,j_wedge)] = cc_ij
        correlation_matrix[j_wedge,i_wedge] = cc_ij

    diffraction_dissimilarity = 1-correlation_matrix

    dist_mat = diffraction_dissimilarity.as_numpy_array()

    # convert the redundant n*n square matrix form into a condensed nC2 array
    dist_mat = ssd.squareform(dist_mat) # distArray[{n choose 2}-{n-i choose 2} + (j-i-1)] is the distance between points i and j

    method = ['single', 'complete', 'average', 'weighted'][2]

    linkage_matrix = hierarchy.linkage(dist_mat, method=method)

    return correlation_matrix, linkage_matrix

  def plot_cc_matrix(self, correlation_matrix, linkage_matrix, labels=None):
    from scipy.cluster import hierarchy

    ind = hierarchy.fcluster(linkage_matrix, t=0.05, criterion='distance')

    # Compute and plot dendrogram.
    fig = pyplot.figure(dpi=1200, figsize=(16,12))
    axdendro = fig.add_axes([0.09,0.1,0.2,0.8])
    Y = linkage_matrix
    Z = hierarchy.dendrogram(Y,
                             color_threshold=0.05,
                             orientation='right')
    axdendro.set_xticks([])
    axdendro.set_yticks([])

    # Plot distance matrix.
    axmatrix = fig.add_axes([0.3,0.1,0.6,0.8])
    index = Z['leaves']
    D = correlation_matrix.as_numpy_array()
    D = D[index,:]
    D = D[:,index]
    im = axmatrix.matshow(D, aspect='auto', origin='lower')
    axmatrix.yaxis.tick_right()
    if labels is not None:
      axmatrix.xaxis.tick_bottom()
      axmatrix.set_xticks(list(range(len(labels))))
      axmatrix.set_xticklabels([labels[i] for i in index], rotation=70)
      axmatrix.yaxis.set_ticks([])

    # Plot colorbar.
    axcolor = fig.add_axes([0.91,0.1,0.02,0.8])
    pyplot.colorbar(im, cax=axcolor)

    # Display and save figure.
    fig.savefig('correlation_matrix.png')
    fig.clear()

    fig = pyplot.figure(dpi=1200, figsize=(16,12))

    if labels is None:
      labels = ['%i' %(i+1) for i in range(len(self.intensities))]

    ddict = hierarchy.dendrogram(linkage_matrix,
                                 #truncate_mode='lastp',
                                 color_threshold=0.05,
                                 labels=labels,
                                 #leaf_rotation=90,
                                 show_leaf_counts=False)
    locs, labels = pyplot.xticks()
    pyplot.setp(labels, rotation=70)
    fig.savefig('dendrogram.png')

    import copy
    y2_dict = scipy_dendrogram_to_plotly_json(ddict) # above heatmap
    x2_dict = copy.deepcopy(y2_dict) # left of heatmap, rotated
    for d in y2_dict['data']:
      d['yaxis'] = 'y2'
      d['xaxis'] = 'x2'

    for d in x2_dict['data']:
      x = d['x']
      y = d['y']
      d['x'] = y
      d['y'] = x
      d['yaxis'] = 'y3'
      d['xaxis'] = 'x3'

    ccdict = {
      'data': [{
        'name': 'correlation_matrix',
        'x': list(range(D.shape[0])),
        'y': list(range(D.shape[1])),
        'z': D.tolist(),
        'type': 'heatmap',
        'colorbar': {
          'title': 'Correlation coefficient',
          'titleside': 'right',
          #'x': 0.96,
          #'y': 0.9,
          #'titleside': 'top',
          #'xanchor': 'right',
          'xpad': 0,
          #'yanchor': 'top'
        },
        'colorscale': 'Jet',
        'xaxis': 'x',
        'yaxis': 'y',
      }],

      'layout': {
        'autosize': False,
        'bargap': 0,
        'height': 1000,
        'hovermode': 'closest',
        'margin': {
          'r': 20,
          't': 50,
          'autoexpand': True,
          'l': 20
          },
        'showlegend': False,
        'title': 'Dendrogram Heatmap',
        'width': 1000,
        'xaxis': {
          'domain': [0.2, 0.9],
          'mirror': 'allticks',
          'showgrid': False,
          'showline': False,
          'showticklabels': True,
          'tickmode': 'array',
          'ticks': '',
          'ticktext': y2_dict['layout']['xaxis']['ticktext'],
          'tickvals': list(range(len(y2_dict['layout']['xaxis']['ticktext']))),
          'tickangle': 300,
          'title': '',
          'type': 'linear',
          'zeroline': False
        },
        'yaxis': {
          'domain': [0, 0.78],
          'anchor': 'x',
          'mirror': 'allticks',
          'showgrid': False,
          'showline': False,
          'showticklabels': True,
          'tickmode': 'array',
          'ticks': '',
          'ticktext': y2_dict['layout']['xaxis']['ticktext'],
          'tickvals': list(range(len(y2_dict['layout']['xaxis']['ticktext']))),
          'title': '',
          'type': 'linear',
          'zeroline': False
        },
        'xaxis2': {
          'domain': [0.2, 0.9],
          'anchor': 'y2',
          'showgrid': False,
          'showline': False,
          'showticklabels': False,
          'zeroline': False
        },
        'yaxis2': {
          'domain': [0.8, 1],
          'anchor': 'x2',
          'showgrid': False,
          'showline': False,
          'zeroline': False
        },
        'xaxis3': {
          'domain': [0.0, 0.1],
          'anchor': 'y3',
          'range': [max(max(d['x']) for d in x2_dict['data']), 0],
          'showgrid': False,
          'showline': False,
          'tickangle': 300,
          'zeroline': False
        },
        'yaxis3': {
          'domain': [0, 0.78],
          'anchor': 'x3',
          'showgrid': False,
          'showline': False,
          'showticklabels': False,
          'zeroline': False
        },
      }
    }
    d = ccdict
    d['data'].extend(y2_dict['data'])
    d['data'].extend(x2_dict['data'])

    d['clusters'] = self._cluster_dict

    import json
    with open('intensity_clusters.json', 'wb') as f:
      json.dump(d, f, indent=2)


  def write_output(self):

    rows = [["cluster_id", "# datasets", "height", "datasets"]]
    for cid in sorted(self._cluster_dict.keys()):
      cluster = self._cluster_dict[cid]
      datasets = cluster['datasets']
      rows.append([str(cid), str(len(datasets)),
                   '%.2f' %cluster['height'], ' '.join(['%s'] * len(datasets)) % tuple(datasets)])

    with open('intensity_clustering.txt', 'wb') as f:
      from libtbx import table_utils
      print >> f, table_utils.format(
        rows, has_header=True, prefix="|", postfix="|")


def scipy_dendrogram_to_plotly_json(ddict):
  colors = { 'b': 'rgb(31, 119, 180)',
             'g': 'rgb(44, 160, 44)',
             'o': 'rgb(255, 127, 14)',
             'r': 'rgb(214, 39, 40)',
  }

  dcoord = ddict['dcoord']
  icoord = ddict['icoord']
  color_list = ddict['color_list']
  ivl = ddict['ivl']
  leaves = ddict['leaves']

  data = []
  xticktext = []
  xtickvals = []

  k_leaf_node = 0

  for k in range(len(dcoord)):
    x = icoord[k]
    y = dcoord[k]

    if y[0] == 0:
      xticktext.append(ivl[k_leaf_node])
      xtickvals.append(x[0])
      k_leaf_node += 1
    if y[3] == 0:
      xticktext.append(ivl[k_leaf_node])
      xtickvals.append(x[3])
      k_leaf_node += 1

    data.append({
      'x': x,
      'y': y,
      'name': ivl,
      'marker': {
        'color': colors.get(color_list[k]),
      },
      'mode':"lines",
    })

  d = {
    'data': data,
    'layout': {
      'barmode': 'group',
      'legend': {
        'x': 100,
        'y': 0.5,
        'bordercolor': 'transparent'
      },
      'margin': {
        'r': 10
      },
      'showlegend': False,
      'title': 'BLEND dendrogram',
      'xaxis': {
        'showline': False,
        'showgrid': False,
        'showticklabels': True,
        'tickangle': 300,
        'title': 'Individual datasets',
        'titlefont': {
          'color': 'none'
        },
        'type': 'linear',
        'ticktext': xticktext,
        'tickvals': xtickvals,
        'tickorientation': 'vertical',
      },
      'yaxis': {
        'showline': False,
        'showgrid': False,
        'showticklabels': True,
        'tickangle': 0,
        'title': 'Ward distance',
        'type': 'linear'
      },
      'hovermode': 'closest',
    }
  }
  return d


def run(args):

  cmd_line = command_line.argument_interpreter(master_params=master_phil_scope)
  working_phil, args = cmd_line.process_and_fetch(args=args, custom_processor="collect_remaining")
  working_phil.show()
  params = working_phil.extract()

  if params.unit_cell is not None:
    unit_cell = params.unit_cell
    crystal_symmetry = crystal.symmetry(unit_cell=unit_cell)
  else:
    crystal_symmetry = None

  from iotbx.reflection_file_reader import any_reflection_file
  result = any_reflection_file(args[0])
  unmerged_intensities = None
  batches_all = None

  for ma in result.as_miller_arrays(
    merge_equivalents=False, crystal_symmetry=crystal_symmetry):
    #print ma.info().labels
    if ma.info().labels == ['I(+)', 'SIGI(+)', 'I(-)', 'SIGI(-)']:
      assert ma.anomalous_flag()
      unmerged_intensities = ma
    elif ma.info().labels == ['I', 'SIGI']:
      assert not ma.anomalous_flag()
      unmerged_intensities = ma
    elif ma.info().labels == ['BATCH']:
      batches_all = ma

  assert batches_all is not None
  assert unmerged_intensities is not None

  id_to_batches = None

  if len(params.batch) > 0:
    id_to_batches = OrderedDict()
    for b in params.batch:
      assert b.id is not None
      assert b.range is not None
      assert b.id not in id_to_batches, "Duplicate batch id: %s" %b.id
      id_to_batches[b.id] = b.range

  multi_crystal_analysis(unmerged_intensities, batches_all,
                         n_bins=params.n_bins, d_min=params.d_min,
                         id_to_batches=id_to_batches)


if __name__ == '__main__':
  import sys
  run(sys.argv[1:])
