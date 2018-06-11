#!/usr/bin/env dials.python
from __future__ import absolute_import, division, print_function

from collections import OrderedDict
import copy
import logging
import math
import os

import iotbx.phil
from iotbx.reflection_file_reader import any_reflection_file
from cctbx import crystal
from cctbx import sgtbx
from dxtbx.serialize import dump, load
from dxtbx.model import ExperimentList

from dials.array_family import flex
from dials.algorithms.symmetry.cosym import analyse_datasets as cosym_analyse_datasets

from dials.command_line.export import phil_scope as export_phil_scope
from dials.util.export_mtz import export_mtz


from xia2.lib.bits import auto_logfiler
from xia2.Handlers.Phil import PhilIndex
from xia2.Modules.MultiCrystal import multi_crystal_analysis
from xia2.Modules.MultiCrystal import separate_unmerged
import xia2.Modules.Scaler.tools as tools
from xia2.Wrappers.CCP4.Aimless import Aimless
from xia2.Wrappers.CCP4.Pointless import Pointless
from xia2.Wrappers.Dials.Refine import Refine
from xia2.Wrappers.Dials.Scale import DialsScale
from xia2.Wrappers.Dials.Symmetry import DialsSymmetry
from xia2.Wrappers.Dials.TwoThetaRefine import TwoThetaRefine


logger = logging.getLogger(__name__)


try:
  import matplotlib
  # http://matplotlib.org/faq/howto_faq.html#generate-images-without-having-a-window-appear
  matplotlib.use('Agg') # use a non-interactive backend
  from matplotlib import pyplot
except ImportError:
  raise Sorry("matplotlib must be installed to generate a plot.")


# The phil scope
phil_scope = iotbx.phil.parse('''
unit_cell_clustering {
  threshold = 5000
    .type = float(value_min=0)
    .help = 'Threshold value for the clustering'
  log = False
    .type = bool
    .help = 'Display the dendrogram with a log scale'
}

scaling
  .short_caption = "aimless"
{
  program = *aimless dials
    .type = choice
  #intensities = summation profile *combine
    #.type = choice
  surface_tie = 0.001
    .type = float
    .short_caption = "Surface tie"
  surface_link = True
    .type = bool
    .short_caption = "Surface link"
  rotation.spacing = 2
    .type = int
    .expert_level = 2
    .short_caption = "Interval (in degrees) between scale factors on rotation axis"
  brotation.spacing = None
    .type = int
    .expert_level = 2
    .short_caption = "Interval (in degrees) between B-factors on rotation axis"
  secondary {
    frame = camera *crystal
      .type = choice
      .help = "Whether to do the secondary beam correction in the camera spindle"
              "frame or the crystal frame"
    lmax = 0
      .type = int
      .expert_level = 2
      .short_caption = "Number of spherical harmonics for absorption correction"
  }
  dials {
    model = *physical array KB
      .type = choice
    outlier_rejection = simple *standard
      .type = choice
  }
}

symmetry {
  resolve_indexing_ambiguity = True
    .type = bool
  cosym {
    include scope dials.algorithms.symmetry.cosym.phil_scope
  }
  le_page_max_delta = 5
    .type = float(value_min=0)
  program = *pointless dials
    .type = choice
}

resolution
  .short_caption = "Resolution"
{
  d_max = None
    .type = float(value_min=0.0)
    .help = "Low resolution cutoff."
    .short_caption = "Low resolution cutoff"
  d_min = None
    .type = float(value_min=0.0)
    .help = "High resolution cutoff."
    .short_caption = "High resolution cutoff"
  include scope dials.util.Resolutionizer.phil_str
}

multi_crystal_analysis {
  include scope xia2.Modules.MultiCrystal.master_phil_scope
}

min_completeness = None
  .type = float(value_min=0, value_max=1)
min_multiplicity = None
  .type = float(value_min=0)

identifiers = None
  .type = strings

''', process_includes=True)

# override default parameters
phil_scope = phil_scope.fetch(source=iotbx.phil.parse(
  """\
resolution {
  cc_half_method = sigma_tau
  cc_half_fit = tanh
  cc_half = 0.3
  isigma = None
  misigma = None
}
"""))


class DataManager(object):
  def __init__(self, experiments, reflections):
    self._input_experiments = experiments
    self._input_reflections = reflections

    self._experiments = copy.deepcopy(experiments)
    self._reflections = copy.deepcopy(reflections)

    self._set_batches()

  def _set_batches(self):
    max_batches = max(e.scan.get_image_range()[1] for e in self._experiments)
    max_batches += 10 # allow some head room

    n = int(math.ceil(math.log10(max_batches)))

    for i, expt in enumerate(self._experiments):
      expt.scan.set_batch_offset(i * 10**n)
      logger.debug("%s %s" % (expt.scan.get_batch_offset(), expt.scan.get_batch_range()))

  @property
  def experiments(self):
    return self._experiments

  @experiments.setter
  def experiments(self, experiments):
    self._experiments = experiments

  @property
  def reflections(self):
    return self._reflections

  @reflections.setter
  def reflections(self, reflections):
    self._reflections = reflections

  def select(self, experiment_identifiers):
    self._experiments = ExperimentList(
      [expt for expt in self._experiments
       if expt.identifier in experiment_identifiers])
    experiment_identifiers = self._experiments.identifiers()
    sel = flex.bool(len(self._reflections), False)
    for i_expt, identifier in enumerate(experiment_identifiers):
      sel_expt = self._reflections['identifier'] == identifier
      sel.set_selected(sel_expt, True)
      self._reflections['id'].set_selected(sel_expt, i_expt)
    self._reflections = self._reflections.select(sel)
    assert self.reflections.are_experiment_identifiers_consistent(
      self._experiments)

  def reflections_as_miller_arrays(self, intensity_key='intensity.sum.value', return_batches=False):
    from cctbx import crystal, miller
    variance_key = intensity_key.replace('.value', '.variance')
    assert intensity_key in self._reflections
    assert variance_key in self._reflections

    miller_arrays = []
    for expt in self._experiments:
      crystal_symmetry = crystal.symmetry(
        unit_cell=expt.crystal.get_unit_cell(),
        space_group=expt.crystal.get_space_group())
      sel = ((self._reflections.get_flags(self._reflections.flags.integrated_sum)
              & (self._reflections['identifier'] == expt.identifier)))
      assert sel.count(True) > 0
      refl = self._reflections.select(sel)
      data = refl[intensity_key]
      variances = refl[variance_key]
      if return_batches:
        batch_offset = expt.scan.get_batch_offset()
        zdet = refl['xyzobs.px.value'].parts()[2]
        batches = flex.floor(zdet).iround() + 1 + batch_offset

      # FIXME probably need to do some filtering of intensities similar to that
      # done in export_mtz
      miller_indices = refl['miller_index']
      assert variances.all_gt(0)
      sigmas = flex.sqrt(variances)

      miller_set = miller.set(crystal_symmetry, miller_indices, anomalous_flag=False)
      intensities = miller.array(miller_set, data=data, sigmas=sigmas)
      intensities.set_observation_type_xray_intensity()
      intensities.set_info(miller.array_info(
        source='DIALS', source_type='pickle'))
      if return_batches:
        batches = miller.array(miller_set, data=batches).set_info(
          intensities.info())
        miller_arrays.append([intensities, batches])
      else:
        miller_arrays.append(intensities)
    return miller_arrays

  def reindex(self, cb_op=None, cb_ops=None, space_group=None):
    assert [cb_op, cb_ops].count(None) == 1

    if cb_op is not None:
      logger.info('Reindexing: %s' % cb_op)
      self._reflections['miller_index'] = cb_op.apply(self._reflections['miller_index'])

      for expt in self._experiments:
        cryst_reindexed = expt.crystal.change_basis(cb_op)
        if space_group is not None:
          cryst_reindexed.set_space_group(space_group)
        expt.crystal.update(cryst_reindexed)

    elif isinstance(cb_ops, dict):
      for cb_op, dataset_ids in cb_ops.iteritems():
        cb_op = sgtbx.change_of_basis_op(cb_op)

        for dataset_id in dataset_ids:
          expt = self._experiments[dataset_id]
          logger.info('Reindexing experiment %s: %s' % (
            expt.identifier, cb_op.as_xyz()))
          cryst_reindexed = expt.crystal.change_basis(cb_op)
          if space_group is not None:
            cryst_reindexed.set_space_group(space_group)
          expt.crystal.update(cryst_reindexed)
          sel = self._reflections['identifier'] == expt.identifier
          self._reflections['miller_index'].set_selected(sel, cb_op.apply(
            self._reflections['miller_index'].select(sel)))

    else:
      assert len(cb_ops) == len(self._experiments)
      for cb_op, expt in zip(cb_ops, self._experiments):
        logger.info('Reindexing experiment %s: %s' % (
          expt.identifier, cb_op.as_xyz()))
        cryst_reindexed = expt.crystal.change_basis(cb_op)
        if space_group is not None:
          cryst_reindexed.set_space_group(space_group)
        expt.crystal.update(cryst_reindexed)
        sel = self._reflections['identifier'] == expt.identifier
        self._reflections['miller_index'].set_selected(sel, cb_op.apply(
          self._reflections['miller_index'].select(sel)))

  def export_reflections(self, filename):
    self._reflections.as_pickle(filename)

  def export_experiments(self, filename):
    dump.experiment_list(self._experiments, filename)

  def export_mtz(self, filename=None, params=None):
    if params is None:
      params = export_phil_scope.extract()
    if filename is not None:
      params.mtz.hklout = filename

    m = export_mtz(
      self._reflections,
      self._experiments,
      params.mtz.hklout,
      include_partials=params.mtz.include_partials,
      keep_partials=params.mtz.keep_partials,
      scale_partials=params.mtz.scale_partials,
      min_isigi=params.mtz.min_isigi,
      force_static_model=params.mtz.force_static_model,
      filter_ice_rings=params.mtz.filter_ice_rings,
      ignore_profile_fitting=params.mtz.ignore_profile_fitting,
      apply_scales=params.mtz.apply_scales)
    m.show_summary()

    b1 = set(b.num() for b in m.batches())
    b2 = set(m.get_column('BATCH').extract_values().as_double().iround())
    assert len(b2.difference(b1)) == 0

    return params.mtz.hklout


class MultiCrystalScale(object):
  def __init__(self, experiments, reflections, params):

    self._data_manager = DataManager(experiments, reflections)
    self._params = params

    if self._params.identifiers is not None:
      self._data_manager.select(self._params.identifiers)

    experiments = self._data_manager.experiments
    reflections = self._data_manager.reflections

    self.unit_cell_clustering(plot_name='cluster_unit_cell_p1.png')

    self.unit_cell_histogram(plot_name='unit_cell_histogram.png')

    if self._params.symmetry.resolve_indexing_ambiguity:
      self.cosym()

    self._scaled = Scale(self._data_manager, self._params)

    self.unit_cell_clustering(plot_name='cluster_unit_cell_sg.png')

    id_to_batches = OrderedDict(
      (expt.identifier, expt.scan.get_batch_range())
      for expt in self._data_manager.experiments)
    mca = self.multi_crystal_analysis(id_to_batches=id_to_batches)

    self._data_manager.export_experiments('experiments_reindexed_all.json')
    self._data_manager.export_reflections('reflections_reindexed_all.pickle')
    self.stereographic_projections('experiments_reindexed_all.json')
    self.plot_multiplicity(self._scaled.scaled_unmerged_mtz)

    min_completeness = self._params.min_completeness
    min_multiplicity = self._params.min_multiplicity
    if min_completeness is not None or min_multiplicity is not None:
      self._data_manager_original = self._data_manager
      for cluster in mca.cos_angle_clusters:
        if min_completeness is not None and cluster.completeness < min_completeness:
          continue
        if min_multiplicity is not None and cluster.multiplicity < min_multiplicity:
          continue
        if len(cluster.labels) == len(self._data_manager_original.experiments):
          continue

        logger.info('Scaling cos angle cluster %i:' % cluster.cluster_id)
        logger.info(cluster)
        data_manager = copy.deepcopy(self._data_manager_original)
        data_manager.select(cluster.labels)
        scaled = Scale(data_manager, self._params)

    return

  @staticmethod
  def stereographic_projections(experiments_filename):
    from xia2.Wrappers.Dials.StereographicProjection import StereographicProjection
    sp_json_files = {}
    for hkl in ((1,0,0), (0,1,0), (0,0,1)):
      sp = StereographicProjection()
      auto_logfiler(sp)
      sp.add_experiments(experiments_filename)
      sp.set_hkl(hkl)
      sp.run()
      sp_json_files[hkl] = sp.get_json_filename()
    return sp_json_files

  @staticmethod
  def plot_multiplicity(unmerged_mtz):
    from xia2.Wrappers.XIA.PlotMultiplicity import PlotMultiplicity
    mult_json_files = {}
    for axis in ('h', 'k', 'l'):
      pm = PlotMultiplicity()
      auto_logfiler(pm)
      pm.set_mtz_filename(unmerged_mtz)
      pm.set_slice_axis(axis)
      pm.set_show_missing(True)
      pm.run()
      mult_json_files[axis] = pm.get_json_filename()
    return mult_json_files

  def unit_cell_clustering(self, plot_name=None):
    crystal_symmetries = []
    for expt in self._data_manager.experiments:
      crystal_symmetry = expt.crystal.get_crystal_symmetry(
        assert_is_compatible_unit_cell=False)
      crystal_symmetries.append(crystal_symmetry.niggli_cell())
    lattice_ids = [expt.identifier for expt in self._data_manager.experiments]
    from xfel.clustering.cluster import Cluster
    from xfel.clustering.cluster_groups import unit_cell_info
    ucs = Cluster.from_crystal_symmetries(crystal_symmetries, lattice_ids=lattice_ids)
    if plot_name is not None:
      from matplotlib import pyplot as plt
      plt.figure("Andrews-Bernstein distance dendogram", figsize=(12, 8))
      ax = plt.gca()
    else:
      ax = None
    clusters, _ = ucs.ab_cluster(
      self._params.unit_cell_clustering.threshold,
      log=self._params.unit_cell_clustering.log,
      write_file_lists=False,
      schnell=False,
      doplot=(plot_name is not None),
      ax=ax
    )
    if plot_name is not None:
      plt.tight_layout()
      plt.savefig(plot_name)
      plt.clf()
    logger.info(unit_cell_info(clusters))
    largest_cluster = None
    largest_cluster_lattice_ids = None
    for cluster in clusters:
      cluster_lattice_ids = [m.lattice_id for m in cluster.members]
      if largest_cluster_lattice_ids is None:
        largest_cluster_lattice_ids = cluster_lattice_ids
      elif len(cluster_lattice_ids) > len(largest_cluster_lattice_ids):
        largest_cluster_lattice_ids = cluster_lattice_ids

    if len(largest_cluster_lattice_ids) < len(crystal_symmetries):
      logger.info(
        'Selecting subset of data sets for subsequent analysis: %s' %str(largest_cluster_lattice_ids))
      self._data_manager.select(largest_cluster_lattice_ids)
    else:
      logger.info('Using all data sets for subsequent analysis')

  def unit_cell_histogram(self, plot_name=None):

    uc_params = [flex.double() for i in range(6)]
    for expt in self._data_manager.experiments:
      uc = expt.crystal.get_unit_cell()
      for i in range(6):
        uc_params[i].append(uc.parameters()[i])

    iqr_ratio = 1.5
    outliers = flex.bool(uc_params[0].size(), False)
    for p in uc_params:
      from scitbx.math import five_number_summary
      min_x, q1_x, med_x, q3_x, max_x = five_number_summary(p)
      logger.info(
        'Five number summary: min %.2f, q1 %.2f, med %.2f, q3 %.2f, max %.2f'
        % (min_x, q1_x, med_x, q3_x, max_x))
      iqr_x = q3_x - q1_x
      if iqr_x < 1e-6:
        continue
      cut_x = iqr_ratio * iqr_x
      outliers.set_selected(p > q3_x + cut_x, True)
      outliers.set_selected(p < q1_x - cut_x, True)
    logger.info('Identified %i unit cell outliers' % outliers.count(True))

    self.plot_uc_histograms(uc_params, outliers,
                            #self._params.steps_per_angstrom
                            )

  @staticmethod
  def plot_uc_histograms(uc_params, outliers, steps_per_angstrom=20,
                         plot_name='uc_histograms.png'):
    from matplotlib import pyplot as plt
    plt.style.use('ggplot')
    uc_labels = ['a', 'b', 'c']
    f, ax = plt.subplots(nrows=2, ncols=3, figsize=(12,8))
    a, b, c = uc_params[:3]

    def uc_param_hist2d(p1, p2, ax):
      nbins = 100
      import numpy as np
      H, xedges, yedges = np.histogram2d(p1, p2, bins=nbins)
      H = np.rot90(H)
      H = np.flipud(H)
      Hmasked = np.ma.masked_where(H==0, H)
      ax.pcolormesh(xedges, yedges, Hmasked)

    uc_param_hist2d(a, b, ax[0][0])
    uc_param_hist2d(b, c, ax[0][1])
    uc_param_hist2d(c, a, ax[0][2])

    for i in range(3):
      mmm = flex.min_max_mean_double(uc_params[i])
      import math
      steps_per_A = steps_per_angstrom
      Amin = math.floor(mmm.min * steps_per_A)/steps_per_A
      Amax = math.floor(mmm.max * steps_per_A)/steps_per_A
      n_slots = int((Amax - Amin) * steps_per_A)
      hist = flex.histogram(uc_params[i], Amin, Amax, n_slots=n_slots)
      hist_inliers = flex.histogram(
        uc_params[i].select(~outliers), Amin, Amax, n_slots=n_slots)
      ax[1][i].bar(
        hist.slot_centers(), hist.slots(), align='center',
        width=hist.slot_width(), zorder=10, color='black', edgecolor=None,
        linewidth=0)
      ax[1][i].bar(
        hist_inliers.slot_centers(), hist_inliers.slots(), align='center',
        width=hist_inliers.slot_width(), zorder=10, color='red', edgecolor=None,
        linewidth=0)

    ax[0][0].set_ylabel('b ($\AA$)')
    ax[0][1].set_ylabel('c ($\AA$)')
    ax[0][2].set_ylabel('a ($\AA$)')
    ax[1][0].set_xlabel('a ($\AA$)')
    ax[1][1].set_xlabel('b ($\AA$)')
    ax[1][2].set_xlabel('c ($\AA$)')

    f.savefig(plot_name)
    plt.tight_layout()
    plt.close(f)

  def cosym(self):

    # per-dataset change of basis operator to ensure all consistent

    cb_op_best_min = None
    change_of_basis_ops = []
    for i, expt in enumerate(self._data_manager.experiments):
      crystal_symmetry = expt.crystal.get_crystal_symmetry()
      metric_subgroups = sgtbx.lattice_symmetry.metric_subgroups(
        crystal_symmetry, max_delta=self._params.symmetry.le_page_max_delta)
      subgroup = metric_subgroups.result_groups[0]
      cb_op_inp_best = subgroup['cb_op_inp_best']
      crystal_symmetry_best = crystal_symmetry.change_basis(cb_op_inp_best)
      if cb_op_best_min is None:
        cb_op_best_min = crystal_symmetry_best.change_of_basis_op_to_niggli_cell()
      cb_op_inp_min = cb_op_best_min * cb_op_inp_best
      change_of_basis_ops.append(cb_op_inp_min)
    self._data_manager.reindex(
      cb_ops=change_of_basis_ops, space_group=sgtbx.space_group())

    miller_arrays = self._data_manager.reflections_as_miller_arrays(
      intensity_key='intensity.sum.value')

    miller_arrays_p1 = []
    for ma in miller_arrays:
      cb_op_to_primitive = ma.change_of_basis_op_to_primitive_setting()
      ma = ma.change_basis(cb_op_to_primitive)
      space_group_info = sgtbx.space_group_info('P1')
      ma = ma.customized_copy(space_group_info=space_group_info)
      ma = ma.merge_equivalents().array()
      miller_arrays_p1.append(ma)

    params = self._params.symmetry.cosym
    from xia2.lib import bits
    xpid = bits._get_number()
    params.plot_prefix = '%i_' % xpid

    result = cosym_analyse_datasets(miller_arrays_p1, params)

    space_groups = {}
    reindexing_ops = {}
    for dataset_id in result.reindexing_ops.iterkeys():
      if 0 in result.reindexing_ops[dataset_id]:
        cb_op = result.reindexing_ops[dataset_id][0]
        reindexing_ops.setdefault(cb_op, [])
        reindexing_ops[cb_op].append(dataset_id)
      if dataset_id in result.space_groups:
        space_groups.setdefault(result.space_groups[dataset_id], [])
        space_groups[result.space_groups[dataset_id]].append(dataset_id)

    logger.info('Space groups:')
    for sg, datasets in space_groups.iteritems():
      logger.info(str(sg.info().reference_setting()))
      logger.info(datasets)

    logger.info('Reindexing operators:')
    for cb_op, datasets in reindexing_ops.iteritems():
      logger.info(cb_op)
      logger.info(datasets)

    self._data_manager.reindex(cb_ops=reindexing_ops)

    return

  def multi_crystal_analysis(self, id_to_batches):

    result = any_reflection_file(self._scaled.scaled_unmerged_mtz)
    intensities = None
    batches = None

    for ma in result.as_miller_arrays(
      merge_equivalents=False, crystal_symmetry=None):
      if ma.info().labels == ['I(+)', 'SIGI(+)', 'I(-)', 'SIGI(-)']:
        assert ma.anomalous_flag()
        intensities = ma
      elif ma.info().labels == ['I', 'SIGI']:
        assert not ma.anomalous_flag()
        intensities = ma
      elif ma.info().labels == ['BATCH']:
        batches = ma

    assert batches is not None
    assert intensities is not None

    separate = separate_unmerged(
      intensities, batches, id_to_batches=id_to_batches)

    from xia2.lib import bits
    xpid = bits._get_number()
    prefix = '%i_' % xpid

    mca = multi_crystal_analysis(
      separate.intensities.values(),
      labels=separate.run_id_to_batch_id.values(),
      prefix=prefix
    )

    return mca


class Scale(object):
  def __init__(self, data_manager, params):
    self._data_manager = data_manager
    self._params = params

    # export reflections
    self._integrated_combined_mtz = self._data_manager.export_mtz(
      filename='integrated_combined.mtz')

    self.decide_space_group()

    self.two_theta_refine()

    #self.unit_cell_clustering(plot_name='cluster_unit_cell_sg.png')

    self.scale()

    d_min, reason = self.estimate_resolution_limit()

    logger.info('Resolution limit: %.2f (%s)' % (d_min, reason))

    self.scale(d_min=d_min)
    self.radiation_damage_analysis(d_min=d_min)

  def decide_space_group(self):
    if self._params.symmetry.program == 'pointless':
      space_group, reindex_op = self._decide_space_group_pointless()
    else:
      space_group, reindex_op = self._decide_space_group_dials()

  def refine(self):
    # refine in correct bravais setting
    self._experiments_filename, self._reflections_filename = self._dials_refine(
      self._experiments_filename, self._reflections_filename)
    self._data_manager.experiments = load.experiment_list(
      self._experiments_filename, check_format=False)
    self._data_manager.reflections = flex.reflection_table.from_pickle(
      self._reflections_filename)

  def two_theta_refine(self):
    # two-theta refinement to get best estimate of unit cell
    self.best_unit_cell, self.best_unit_cell_esd = self._dials_two_theta_refine(
      self._experiments_filename, self._reflections_filename)
    tools.patch_mtz_unit_cell(self._sorted_mtz, self.best_unit_cell)

  def scale(self, d_min=None):

    if self._params.scaling.program == 'aimless':
      # scale data with aimless
      scaled = self._scale_aimless(d_min=d_min)
    elif self._params.scaling.program == 'dials':
      scaled = self._scale_dials(d_min=d_min)
    return scaled

  @property
  def scaled_mtz(self):
    return self._scaled_mtz

  @property
  def scaled_unmerged_mtz(self):
    return self._scaled_unmerged_mtz

  @property
  def data_manager(self):
    return self._data_manager

  def _decide_space_group_pointless(self):
    logger.debug('Deciding space group with pointless')
    symmetry = Pointless()
    auto_logfiler(symmetry)

    self._sorted_mtz = '%i_sorted.mtz' % symmetry.get_xpid()
    self._experiments_filename = '%i_experiments_reindexed.json' % symmetry.get_xpid()
    self._reflections_filename = '%i_reflections_reindexed.pickle' % symmetry.get_xpid()

    symmetry.set_hklin(self._integrated_combined_mtz)
    symmetry.set_hklout(self._sorted_mtz)
    symmetry.set_allow_out_of_sequence_files(allow=True)
    symmetry.decide_pointgroup()
    space_group = sgtbx.space_group_info(
      symbol=str(symmetry.get_pointgroup())).group()
    cb_op =  sgtbx.change_of_basis_op(symmetry.get_reindex_operator())

    # reindex to correct bravais setting
    self._data_manager.reindex(cb_op=cb_op, space_group=space_group)
    self._data_manager.export_experiments(self._experiments_filename)
    self._data_manager.export_reflections(self._reflections_filename)

    logger.info('Space group determined by pointless: %s' % space_group.info())
    return space_group, cb_op

  def _decide_space_group_dials(self):
    logger.debug('Deciding space group with dials.symmetry')
    symmetry = DialsSymmetry()
    auto_logfiler(symmetry)

    self._sorted_mtz = '%i_sorted.mtz' % symmetry.get_xpid()
    self._experiments_filename = '%i_experiments_reindexed.json' % symmetry.get_xpid()
    self._reflections_filename = '%i_reflections_reindexed.pickle' % symmetry.get_xpid()

    experiments_filename = 'tmp_experiments.json'
    reflections_filename = 'tmp_reflections.pickle'
    self._data_manager.export_experiments(experiments_filename)
    self._data_manager.export_reflections(reflections_filename)

    symmetry.set_experiments_filename(experiments_filename)
    symmetry.set_reflections_filename(reflections_filename)
    symmetry.set_output_experiments_filename(self._experiments_filename)
    symmetry.set_output_reflections_filename(self._reflections_filename)
    symmetry.decide_pointgroup()
    space_group = sgtbx.space_group_info(
      symbol=str(symmetry.get_pointgroup())).group()
    cb_op =  sgtbx.change_of_basis_op(symmetry.get_reindex_operator())

    self._data_manager.experiments = load.experiment_list(
      self._experiments_filename, check_format=False)
    self._data_manager.reflections = flex.reflection_table.from_pickle(
      self._reflections_filename)
    # export reflections
    self._sorted_mtz = self._data_manager.export_mtz(
      filename=self._sorted_mtz)

    logger.info('Space group determined by dials.symmetry: %s' % space_group.info())
    return space_group, cb_op

  @staticmethod
  def _dials_refine(experiments_filename, reflections_filename):
    refiner = Refine()
    auto_logfiler(refiner)
    refiner.set_experiments_filename(experiments_filename)
    refiner.set_indexed_filename(reflections_filename)
    refiner.run()
    return refiner.get_refined_experiments_filename(), refiner.get_refined_filename()

  @staticmethod
  def _dials_two_theta_refine(experiments_filename, reflections_filename):
    tt_refiner = TwoThetaRefine()
    auto_logfiler(tt_refiner)
    tt_refiner.set_experiments([experiments_filename])
    tt_refiner.set_pickles([reflections_filename])
    tt_refiner.run()
    unit_cell = tt_refiner.get_unit_cell()
    unit_cell_esd = tt_refiner.get_unit_cell_esd()
    return unit_cell, unit_cell_esd

  def _scale_aimless(self, d_min=None):
    logger.debug('Scaling with aimless')
    PhilIndex.params.xia2.settings.multiprocessing.nproc = 1
    scaler = Aimless()
    auto_logfiler(scaler)
    self._scaled_mtz = '%i_scaled.mtz' % scaler.get_xpid()
    scaler.set_surface_link(False) # multi-crystal
    scaler.set_hklin(self._sorted_mtz)
    scaler.set_hklout(self._scaled_mtz)
    scaler.set_surface_tie(self._params.scaling.surface_tie)
    if self._params.scaling.secondary.frame == 'camera':
      secondary = 'secondary'
    else:
      secondary = 'absorption'
    lmax = self._params.scaling.secondary.lmax
    scaler.set_secondary(mode=secondary, lmax=lmax)
    scaler.set_spacing(self._params.scaling.rotation.spacing)
    if d_min is not None:
      scaler.set_resolution(d_min)
    scaler.scale()
    self._scaled_unmerged_mtz \
      = os.path.splitext(self._scaled_mtz)[0] + '_unmerged.mtz'
    return scaler

  def _scale_dials(self, d_min=None):
    logger.debug('Scaling with dials.scale')
    #PhilIndex.params.xia2.settings.multiprocessing.nproc = 1
    scaler = DialsScale()
    auto_logfiler(scaler)
    #scaler.set_surface_link(False) # multi-crystal
    scaler.add_experiments_json(self._experiments_filename)
    scaler.add_reflections_pickle(self._reflections_filename)
    #scaler.set_surface_tie(self._params.scaling.surface_tie)
    lmax = self._params.scaling.secondary.lmax
    if lmax:
      scaler.set_absorption_correction(True)
      scaler.set_lmax(lmax)
    else:
      scaler.set_absorption_correction(False)
    scaler.set_spacing(self._params.scaling.rotation.spacing)
    if d_min is not None:
      scaler.set_resolution(d_min)

    scaler.set_full_matrix(False)
    scaler.set_model(self._params.scaling.dials.model)
    scaler.set_outlier_rejection(self._params.scaling.dials.outlier_rejection)

    scaler.scale()
    self._scaled_mtz = scaler.get_scaled_mtz()
    self._scaled_unmerged_mtz = scaler.get_scaled_unmerged_mtz()
    self._experiments_filename = scaler.get_scaled_experiments()
    self._reflections_filename = scaler.get_scaled_reflections()
    DataManager.experiments = load.experiment_list(
      self._experiments_filename, check_format=False)
    DataManager.reflections = flex.reflection_table.from_pickle(
      self._reflections_filename)
    self._params.resolution.labels = 'IPR,SIGIPR'
    return scaler

  def estimate_resolution_limit(self):
    # see also xia2/Modules/Scaler/CommonScaler.py: CommonScaler._estimate_resolution_limit()
    from xia2.Wrappers.XIA.Merger import Merger
    params = self._params.resolution
    m = Merger()
    auto_logfiler(m)
    m.set_hklin(self._scaled_unmerged_mtz)
    m.set_limit_rmerge(params.rmerge)
    m.set_limit_completeness(params.completeness)
    m.set_limit_cc_half(params.cc_half)
    m.set_cc_half_fit(params.cc_half_fit)
    m.set_cc_half_significance_level(params.cc_half_significance_level)
    m.set_limit_isigma(params.isigma)
    m.set_limit_misigma(params.misigma)
    m.set_labels(params.labels)
    #if batch_range is not None:
      #start, end = batch_range
      #m.set_batch_range(start, end)
    m.run()

    resolution_limits = []
    reasoning = []

    if params.completeness is not None:
      r_comp = m.get_resolution_completeness()
      resolution_limits.append(r_comp)
      reasoning.append('completeness > %s' % params.completeness)

    if params.cc_half is not None:
      r_cc_half = m.get_resolution_cc_half()
      resolution_limits.append(r_cc_half)
      reasoning.append('cc_half > %s' % params.cc_half)

    if params.rmerge is not None:
      r_rm = m.get_resolution_rmerge()
      resolution_limits.append(r_rm)
      reasoning.append('rmerge > %s' % params.rmerge)

    if params.isigma is not None:
      r_uis = m.get_resolution_isigma()
      resolution_limits.append(r_uis)
      reasoning.append('unmerged <I/sigI> > %s' % params.isigma)

    if params.misigma is not None:
      r_mis = m.get_resolution_misigma()
      resolution_limits.append(r_mis)
      reasoning.append('merged <I/sigI> > %s' % params.misigma)

    if len(resolution_limits):
      resolution = max(resolution_limits)
      reasoning = [
          reason for limit, reason in zip(resolution_limits, reasoning)
          if limit >= resolution
      ]
      reasoning = ', '.join(reasoning)
    else:
      resolution = 0.0
      reasoning = None

    return resolution, reasoning

  def radiation_damage_analysis(self, d_min=None):
    from xia2.Modules.PyChef2.PyChef import Statistics

    if d_min is None:
      d_min = PyChef.resolution_limit(
        mtz_file=self.unmerged_mtz, min_completeness=self.params.chef_min_completeness, n_bins=8)
      logger.info('Estimated d_min for CHEF analysis: %.2f' % d_min)
    miller_arrays = self._data_manager.reflections_as_miller_arrays(
      return_batches=True)
    for i, (intensities, batches) in enumerate(miller_arrays):
      # convert batches to dose
      data = batches.data() - self._data_manager.experiments[i].scan.get_batch_offset()
      miller_arrays[i][1] = batches.array(data=data).set_info(batches.info())
    intensities, dose = miller_arrays[0]
    for (i, d) in miller_arrays[1:]:
      intensities = intensities.concatenate(i)
      dose = dose.concatenate(d)

    intensities = intensities.resolution_filter(d_min=d_min)
    dose = dose.resolution_filter(d_min=d_min)
    stats = Statistics(intensities, dose.data())

    stats.print_completeness_vs_dose()
    stats.print_rcp_vs_dose()
    stats.print_scp_vs_dose()
    stats.print_rd_vs_dose()

    with open('chef.json', 'wb') as f:
      import json
      json.dump(stats.to_dict(), f)

if __name__ == "__main__":
  run()
