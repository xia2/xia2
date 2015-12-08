from __future__ import division
import os
import sys

if not os.environ.has_key('XIA2CORE_ROOT'):
  raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
  sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                               'Python'))

if not os.environ['XIA2_ROOT'] in sys.path:
  sys.path.append(os.environ['XIA2_ROOT'])

import iotbx.phil
from libtbx.phil import command_line
from scitbx.array_family import flex
from libtbx.containers import OrderedDict
from cctbx import crystal, miller, sgtbx, uctbx

from Handlers.Streams import Chatter, Debug

master_phil_scope = iotbx.phil.parse("""\
unit_cell = None
  .type = unit_cell
n_bins = 20
  .type = int(value_min=1)
d_min = None
  .type = float(value_min=0)
batch
  .multiple = True
{
  id = None
    .type = str
  range = None
    .type = ints(size=2, value_min=0)
}
""")


try:
  import matplotlib
  # http://matplotlib.org/faq/howto_faq.html#generate-images-without-having-a-window-appear
  matplotlib.use('Agg') # use a non-interactive backend
  from matplotlib import pyplot
except ImportError:
  raise Sorry("matplotlib must be installed to generate a plot.")


class multi_crystal_analysis(object):

  def __init__(self, unmerged_intensities, batches_all, n_bins=20, d_min=None,
               id_to_batches=None):

    intensities = OrderedDict()
    individual_merged_intensities = OrderedDict()
    batches = OrderedDict()
    #m_isym = OrderedDict()

    sel = unmerged_intensities.sigmas() > 0
    unmerged_intensities = unmerged_intensities.select(sel)
    batches_all = batches_all.select(sel)

    if id_to_batches is None:
      run_id_to_batch_id = None
      run_id = 0
      unique_batches = sorted(set(batches_all.data()))
      last_batch = None
      run_start = unique_batches[0]
      for i, batch in enumerate(unique_batches):
        if last_batch is not None and batch > (last_batch + 1) or (i+1) == len(unique_batches):
          batch_sel = (batches_all.data() >= run_start) & (batches_all.data() <= last_batch)
          batches[run_id] = batches_all.select(batch_sel).resolution_filter(d_min=d_min)
          intensities[run_id] = unmerged_intensities.select(batch_sel).resolution_filter(d_min=d_min)
          individual_merged_intensities[run_id] = intensities[run_id].merge_equivalents().array()
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
        batches[run_id] = batches_all.select(batch_sel).resolution_filter(d_min=d_min)
        intensities[run_id] = unmerged_intensities.select(batch_sel).resolution_filter(d_min=d_min)
        individual_merged_intensities[run_id] = intensities[run_id].merge_equivalents().array()
        Debug.write("run %i batch %i to %i" %(run_id+1, run_start, last_batch))
        run_id += 1

    unmerged_intensities.setup_binner(n_bins=n_bins)
    unmerged_intensities.show_summary()
    #result = unmerged_intensities.cc_one_half(use_binning=True)
    #result.show()

    self.unmerged_intensities = unmerged_intensities
    self.merged_intensities = unmerged_intensities.merge_equivalents().array()
    self.intensities = intensities
    self.individual_merged_intensities = individual_merged_intensities
    self.batches = batches

    if run_id_to_batch_id is not None:
      labels = run_id_to_batch_id.values()
    else:
      labels = None
    racc = self.relative_anomalous_cc()
    if racc is not None:
      self.plot_relative_anomalous_cc(racc, labels=labels)
    correlation_matrix, linkage_matrix = self.compute_correlation_coefficient_matrix()
    self.plot_cc_matrix(correlation_matrix, linkage_matrix, labels=labels)

    self.write_output(correlation_matrix, linkage_matrix, racc)

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

    hierarchy.dendrogram(linkage_matrix,
                         #truncate_mode='lastp',
                         color_threshold=0.05,
                         labels=labels,
                         #leaf_rotation=90,
                         show_leaf_counts=False)
    locs, labels = pyplot.xticks()
    pyplot.setp(labels, rotation=70)
    fig.savefig('dendrogram.png')

  def write_output(self, correlation_matrix, linkage_matrix, racc):
    from scipy.cluster import hierarchy
    tree = hierarchy.to_tree(linkage_matrix, rd=False)
    leaves_list = hierarchy.leaves_list(linkage_matrix)
    #print tree
    #print leaves_list
    #print tree.get_count()
    #print tree.get_id()
    #print tree.get_left()
    #print tree.get_right()
    #print tree.is_leaf()
    #print tree.pre_order()

    cluster_dict = {}

    # http://w3facility.org/question/scipy-dendrogram-to-json-for-d3-js-tree-visualisation/
    # https://gist.github.com/mdml/7537455

    def add_node(node):
      if node.is_leaf(): return
      cluster_id = node.get_id() - len(linkage_matrix) - 1
      row = linkage_matrix[cluster_id]
      cluster_dict[cluster_id+1] = {
        'datasets': [i+1 for i in sorted(node.pre_order())],
        'height': row[2],
      }

      # Recursively add the current node's children
      if node.left: add_node(node.left)
      if node.right: add_node(node.right)

    add_node(tree)

    rows = [["cluster_id", "# datasets", "height", "datasets"]]
    for cid in sorted(cluster_dict.keys()):
      cluster = cluster_dict[cid]
      datasets = cluster['datasets']
      rows.append([str(cid), str(len(datasets)),
                   '%.2f' %cluster['height'], ' '.join(['%s'] * len(datasets)) % tuple(datasets)])

    with open('intensity_clusters.json', 'wb') as f:
      import json
      json.dump(cluster_dict, f)

    with open('intensity_clustering.txt', 'wb') as f:
      from libtbx import table_utils
      print >> f, table_utils.format(
        rows, has_header=True, prefix="|", postfix="|")


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
    id_to_batches = {
    }
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
