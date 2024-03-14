from __future__ import annotations

import copy
import logging
import os
from collections import OrderedDict

import iotbx.phil
from cctbx import sgtbx, uctbx
from dials.array_family import flex
from dials.command_line.unit_cell_histogram import plot_uc_histograms
from dials.util import tabulate
from dials.util.export_mtz import match_wavelengths
from dials.util.mp import available_cores
from dxtbx.serialize import load
from libtbx import Auto
from scitbx.math import five_number_summary

from xia2.Handlers.Phil import PhilIndex
from xia2.lib.bits import auto_logfiler
from xia2.Modules import Report
from xia2.Modules.MultiCrystal.data_manager import DataManager
from xia2.Modules.MultiCrystalAnalysis import MultiCrystalAnalysis
from xia2.Modules.Scaler.DialsScaler import (
    convert_merged_mtz_to_sca,
    convert_unmerged_mtz_to_sca,
    scaling_model_auto_rules,
)
from xia2.Wrappers.Dials.Cosym import DialsCosym
from xia2.Wrappers.Dials.EstimateResolution import EstimateResolution
from xia2.Wrappers.Dials.Refine import Refine
from xia2.Wrappers.Dials.Reindex import Reindex
from xia2.Wrappers.Dials.Scale import DialsScale
from xia2.Wrappers.Dials.Symmetry import DialsSymmetry
from xia2.Wrappers.Dials.TwoThetaRefine import TwoThetaRefine

logger = logging.getLogger(__name__)


# The phil scope
phil_scope = iotbx.phil.parse(
    """
unit_cell_clustering
  .short_caption = "Unit cell clustering"
{
  threshold = 5000
    .type = float(value_min=0)
    .help = 'Threshold value for the clustering'
  log = False
    .type = bool
    .help = 'Display the dendrogram with a log scale'
}

scaling
  .short_caption = "Scaling"
{
  anomalous = False
    .help = "Separate anomalous pairs in scaling and error model optimisation."
    .type = bool
  rotation.spacing = None
    .type = int
    .expert_level = 2
    .short_caption = "Interval (in degrees) between scale factors on rotation axis"
  brotation.spacing = None
    .type = int
    .expert_level = None
    .short_caption = "Interval (in degrees) between B-factors on rotation axis"
  secondary {
    lmax = 0
      .type = int
      .expert_level = 2
      .short_caption = "Number of spherical harmonics for absorption correction"
    share.absorption = False
      .type = bool
      .expert_level = 2
      .short_caption = "Shared absorption correction"
      .help = "Apply a shared absorption correction between sweeps. Only"
              "suitable for scaling measurements from a single crystal."
  }
  absorption_level = low medium high
    .type = choice
    .expert_level = 2
    .help = "Set the extent of absorption correction in scaling"
    .short_caption = "Absorption level"
  model = physical dose_decay array KB *auto
    .type = choice
    .short_caption = "Scaling model"
  outlier_rejection = simple standard
    .type = choice
    .short_caption = "Outlier rejection"
  min_partiality = None
    .type = float(value_min=0, value_max=1)
    .short_caption = "Minimum partiality"
  partiality_cutoff = None
    .type = float(value_min=0, value_max=1)
    .short_caption = "Partiality cutoff"
  reflection_selection
    .short_caption = "Reflection selection"
  {
    method = quasi_random intensity_ranges use_all random
      .type = choice
      .help = "Method to use when choosing a reflection subset for scaling model"
              "minimisation."
              "The quasi_random option randomly selects reflections groups"
              "within a dataset, and also selects groups which have good"
              "connectedness across datasets for multi-dataset cases. The random"
              "option selects reflection groups randomly for both single"
              "and multi dataset scaling, so for a single dataset"
              "quasi_random == random."
              "The intensity_ranges option uses the E2_range, Isigma_range and"
              "d_range options to the subset of reflections"
              "The use_all option uses all suitable reflections, which may be"
              "slow for large datasets."
    Isigma_range = None
      .type = floats(size=2)
      .short_caption = "I/σ range"
      .help = "Minimum and maximum I/sigma values used to select a subset of"
              "reflections for minimisation. A value of 0.0 for the maximum"
              "indicates that no upper limit should be applied."
  }
}
symmetry
  .short_caption = "Symmetry"
{
  resolve_indexing_ambiguity = True
    .type = bool
    .short_caption = "Resolve indexing ambiguity"
  cosym {
    include scope dials.algorithms.symmetry.cosym.phil_scope
  }
  laue_group = None
    .type = space_group
    .help = "Specify the Laue group. If None, then the Laue group will be determined"
            "by dials.cosym."
    .short_caption = "Laue group"
  space_group = None
    .type = space_group
    .help = "Specify the space group. If None, then the dials.symmetry will perform"
            "analysis of systematically absent reflections to determine the space group."
    .short_caption = "Space group"
}

reference = None
    .type = path
    .help = "A file containing a reference set of intensities e.g. MTZ/cif, or a"
            "file from which a reference set of intensities can be calculated"
            "e.g. .pdb or .cif . The space group of the reference file will"
            "be used and if an indexing ambiguity is present, the input"
            "data will be reindexed to be consistent with the indexing mode of"
            "this reference file."
    .expert_level = 2

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
  include scope dials.util.resolution_analysis.phil_str
}

rescale_after_resolution_cutoff = False
  .help = "Re-scale the data after application of a resolution cutoff"
  .type = bool
  .short_caption = "Rescale after resolution cutoff"

filtering
  .short_caption = "Filtering"
{

  method = None deltacchalf
    .type = choice
    .help = "Choice of whether to do any filtering cycles, default None."

  deltacchalf
    .short_caption = "ΔCC½"
  {
    max_cycles = None
      .type = int(value_min=1)
      .short_caption = "Maximum number of cycles"
    max_percent_removed = None
      .type = float
      .short_caption = "Maximum percentage removed"
    min_completeness = None
      .type = float(value_min=0, value_max=100)
      .help = "Desired minimum completeness, as a percentage (0 - 100)."
      .short_caption = "Minimum completeness"
    mode = dataset image_group
      .type = choice
      .help = "Perform analysis on whole datasets or batch groups"
    group_size = None
      .type = int(value_min=1)
      .help = "The number of images to group together when calculating delta"
              "cchalf in image_group mode"
      .short_caption = "Group size"
    stdcutoff = None
      .type = float
      .help = "Datasets with a ΔCC½ below (mean - stdcutoff*std) are removed"
      .short_caption = "Standard deviation cutoff"
  }
}

multi_crystal_analysis {
  include scope xia2.Modules.MultiCrystal.master_phil_scope
}

unit_cell
  .short_caption = "Unit cell"
{
  refine = *two_theta
    .type = choice(multi=True)
}

two_theta_refine
  .short_caption = "2θ refinement"
{
  combine_crystal_models = True
    .type = bool
    .short_caption = "Combine crystal models"
}


clustering
  .short_caption = "Clustering"
{
  output_clusters = False
    .type = bool
    .help = "Set this to true to enable scaling and merging of individual clusters"
    .short_caption = "Output individual clusters"
  method = *cos_angle correlation
    .type = choice(multi=True)
    .short_caption = "Metric on which to perform clustering"
  min_completeness = 0
    .type = float(value_min=0, value_max=1)
    .short_caption = "Minimum completeness"
  min_multiplicity = 0
    .type = float(value_min=0)
    .short_caption = "Minimum multiplicity"
  max_output_clusters = 10
    .type = int(value_min=1)
    .short_caption = "Maximum number of clusters to be output"
  min_cluster_size = 2
    .type = int
    .short_caption = "Minimum number of datasets for a cluster"
  max_cluster_height = 100
    .type = float
    .short_caption = "Maximum height in dendrogram for clusters"
  max_cluster_height_cc = 100
    .type = float
    .short_caption = "Maximum height in correlation dendrogram for clusters"
  max_cluster_height_cos = 100
    .type = float
    .short_caption = "Maximum height in cos angle dendrogram for clusters"
  analysis = False
    .type = bool
    .help = "This will determine whether optional cluster analysis is undertaken."
            "To assist in decreasing computation time, only clusters that appear"
            "scientifically interesting to compare will be scaled and merged."
            "Pairs of clusters that are interesting to compare are currently"
            "defined as two clusters with no datasets in common that eventually"
            "join on the output dendrogram."
    .short_caption = "Cluster Analysis"
}

identifiers = None
  .type = strings
  .short_caption = "Identifiers"

dose = None
  .type = ints(size=2, value_min=0)
  .short_caption = "Dose"

nproc = Auto
  .type = int(value_min=1)
  .help = "The number of processors to use"
  .expert_level = 0
remove_profile_fitting_failures = True
  .type = bool
  .short_caption = "Remove profile fitting failures"

include scope dials.algorithms.merging.merge.r_free_flags_phil_scope

""",
    process_includes=True,
)

# the phil scope which used to live in xia2.multi_crystal_analysis
mca_phil = iotbx.phil.parse(
    """
include scope xia2.cli.report.phil_scope

seed = 42
  .type = int(value_min=0)

unit_cell_clustering {
  threshold = 5000
    .type = float(value_min=0)
    .help = 'Threshold value for the clustering'
  log = False
    .type = bool
    .help = 'Display the dendrogram with a log scale'
}

output {
  log = xia2.multi_crystal_analysis.log
    .type = str
}
""",
    process_includes=True,
)

# override default parameters
phil_scope = phil_scope.fetch(
    source=iotbx.phil.parse(
        """\
resolution {
  cc_half_method = sigma_tau
  cc_half_fit = tanh
  cc_half = 0.3
  isigma = None
  misigma = None
}
symmetry.cosym.best_monoclinic_beta = False
"""
    )
)


class MultiCrystalScale:
    def __init__(self, experiments, reflections, params):

        self._data_manager = DataManager(experiments, reflections)

        self._params = params
        if all([params.symmetry.laue_group, params.symmetry.space_group]):
            raise ValueError("Can not specify both laue_group and space_group")

        if self._params.nproc is Auto:
            self._params.nproc = available_cores()
        PhilIndex.params.xia2.settings.multiprocessing.nproc = self._params.nproc

        if self._params.identifiers is not None:
            self._data_manager.select(self._params.identifiers)
        if self._params.dose is not None:
            self._data_manager.filter_dose(*self._params.dose)

        if params.remove_profile_fitting_failures:
            reflections = self._data_manager.reflections
            profile_fitted_mask = reflections.get_flags(
                reflections.flags.integrated_prf
            )
            keep_expts = []
            for i, expt in enumerate(self._data_manager.experiments):
                refl_used = reflections.select(profile_fitted_mask)
                if (
                    expt.identifier in refl_used.experiment_identifiers().values()
                    and refl_used.select_on_experiment_identifiers(
                        [expt.identifier]
                    ).size()
                ):
                    keep_expts.append(expt.identifier)
            if len(keep_expts):
                logger.info(
                    "Selecting %i experiments with profile-fitted reflections"
                    % len(keep_expts)
                )
                self._data_manager.select(keep_expts)

        reflections = self._data_manager.reflections
        used_in_refinement_mask = reflections.get_flags(
            reflections.flags.used_in_refinement
        )
        keep_expts = []
        for i, expt in enumerate(self._data_manager.experiments):
            refl_used = reflections.select(used_in_refinement_mask)
            if (
                expt.identifier in refl_used.experiment_identifiers().values()
                and refl_used.select_on_experiment_identifiers([expt.identifier]).size()
            ):
                keep_expts.append(expt.identifier)
            else:
                logger.info(
                    "Removing experiment %s (no refined reflections remaining)"
                    % expt.identifier
                )
        if len(keep_expts):
            logger.info(
                "Selecting %i experiments with refined reflections" % len(keep_expts)
            )
            self._data_manager.select(keep_expts)

        self.unit_cell_clustering(plot_name="cluster_unit_cell_p1.png")

        if self._params.symmetry.resolve_indexing_ambiguity:
            self.cosym()

        self._individual_report_dicts = OrderedDict()
        self._comparison_graphs = OrderedDict()

        self._scaled = Scale(self._data_manager, self._params)
        self._experiments_filename = self._scaled._experiments_filename
        self._reflections_filename = self._scaled._reflections_filename

        if self._params.reference is not None:
            self.reindex()
        else:
            self.decide_space_group()

        d_spacings = self._scaled.data_manager._reflections["d"]
        self._params.r_free_flags.d_min = flex.min(d_spacings.select(d_spacings > 0))
        self._params.r_free_flags.d_max = flex.max(d_spacings)
        self._data_manager.export_experiments("scaled.expt")
        self._data_manager.export_reflections("scaled.refl", d_min=self._scaled.d_min)
        # by default, extend=True, i.e. we want to extend to the full resolution range once we have a reference
        free_flags_in_full_set = False
        if self._params.r_free_flags.reference:
            free_flags_in_full_set = (
                True  # will be after this first export if extend=True.
            )
        self._data_manager.export_merged_mtz(
            "scaled.mtz",
            d_min=self._scaled.d_min,
            r_free_params=self._params.r_free_flags,
            wavelength_tolerance=self._params.wavelength_tolerance,
        )
        # whether there was an external reference or not, we can use the scaled.mtz going forward for the reference rfree
        self._params.r_free_flags.reference = os.path.join(os.getcwd(), "scaled.mtz")
        # however, if extend=True, we will need to record the next merged mtz as the reference going forward.

        self.wavelengths = match_wavelengths(
            self._data_manager.experiments, self._params.wavelength_tolerance
        )  # in experiments order

        if len(self.wavelengths) > 1:
            identifiers_list = list(self._data_manager.experiments.identifiers())
            logger.info(
                "Multiple wavelengths found, wavelengths will be grouped for MTZ writing: \n%s",
                "\n".join(
                    f"  Wavlength range: {v.min_wl:.5f} - {v.max_possible_wl:.5f}, experiment numbers: %s "
                    % (
                        ",".join(
                            map(str, [identifiers_list.index(i) for i in v.identifiers])
                        )
                    )
                    for v in self.wavelengths.values()
                ),
            )
            self._data_manager.split_by_wavelength(self._params.wavelength_tolerance)
            for wl in self.wavelengths:
                name = self._data_manager.export_unmerged_wave_mtz(
                    wl,
                    "scaled_unmerged",
                    d_min=self._scaled.d_min,
                    wavelength_tolerance=self._params.wavelength_tolerance,
                )
                convert_unmerged_mtz_to_sca(name)
            # now export merged of each
            for wl in self.wavelengths:
                name = self._data_manager.export_merged_wave_mtz(
                    wl,
                    "scaled",
                    d_min=self._scaled.d_min,
                    r_free_params=self._params.r_free_flags,
                    wavelength_tolerance=self._params.wavelength_tolerance,
                )
                convert_merged_mtz_to_sca(name)
        else:
            self._data_manager.export_unmerged_mtz(
                "scaled_unmerged.mtz",
                d_min=self._scaled.d_min,
                wavelength_tolerance=self._params.wavelength_tolerance,
            )
            convert_merged_mtz_to_sca("scaled.mtz")
            convert_unmerged_mtz_to_sca("scaled_unmerged.mtz")

        self._record_individual_report(
            self._data_manager, self._scaled.report(), "All data"
        )

        self._mca = self.multi_crystal_analysis()
        self.cluster_analysis()

        min_completeness = self._params.clustering.min_completeness
        min_multiplicity = self._params.clustering.min_multiplicity
        max_clusters = self._params.clustering.max_output_clusters
        min_cluster_size = self._params.clustering.min_cluster_size
        max_cluster_height_cos = self._params.clustering.max_cluster_height_cos
        max_cluster_height_cc = self._params.clustering.max_cluster_height_cc
        max_cluster_height = self._params.clustering.max_cluster_height

        if self._params.clustering.method[0] == "cos_angle":
            clusters = self._cos_angle_clusters
            ctype = ["cos" for i in clusters]
        elif self._params.clustering.method[0] == "correlation":
            clusters = self._cc_clusters
            ctype = ["cc" for i in clusters]
        elif self._params.clustering.method == ["cos_angle", "correlation"]:
            clusters = self._cos_angle_clusters + self._cc_clusters
            ctype = ["cos" for i in self._cos_angle_clusters] + [
                "cc" for i in self._cc_clusters
            ]
        else:
            raise ValueError(
                "Invalid cluster method: %s" % self._params.clustering.method
            )

        clusters.reverse()
        ctype.reverse()
        self.cos_clusters = []
        self.cc_clusters = []
        self.cos_cluster_ids = {}
        self.cc_cluster_ids = {}

        if self._params.clustering.output_clusters:
            self._data_manager_original = self._data_manager
            cwd = os.path.abspath(os.getcwd())
            n_processed_cos = 0
            n_processed_cc = 0

            for c, cluster in zip(ctype, clusters):

                logger.info("HELLO THERE")
                logger.info(c)
                logger.info(cluster)

                # This simplifies max_cluster_height into cc and cos angle versions
                # But still gives the user the option of just selecting max_cluster_height
                # Which makes more sense when they only want one type of clustering

                if (
                    c == "cc"
                    and max_cluster_height != 100
                    and max_cluster_height_cc == 100
                ):
                    max_cluster_height_cc = max_cluster_height
                    # if user has weirdly set both max_cluster_height and max_cluster_height_cc
                    # will still default to max_cluster_height_cc as intended
                if (
                    c == "cos"
                    and max_cluster_height != 100
                    and max_cluster_height_cos == 100
                ):
                    max_cluster_height_cos = max_cluster_height

                if n_processed_cos == max_clusters and c == "cos":
                    logger.info("1")
                    continue
                if n_processed_cc == max_clusters and c == "cc":
                    logger.info("2")
                    continue
                if cluster.completeness < min_completeness:
                    logger.info("3")
                    continue
                if cluster.multiplicity < min_multiplicity:
                    logger.info("4")
                    continue
                if len(cluster.labels) == len(self._data_manager_original.experiments):
                    logger.info("5")
                    continue
                if cluster.height > max_cluster_height_cc and c == "cc":
                    logger.info("6")
                    continue
                if cluster.height > max_cluster_height_cos and c == "cos":
                    logger.info("7")
                    continue
                if len(cluster.labels) < min_cluster_size:
                    logger.info("8")
                    continue

                data_manager = copy.deepcopy(self._data_manager_original)
                cluster_identifiers = [
                    data_manager.ids_to_identifiers_map[l] for l in cluster.labels
                ]

                if self._params.clustering.analysis:
                    if c == "cos":
                        self.cos_clusters.append(cluster)
                        self.cos_cluster_ids[cluster.cluster_id] = cluster_identifiers
                    elif c == "cc":
                        self.cc_clusters.append(cluster)
                        self.cc_cluster_ids[cluster.cluster_id] = cluster_identifiers

                else:
                    if c == "cos":
                        n_processed_cos += 1
                    elif c == "cc":
                        n_processed_cc += 1

                    if c == "cos":
                        logger.info("Scaling cos cluster %i:" % cluster.cluster_id)
                        logger.info(cluster)
                        cluster_dir = "cos_cluster_%i" % cluster.cluster_id
                    elif c == "cc":
                        logger.info("Scaling cc cluster %i:" % cluster.cluster_id)
                        logger.info(cluster)
                        cluster_dir = "cc_cluster_%i" % cluster.cluster_id

                    if not os.path.exists(cluster_dir):
                        os.mkdir(cluster_dir)
                    os.chdir(cluster_dir)

                    scaled = self.scale_cluster(
                        data_manager,
                        cluster_identifiers,
                        free_flags_in_full_set,
                    )
                    self._record_individual_report(
                        data_manager, scaled.report(), cluster_dir.replace("_", " ")
                    )
                    os.chdir(cwd)

        if self._params.clustering.analysis:

            for k, clusters in enumerate([self.cos_clusters, self.cc_clusters]):
                if k == 0:
                    cty = "cos"
                elif k == 1:
                    cty = "cc"
                logger.info("----------------------")
                logger.info(f"{cty} cluster analysis")
                logger.info("----------------------")

                (
                    file_data,
                    list_of_clusters,
                ) = MultiCrystalAnalysis.interesting_cluster_identification(
                    clusters, self._params
                )

                if len(list_of_clusters) > 0:
                    for item in list_of_clusters:
                        if k == 0:
                            cluster_dir = "cos_" + item
                        elif k == 1:
                            cluster_dir = "cc_" + item
                        if not os.path.exists(cluster_dir):
                            os.mkdir(cluster_dir)
                        os.chdir(cluster_dir)
                        logger.info("Scaling: %s" % cluster_dir)
                        free_flags_in_full_set = True

                        for cluster in clusters:
                            if "cluster_" + str(cluster.cluster_id) == item:
                                if k == 0:
                                    ids = self.cos_cluster_ids[cluster.cluster_id]
                                elif k == 1:
                                    ids = self.cc_cluster_ids[cluster.cluster_id]

                                scaled = self.scale_cluster(
                                    data_manager, ids, free_flags_in_full_set
                                )
                                self._record_individual_report(
                                    data_manager,
                                    scaled.report(),
                                    cluster_dir.replace("_", " "),
                                )
                        os.chdir("..")

        if self._params.filtering.method:
            # Final round of scaling, this time filtering out any bad datasets
            data_manager = copy.deepcopy(self._data_manager)
            params = copy.deepcopy(self._params)
            params.unit_cell.refine = []
            params.resolution.d_min = self._params.resolution.d_min
            scaled = Scale(data_manager, params, filtering=True)
            self.scale_and_filter_results = scaled.scale_and_filter_results
            logger.info("Scale and filtering:\n%s", self.scale_and_filter_results)

            data_manager.export_merged_mtz(
                "filtered.mtz",
                d_min=scaled.d_min,
                r_free_params=self._params.r_free_flags,
                wavelength_tolerance=self._params.wavelength_tolerance,
            )
            if (not free_flags_in_full_set) and (
                self._params.r_free_flags.extend is True
            ):
                self._params.r_free_flags.reference = os.path.join(
                    os.getcwd(), "filtered.mtz"
                )
                free_flags_in_full_set = True

            if len(self.wavelengths) > 1:
                data_manager.split_by_wavelength(self._params.wavelength_tolerance)
                for wl in self.wavelengths:
                    name = data_manager.export_unmerged_wave_mtz(
                        wl,
                        "filtered_unmerged",
                        d_min=scaled.d_min,
                        wavelength_tolerance=self._params.wavelength_tolerance,
                    )
                    if name:
                        convert_unmerged_mtz_to_sca(name)
                # now export merged of each
                for wl in self.wavelengths:
                    name = data_manager.export_merged_wave_mtz(
                        wl,
                        "filtered",
                        d_min=scaled.d_min,
                        r_free_params=self._params.r_free_flags,
                        wavelength_tolerance=self._params.wavelength_tolerance,
                    )
                    if name:
                        convert_merged_mtz_to_sca(name)
            else:
                data_manager.export_unmerged_mtz(
                    "filtered_unmerged.mtz",
                    d_min=scaled.d_min,
                    wavelength_tolerance=self._params.wavelength_tolerance,
                )
                convert_merged_mtz_to_sca("filtered.mtz")
                convert_unmerged_mtz_to_sca("filtered_unmerged.mtz")

            self._record_individual_report(data_manager, scaled.report(), "Filtered")
            data_manager.export_experiments("filtered.expt")
            data_manager.export_reflections("filtered.refl", d_min=scaled.d_min)
        else:
            self.scale_and_filter_results = None

        self.report()

    def scale_cluster(self, data_manager_input, identifiers, free_flags_in_full_set):
        data_manager = copy.deepcopy(data_manager_input)
        data_manager.select(identifiers)

        scaled = Scale(data_manager, self._params)
        data_manager.export_experiments("scaled.expt")
        data_manager.export_reflections("scaled.refl", d_min=scaled.d_min)

        # if we didn't have an external reference for the free_flags set, we need to make
        # and record one here.

        data_manager.export_merged_mtz(
            "scaled.mtz",
            d_min=scaled.d_min,
            r_free_params=self._params.r_free_flags,
            wavelength_tolerance=self._params.wavelength_tolerance,
        )
        if (not free_flags_in_full_set) and (self._params.r_free_flags.extend is True):
            self._params.r_free_flags.reference = os.path.join(
                os.getcwd(), "scaled.mtz"
            )
            free_flags_in_full_set = True

        if len(self.wavelengths) > 1:
            data_manager.split_by_wavelength(self._params.wavelength_tolerance)
            for wl in self.wavelengths:
                name = data_manager.export_unmerged_wave_mtz(
                    wl,
                    "scaled_unmerged",
                    d_min=scaled.d_min,
                    wavelength_tolerance=self._params.wavelength_tolerance,
                )
                if name:
                    convert_unmerged_mtz_to_sca(name)
            for wl in self.wavelengths:
                name = data_manager.export_merged_wave_mtz(
                    wl,
                    "scaled",
                    d_min=scaled.d_min,
                    r_free_params=self._params.r_free_flags,
                    wavelength_tolerance=self._params.wavelength_tolerance,
                )
                if name:
                    convert_merged_mtz_to_sca(name)
        else:
            data_manager.export_unmerged_mtz(
                "scaled_unmerged.mtz",
                d_min=scaled.d_min,
                wavelength_tolerance=self._params.wavelength_tolerance,
            )
            convert_merged_mtz_to_sca("scaled.mtz")
            convert_unmerged_mtz_to_sca("scaled_unmerged.mtz")

        return scaled

    def _record_individual_report(self, data_manager, report, cluster_name):
        d = self._report_as_dict(report)

        self._individual_report_dicts[cluster_name] = self._individual_report_dict(
            d, cluster_name
        )

        self._comparison_graphs.setdefault(
            "radar",
            {
                "data": [],
                "layout": {
                    "polar": {
                        "radialaxis": {
                            "visible": True,
                            "showticklabels": False,
                            "range": [0, 1],
                        }
                    }
                },
            },
        )

        self._comparison_graphs["radar"]["data"].append(
            {
                "type": "scatterpolar",
                "r": [],
                "theta": [],
                "fill": "toself",
                "name": cluster_name,
            }
        )

        for k, text in (
            ("cc_one_half", "CC½"),
            ("mean_redundancy", "Multiplicity"),
            ("completeness", "Completeness"),
            ("i_over_sigma_mean", "I/σ(I)"),
        ):
            self._comparison_graphs["radar"]["data"][-1]["r"].append(
                getattr(report.merging_stats.overall, k)
            )
            self._comparison_graphs["radar"]["data"][-1]["theta"].append(text)

        self._comparison_graphs["radar"]["data"][-1]["r"].append(
            uctbx.d_as_d_star_sq(report.merging_stats.overall.d_min)
        )
        self._comparison_graphs["radar"]["data"][-1]["theta"].append("Resolution")

        for graph in (
            "cc_one_half",
            "i_over_sig_i",
            "completeness",
            "multiplicity_vs_resolution",
            "r_pim",
        ):
            self._comparison_graphs.setdefault(
                graph, {"layout": d[graph]["layout"], "data": []}
            )
            data = copy.deepcopy(d[graph]["data"][0])
            data["name"] = cluster_name
            data.pop("line", None)  # remove default color override
            self._comparison_graphs[graph]["data"].append(data)

        def remove_html_tags(table):
            return [
                [
                    s.replace("<strong>", "")
                    .replace("</strong>", "")
                    .replace("<sub>", "")
                    .replace("</sub>", "")
                    if isinstance(s, str)
                    else s
                    for s in row
                ]
                for row in table
            ]

        logger.info(
            "\nOverall merging statistics:\n%s",
            tabulate(
                remove_html_tags(d["overall_statistics_table"]), headers="firstrow"
            ),
        )
        logger.info(
            "\nResolution shells:\n%s",
            tabulate(
                remove_html_tags(d["merging_statistics_table"]), headers="firstrow"
            ),
        )

    @staticmethod
    def _report_as_dict(report):
        (
            overall_stats_table,
            merging_stats_table,
            stats_plots,
        ) = report.resolution_plots_and_stats()

        if report.params.anomalous:
            stats_plots.update(report.dano_plots())
        d = {
            "merging_statistics_table": merging_stats_table,
            "overall_statistics_table": overall_stats_table,
        }

        d.update(stats_plots)
        d.update(report.batch_dependent_plots())
        d.update(report.intensity_stats_plots())
        d.update(report.pychef_plots())

        xtriage_success, xtriage_warnings, xtriage_danger = report.xtriage_report()
        d["xtriage"] = {
            "success": xtriage_success,
            "warnings": xtriage_warnings,
            "danger": xtriage_danger,
        }
        d["merging_stats"] = report.merging_stats.as_dict()
        d["merging_stats_anom"] = report.merging_stats.as_dict()

        max_points = 500
        for g in (
            "scale_rmerge_vs_batch",
            "completeness_vs_dose",
            "rcp_vs_dose",
            "scp_vs_dose",
            "rd_vs_batch_difference",
        ):
            for i, data in enumerate(d[g]["data"]):
                n = len(data["x"])
                if n > max_points:
                    step = n // max_points
                    sel = (flex.int_range(n) % step) == 0
                    data["x"] = list(flex.int(data["x"]).select(sel))
                    data["y"] = list(flex.double(data["y"]).select(sel))
                    if "text" in data:
                        data["text"] = list(flex.std_string(data["text"]).select(sel))

        d.update(report.multiplicity_plots())
        return d

    @staticmethod
    def _individual_report_dict(report_d, cluster_name):
        cluster_name = cluster_name.replace(" ", "_")
        d = {
            "merging_statistics_table": report_d["merging_statistics_table"],
            "overall_statistics_table": report_d["overall_statistics_table"],
            "image_range_table": report_d["image_range_table"],
        }

        resolution_graphs = OrderedDict(
            (k + "_" + cluster_name, report_d[k])
            for k in (
                "cc_one_half",
                "i_over_sig_i",
                "second_moments",
                "wilson_intensity_plot",
                "completeness",
                "multiplicity_vs_resolution",
                "dano",
            )
            if k in report_d
        )

        batch_graphs = OrderedDict(
            (k + "_" + cluster_name, report_d[k])
            for k in (
                "scale_rmerge_vs_batch",
                "i_over_sig_i_vs_batch",
                "completeness_vs_dose",
                "rcp_vs_dose",
                "scp_vs_dose",
                "rd_vs_batch_difference",
            )
        )

        misc_graphs = OrderedDict(
            (k + "_" + cluster_name, report_d[k])
            for k in ("cumulative_intensity_distribution", "l_test", "multiplicities")
            if k in report_d
        )

        for hkl in "hkl":
            misc_graphs["multiplicity_" + hkl + "_" + cluster_name] = {
                "img": report_d["multiplicity_" + hkl]
            }

        d["resolution_graphs"] = resolution_graphs
        d["batch_graphs"] = batch_graphs
        d["misc_graphs"] = misc_graphs
        d["xtriage"] = report_d["xtriage"]
        d["merging_stats"] = report_d["merging_stats"]
        d["merging_stats_anom"] = report_d["merging_stats_anom"]
        return d

    def unit_cell_clustering(self, plot_name=None):
        lattice_ids = [
            self._data_manager.identifiers_to_ids_map[i]
            for i in self._data_manager.experiments.identifiers()
        ]

        clustering = MultiCrystalAnalysis.unit_cell_clustering(
            self._data_manager.experiments,
            lattice_ids=lattice_ids,
            threshold=self._params.unit_cell_clustering.threshold,
            log=self._params.unit_cell_clustering.log,
            plot_name=plot_name,
        )
        logger.info(clustering)
        largest_cluster = sorted(clustering.clusters, key=len)[-1]

        if len(largest_cluster) < len(self._data_manager.experiments):
            logger.info(
                "Selecting subset of data sets for subsequent analysis: %s"
                % str(largest_cluster.lattice_ids)
            )
            cluster_identifiers = [
                self._data_manager.ids_to_identifiers_map[l]
                for l in largest_cluster.lattice_ids
            ]
            self._data_manager.select(cluster_identifiers)
        else:
            logger.info("Using all data sets for subsequent analysis")

    def unit_cell_histogram(self, plot_name=None):

        uc_params = [flex.double() for i in range(6)]
        for expt in self._data_manager.experiments:
            uc = expt.crystal.get_unit_cell()
            for i in range(6):
                uc_params[i].append(uc.parameters()[i])

        iqr_ratio = 1.5
        outliers = flex.bool(uc_params[0].size(), False)
        for p in uc_params:
            min_x, q1_x, med_x, q3_x, max_x = five_number_summary(p)
            logger.info(
                "Five number summary: min %.2f, q1 %.2f, med %.2f, q3 %.2f, max %.2f"
                % (min_x, q1_x, med_x, q3_x, max_x)
            )
            iqr_x = q3_x - q1_x
            if iqr_x < 1e-6:
                continue
            cut_x = iqr_ratio * iqr_x
            outliers.set_selected(p > q3_x + cut_x, True)
            outliers.set_selected(p < q1_x - cut_x, True)
        logger.info("Identified %i unit cell outliers" % outliers.count(True))

        plot_uc_histograms(uc_params, outliers)

    def cosym(self):
        logger.debug("Running cosym analysis")
        experiments_filename = self._data_manager.export_experiments("tmp.expt")
        reflections_filename = self._data_manager.export_reflections("tmp.refl")
        cosym = DialsCosym()
        auto_logfiler(cosym)

        cosym.add_experiments_json(experiments_filename)
        cosym.add_reflections_file(reflections_filename)
        if self._params.symmetry.space_group is not None:
            cosym.set_space_group(self._params.symmetry.space_group.group())
        if self._params.symmetry.laue_group is not None:
            cosym.set_space_group(self._params.symmetry.laue_group.group())
        cosym.set_best_monoclinic_beta(self._params.symmetry.cosym.best_monoclinic_beta)
        cosym.set_lattice_symmetry_max_delta(
            self._params.symmetry.cosym.lattice_symmetry_max_delta
        )
        cosym.run()
        self._cosym_analysis = cosym.get_cosym_analysis()
        self._experiments_filename = cosym.get_reindexed_experiments()
        self._reflections_filename = cosym.get_reindexed_reflections()
        self._data_manager.experiments = load.experiment_list(
            self._experiments_filename, check_format=False
        )
        self._data_manager.reflections = flex.reflection_table.from_file(
            self._reflections_filename
        )

        if not any(
            [self._params.symmetry.space_group, self._params.symmetry.laue_group]
        ):
            best_solution = cosym.get_best_solution()
            best_space_group = sgtbx.space_group(
                str(best_solution["patterson_group"])
            ).build_derived_acentric_group()
            self._params.symmetry.laue_group = best_space_group.info()
            logger.info(
                "Laue group determined by dials.cosym: %s" % best_space_group.info()
            )

    def reindex(self):
        logger.debug("Running reindexing")
        logger.info("Re-indexing to reference")
        reindex = Reindex()
        auto_logfiler(reindex)
        reindex.set_experiments_filename(self._experiments_filename)
        reindex.set_indexed_filename(self._reflections_filename)
        reindex.set_reference_file(self._params.reference)
        reindex.set_space_group(self._params.symmetry.space_group)

        reindex.run()

        self._experiments_filename = reindex.get_reindexed_experiments_filename()
        self._reflections_filename = reindex.get_reindexed_reflections_filename()
        self._data_manager.experiments = load.experiment_list(
            self._experiments_filename, check_format=False
        )
        self._data_manager.reflections = flex.reflection_table.from_file(
            self._reflections_filename
        )

    def decide_space_group(self):

        if self._params.symmetry.space_group is not None:
            # reindex to correct bravais setting
            cb_op = sgtbx.change_of_basis_op()
            space_group = self._params.symmetry.space_group.group()
            self._data_manager.reindex(cb_op=cb_op, space_group=space_group)
            crystal_symmetry = self._data_manager.experiments[
                0
            ].crystal.get_crystal_symmetry()
            cb_op_to_ref = crystal_symmetry.change_of_basis_op_to_reference_setting()
            self._data_manager.reindex(cb_op=cb_op_to_ref)
            self._experiments_filename = "models.expt"
            self._reflections_filename = "observations.refl"
            self._data_manager.export_experiments(self._experiments_filename)
            self._data_manager.export_reflections(self._reflections_filename)
            return

        logger.debug("Deciding space group with dials.symmetry")
        symmetry = DialsSymmetry()
        auto_logfiler(symmetry)

        self._experiments_filename = "%i_reindexed.expt" % symmetry.get_xpid()
        self._reflections_filename = "%i_reindexed.refl" % symmetry.get_xpid()

        experiments_filename = "tmp.expt"
        reflections_filename = "tmp.refl"
        self._data_manager.export_experiments(experiments_filename)
        self._data_manager.export_reflections(reflections_filename)

        symmetry.set_experiments_filename(experiments_filename)
        symmetry.set_reflections_filename(reflections_filename)
        symmetry.set_output_experiments_filename(self._experiments_filename)
        symmetry.set_output_reflections_filename(self._reflections_filename)
        symmetry.set_tolerance(
            relative_length_tolerance=None, absolute_angle_tolerance=None
        )
        symmetry.set_mode_absences_only()
        symmetry.decide_pointgroup()

        self._data_manager.experiments = load.experiment_list(
            self._experiments_filename, check_format=False
        )
        self._data_manager.reflections = flex.reflection_table.from_file(
            self._reflections_filename
        )
        space_group = self._data_manager.experiments[0].crystal.get_space_group()

        logger.info("Space group determined by dials.symmetry: %s" % space_group.info())

    def multi_crystal_analysis(self):
        from xia2.Modules.MultiCrystalAnalysis import MultiCrystalReport

        params = mca_phil.extract()
        params.prefix = "xia2.multiplex"
        params.title = "xia2.multiplex report"
        data_manager = copy.deepcopy(self._data_manager)
        refl = data_manager.reflections
        data_manager.reflections = refl.select(refl["d"] >= self._scaled.d_min)
        mca = MultiCrystalReport(params=params, data_manager=data_manager)
        return mca

    def report(self):
        # Scale so that all the data are in the range 0->1
        radar_data = self._comparison_graphs["radar"]["data"]
        for i in range(len(radar_data[0]["r"])):
            max_r = max(data["r"][i] for data in radar_data)
            for data in radar_data:
                data["r"][i] /= max_r

        self._mca.report(
            self._individual_report_dicts,
            self._comparison_graphs,
            self._cosym_analysis,
            image_range_table=self._individual_report_dicts["All data"][
                "image_range_table"
            ],
            scale_and_filter_results=self.scale_and_filter_results,
            scale_and_filter_mode=self._params.filtering.deltacchalf.mode,
        )

    def cluster_analysis(self):
        mca = self._mca.cluster_analysis()
        self._cos_angle_clusters = mca.cos_angle_clusters
        self._cc_clusters = mca.cc_clusters


class Scale:
    def __init__(self, data_manager, params, filtering=False):
        self._data_manager = data_manager
        self._params = params
        self._filtering = filtering

        self._experiments_filename = "models.expt"
        self._reflections_filename = "observations.refl"
        self._data_manager.export_experiments(self._experiments_filename)
        self._data_manager.export_reflections(self._reflections_filename)

        if "two_theta" in self._params.unit_cell.refine:
            self.two_theta_refine()

        self.d_min = self._params.resolution.d_min
        d_max = self._params.resolution.d_max
        self.scale(d_min=self.d_min, d_max=d_max)

        if self.d_min is None:
            self.d_min, reason = self.estimate_resolution_limit()
            logger.info(f"Resolution limit: {self.d_min:.2f} ({reason})")
            if self._params.rescale_after_resolution_cutoff:
                self.scale(d_min=self.d_min, d_max=d_max)

    def refine(self):
        # refine in correct bravais setting
        self._experiments_filename, self._reflections_filename = self._dials_refine(
            self._experiments_filename, self._reflections_filename
        )
        self._data_manager.experiments = load.experiment_list(
            self._experiments_filename, check_format=False
        )
        self._data_manager.reflections = flex.reflection_table.from_file(
            self._reflections_filename
        )

    def two_theta_refine(self):
        # two-theta refinement to get best estimate of unit cell
        self._experiments_filename = self._dials_two_theta_refine(
            self._experiments_filename,
            self._reflections_filename,
            combine_crystal_models=self._params.two_theta_refine.combine_crystal_models,
        )
        self._data_manager.experiments = load.experiment_list(
            self._experiments_filename, check_format=False
        )

    @property
    def data_manager(self):
        return self._data_manager

    @staticmethod
    def _dials_refine(experiments_filename, reflections_filename):
        refiner = Refine()
        auto_logfiler(refiner)
        refiner.set_experiments_filename(experiments_filename)
        refiner.set_indexed_filename(reflections_filename)
        refiner.run()
        return (
            refiner.get_refined_experiments_filename(),
            refiner.get_refined_filename(),
        )

    @staticmethod
    def _dials_two_theta_refine(
        experiments_filename, reflections_filename, combine_crystal_models=True
    ):
        tt_refiner = TwoThetaRefine()
        auto_logfiler(tt_refiner)
        tt_refiner.set_experiments([experiments_filename])
        tt_refiner.set_reflection_files([reflections_filename])
        tt_refiner.set_combine_crystal_models(combine_crystal_models)
        tt_refiner.run()
        return tt_refiner.get_output_experiments()

    def scale(self, d_min=None, d_max=None):
        logger.debug("Scaling with dials.scale")
        scaler = DialsScale()
        auto_logfiler(scaler)
        scaler.add_experiments_json(self._experiments_filename)
        scaler.add_reflections_file(self._reflections_filename)

        scaler.set_anomalous(self._params.scaling.anomalous)

        # Let dials.scale use its auto model determination as the default
        # (physical model if > 1 degree sweep else KB model, with an absorption
        # surface if > 60 degrees).
        if self._params.scaling.model not in (None, "auto", Auto):
            scaler.set_model(self._params.scaling.model)

        if self._params.scaling.absorption_level:
            scaler.set_absorption_level(self._params.scaling.absorption_level)
            scaler.set_absorption_correction(True)
        elif self._params.scaling.secondary.lmax:
            scaler.set_absorption_correction(True)
            scaler.set_lmax(self._params.scaling.secondary.lmax)

        if self._params.scaling.secondary.share.absorption:
            scaler.set_shared_absorption(True)

        exp = self._data_manager.experiments[0]
        scale_interval, decay_interval = scaling_model_auto_rules(exp)
        if self._params.scaling.rotation.spacing is not None:
            scaler.set_spacing(self._params.scaling.rotation.spacing)
        else:
            scaler.set_spacing(scale_interval)
        if self._params.scaling.brotation.spacing is not None:
            scaler.set_bfactor(brotation=self._params.scaling.brotation.spacing)
        else:
            scaler.set_bfactor(brotation=decay_interval)

        scaler.set_resolution(d_min=d_min, d_max=d_max)
        if self._params.scaling.reflection_selection.Isigma_range is not None:
            scaler.set_isigma_selection(
                self._params.scaling.reflection_selection.Isigma_range
            )
        if self._params.scaling.min_partiality is not None:
            scaler.set_min_partiality(self._params.scaling.min_partiality)
        if self._params.scaling.partiality_cutoff is not None:
            scaler.set_partiality_cutoff(self._params.scaling.partiality_cutoff)
        if self._params.scaling.reflection_selection.method is not None:
            scaler.set_reflection_selection_method(
                self._params.scaling.reflection_selection.method
            )

        scaler.set_full_matrix(False)

        scaler.set_outlier_rejection(self._params.scaling.outlier_rejection)

        if self._filtering:
            scaler.set_filtering_method(self._params.filtering.method)
            scaler.set_deltacchalf_max_cycles(
                self._params.filtering.deltacchalf.max_cycles
            )
            scaler.set_deltacchalf_max_percent_removed(
                self._params.filtering.deltacchalf.max_percent_removed
            )
            scaler.set_deltacchalf_min_completeness(
                self._params.filtering.deltacchalf.min_completeness
            )
            scaler.set_deltacchalf_mode(self._params.filtering.deltacchalf.mode)
            scaler.set_deltacchalf_group_size(
                self._params.filtering.deltacchalf.group_size
            )
            scaler.set_deltacchalf_stdcutoff(
                self._params.filtering.deltacchalf.stdcutoff
            )

        scaler.scale()
        self._experiments_filename = scaler.get_scaled_experiments()
        self._reflections_filename = scaler.get_scaled_reflections()
        self._data_manager.experiments = load.experiment_list(
            self._experiments_filename, check_format=False
        )
        self._data_manager.reflections = flex.reflection_table.from_file(
            self._reflections_filename
        )
        self._params.resolution.labels = "IPR,SIGIPR"
        if self._filtering:
            self.scale_and_filter_results = scaler.get_scale_and_filter_results()
        return scaler

    def estimate_resolution_limit(self):
        # see also xia2/Modules/Scaler/CommonScaler.py: CommonScaler._estimate_resolution_limit()
        params = self._params.resolution
        m = EstimateResolution()
        auto_logfiler(m)
        # use the scaled .refl and .expt file
        if self._experiments_filename and self._reflections_filename:
            m.set_reflections(self._reflections_filename)
            m.set_experiments(self._experiments_filename)
        else:
            m.set_hklin(self._scaled_unmerged_mtz)
        m.set_limit_rmerge(params.rmerge)
        m.set_limit_completeness(params.completeness)
        m.set_limit_cc_half(params.cc_half)
        m.set_cc_half_fit(params.cc_half_fit)
        m.set_cc_half_significance_level(params.cc_half_significance_level)
        m.set_limit_isigma(params.isigma)
        m.set_limit_misigma(params.misigma)
        m.set_labels(params.labels)
        # if batch_range is not None:
        # start, end = batch_range
        # m.set_batch_range(start, end)
        m.run()

        resolution_limits = []
        reasoning = []

        if params.completeness is not None:
            r_comp = m.get_resolution_completeness()
            resolution_limits.append(r_comp)
            reasoning.append("completeness > %s" % params.completeness)

        if params.cc_half is not None:
            r_cc_half = m.get_resolution_cc_half()
            resolution_limits.append(r_cc_half)
            reasoning.append("cc_half > %s" % params.cc_half)

        if params.rmerge is not None:
            r_rm = m.get_resolution_rmerge()
            resolution_limits.append(r_rm)
            reasoning.append("rmerge > %s" % params.rmerge)

        if params.isigma is not None:
            r_uis = m.get_resolution_isigma()
            resolution_limits.append(r_uis)
            reasoning.append("unmerged <I/sigI> > %s" % params.isigma)

        if params.misigma is not None:
            r_mis = m.get_resolution_misigma()
            resolution_limits.append(r_mis)
            reasoning.append("merged <I/sigI> > %s" % params.misigma)

        if any(resolution_limits):
            resolution = max(r for r in resolution_limits if r is not None)
            reasoning = [
                reason
                for limit, reason in zip(resolution_limits, reasoning)
                if limit is not None and limit >= resolution
            ]
            reasoning = ", ".join(reasoning)
        else:
            resolution = 0.0
            reasoning = None

        return resolution, reasoning

    def report(self):
        params = Report.phil_scope.extract()
        params.dose.batch = []
        params.d_min = self.d_min
        params.anomalous = self._params.scaling.anomalous
        report = Report.Report.from_data_manager(self._data_manager, params=params)
        return report
