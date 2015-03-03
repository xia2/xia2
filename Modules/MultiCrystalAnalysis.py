import os

import iotbx.phil
from libtbx.phil import command_line
from scitbx.array_family import flex
from libtbx.containers import OrderedDict
from cctbx import crystal, miller, sgtbx, uctbx

master_phil_scope = iotbx.phil.parse("""\
unit_cell = None
  .type = unit_cell
n_bins = 20
  .type = int(value_min=1)
d_min = None
  .type = float(value_min=0)
""")


try:
  import matplotlib
  # http://matplotlib.org/faq/howto_faq.html#generate-images-without-having-a-window-appear
  matplotlib.use('Agg') # use a non-interactive backend
  from matplotlib import pyplot
except ImportError:
  raise Sorry("matplotlib must be installed to generate a plot.")


class multi_crystal_analysis(object):

  def __init__(self, unmerged_intensities, batches_all, n_bins=20, d_min=None):

    intensities = OrderedDict()
    individual_merged_intensities = OrderedDict()
    batches = OrderedDict()
    #m_isym = OrderedDict()

    sel = unmerged_intensities.sigmas() > 0
    unmerged_intensities = unmerged_intensities.select(sel)
    batches_all = batches_all.select(sel)

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
        print "run %i batch %i to %i" %(run_id+1, run_start, last_batch)
        run_id += 1
        run_start = batch
      last_batch = batch

    unmerged_intensities.setup_binner(n_bins=n_bins)
    unmerged_intensities.show_summary()
    #result = unmerged_intensities.cc_one_half(use_binning=True)
    #result.show()

    self.unmerged_intensities = unmerged_intensities
    self.merged_intensities = unmerged_intensities.merge_equivalents().array()
    self.intensities = intensities
    self.individual_merged_intensities = individual_merged_intensities
    self.batches = batches

    self.relative_anomalous_cc_plot()
    self.cc_matrix_plot()

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

  def relative_anomalous_cc_plot(self):
    racc = self.relative_anomalous_cc()
    if racc is not None:
      perm = flex.sort_permutation(racc)
      fig = pyplot.figure(dpi=1200, figsize=(16,12))
      pyplot.bar(range(len(racc)), list(racc.select(perm)))
      pyplot.xticks([i+0.5 for i in range(len(racc))],
                    ["%.0f" %(j+1) for j in perm])
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

  def cc_matrix_plot(self):
    from scipy.cluster import hierarchy

    correlation_matrix, linkage_matrix = self.compute_correlation_coefficient_matrix()

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

    # Plot colorbar.
    axcolor = fig.add_axes([0.91,0.1,0.02,0.8])
    pyplot.colorbar(im, cax=axcolor)

    # Display and save figure.
    fig.savefig('correlation_matrix.png')
    fig.clear()

    fig = pyplot.figure(dpi=1200, figsize=(16,12))

    hierarchy.dendrogram(linkage_matrix,
                         #truncate_mode='lastp',
                         color_threshold=0.05,
                         labels=['%i' %(i+1) for i in range(len(self.intensities))],
                         show_leaf_counts=True)
    fig.savefig('dendrogram.png')


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
    print ma.info().labels
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

  multi_crystal_analysis(unmerged_intensities, batches_all,
                         n_bins=params.n_bins, d_min=params.d_min)


if __name__ == '__main__':
  import sys
  run(sys.argv[1:])
