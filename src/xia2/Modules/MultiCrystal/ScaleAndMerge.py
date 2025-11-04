from __future__ import annotations

import copy
import logging
import math
import os
import pathlib
from collections import OrderedDict
from typing import Any

import iotbx.phil
import libtbx.phil
from cctbx import sgtbx, uctbx
from dials.algorithms.scaling import scale_and_filter
from dials.array_family import flex
from dials.command_line.unit_cell_histogram import plot_uc_histograms
from dials.util import tabulate
from dials.util.export_mtz import match_wavelengths
from dials.util.system import CPU_COUNT
from dxtbx.model import ExperimentList
from dxtbx.serialize import load
from dxtbx.util import format_float_with_standard_uncertainty
from libtbx import Auto
from scitbx.math import five_number_summary

from xia2.Driver.timing import record_step
from xia2.Handlers.Phil import PhilIndex
from xia2.Handlers.Streams import banner
from xia2.lib.bits import auto_logfiler
from xia2.Modules import Report
from xia2.Modules.MultiCrystal.cluster_analysis import SubCluster, get_subclusters
from xia2.Modules.MultiCrystal.data_manager import DataManager
from xia2.Modules.MultiCrystalAnalysis import MultiCrystalAnalysis, MultiCrystalReport
from xia2.Modules.Scaler.DialsScaler import (
    convert_merged_mtz_to_sca,
    convert_unmerged_mtz_to_sca,
    scaling_model_auto_rules,
)
from xia2.Wrappers.Dials.Cosym import DialsCosym
from xia2.Wrappers.Dials.EstimateResolution import EstimateResolution
from xia2.Wrappers.Dials.Functional.ExportShelx import ExportShelx
from xia2.Wrappers.Dials.Functional.Merge import Merge
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
    relative_length_tolerance = 0.05
      .type = float(value_min=0)
      .help = "Datasets are only accepted if unit cell lengths fall within this relative tolerance of the median cell lengths."
    absolute_angle_tolerance = 2
      .type = float(value_min=0)
      .help = "Datasets are only accepted if unit cell angles fall within this absolute tolerance of the median cell angles."
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
  unit_cell = None
    .type = unit_cell
    .short_caption = "Unit cell"
  n_bins = 20
    .type = int(value_min=1)
    .short_caption = "Number of bins"
  d_min = None
    .type = float(value_min=0)
    .short_caption = "High resolution cutoff"
  batch
    .multiple = True
  {
    id = None
      .type = str
    range = None
      .type = ints(size=2, value_min=0)
  }
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

include scope xia2.cli.cluster_analysis.cluster_phil_scope

identifiers = None
  .type = strings
  .short_caption = "Identifiers"
  .help = "Unique DIALS identifiers of experiments to be merged"

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

significant_clusters {
  min_points_buffer = 0.5
    .type = float(value_min=0, value_max=1)
    .help = "Buffer for minimum number of points required for a cluster in OPTICS algorithm: min_points=(number_of_datasets/number_of_dimensions)*buffer"
  xi = 0.05
    .type = float(value_min=0, value_max=1)
    .help = "xi parameter to determine min steepness to define cluster boundary"
  max_distance = 0.5
    .type = float
    .help = "maximum distance away from cluster centre for a data point to be considered (max_eps)"
  min_points = 5
    .type = int
    .help = "Set minimum number of points required for a cluster in OPTICS. Only used when optimise_input=False."
  optimise_input = True
    .type = bool
    .help = "Turn to false to use custom clustering parameters."
}

small_molecule {
  composition = None
    .type = str
    .help = "The chemical composition of the asymmetric unit. Set this to trigger export to shelx format."
}

""",
    process_includes=True,
)

# the phil scope which used to live in xia2.multi_crystal_analysis
mca_phil = iotbx.phil.parse(
    """
include scope xia2.cli.report.phil_scope

seed = 230
  .type = int(value_min=0)

unit_cell_clustering {
  threshold = 5000
    .type = float(value_min=0)
    .help = 'Threshold value for the clustering'
  log = False
    .type = bool
    .help = 'Display the dendrogram with a log scale'
}

include scope dials.algorithms.correlation.analysis.working_phil

output {
  log = xia2.multi_crystal_analysis.log
    .type = str
  json = xia2.multiplex_clusters.json
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
    def __init__(
        self,
        experiments: ExperimentList,
        reflections: flex.reflection_table,
        params: iotbx.phil.scope_extract,
    ):
        self._data_manager = DataManager(experiments, reflections)

        self._params = params
        if all([params.symmetry.laue_group, params.symmetry.space_group]):
            raise ValueError("Can not specify both laue_group and space_group")

        if self._params.nproc is Auto:
            self._params.nproc = CPU_COUNT
            PhilIndex.params.xia2.settings.multiprocessing.nproc = self._params.nproc

        if self._params.identifiers is not None:
            self._data_manager.select(self._params.identifiers)
        if self._params.dose is not None:
            self._data_manager.filter_dose(*self._params.dose)

        logger.notice(banner("Filtering reflections"))  # type: ignore

        if params.remove_profile_fitting_failures:
            reflections = self._data_manager.reflections
            profile_fitted_mask = reflections.get_flags(
                reflections.flags.integrated_prf
            )
            ids_used = set(reflections["id"].select(profile_fitted_mask))
            id_map = reflections.experiment_identifiers()
            keep_expts = []
            for id_ in ids_used:
                keep_expts.append(id_map[id_])
            if keep_expts:
                logger.info(
                    f"Selecting {len(keep_expts)} experiments with profile-fitted reflections"
                )
                # Only do the selection if we are not keeping all data.
                if len(keep_expts) != len(self._data_manager.experiments):
                    self._data_manager.select(keep_expts)

        reflections = self._data_manager.reflections
        used_in_refinement_mask = reflections.get_flags(
            reflections.flags.used_in_refinement
        )
        ids_used = set(reflections["id"].select(used_in_refinement_mask))
        id_map = reflections.experiment_identifiers()
        keep_expts = []
        for id_ in ids_used:
            keep_expts.append(id_map[id_])
        if keep_expts:
            logger.info(
                f"Selecting {len(keep_expts)} experiments with refined reflections"
            )
            # Only do the selection if we are not keeping all data.
            if len(keep_expts) != len(self._data_manager.experiments):
                self._data_manager.select(keep_expts)

        self._individual_report_dicts: dict[str, dict[str, Any]] = OrderedDict()
        self._comparison_graphs: dict[str, dict[str, Any]] = OrderedDict()
        self.scale_and_filter_results: scale_and_filter.AnalysisResults | None = None
        self._cosym_analysis: dict[str, Any] = OrderedDict({"cosym_graphs": {}})

    def run(self) -> None:
        logger.notice(banner("Unit cell clustering"))  # type: ignore
        self.unit_cell_clustering(plot_name="cluster_unit_cell_p1.png")

        if self._params.symmetry.resolve_indexing_ambiguity:
            logger.notice(banner("Applying consistent symmetry"))  # type: ignore
            self.cosym()

        logger.notice(banner("Scaling"))  # type: ignore

        self._scaled = Scale(self._data_manager, self._params)
        self._experiments_filename = self._scaled._experiments_filename
        self._reflections_filename = self._scaled._reflections_filename

        if self._params.reference is not None:
            logger.notice(banner("Reindexing to reference"))  # type: ignore
            self.reindex()
        else:
            logger.notice(banner("Determining space group"))  # type: ignore
            self.decide_space_group()

        logger.notice(banner("Merging (All data)"))  # type: ignore

        d_spacings: flex.double = self._scaled.data_manager._reflections["d"]
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

        if self._params.small_molecule.composition:
            self.export_shelx(
                self._params,
                self._data_manager._experiments,
                self._data_manager._reflections,
                "scaled",
            )

        self.export_merged_mtz(
            self._params,
            self._data_manager._experiments,
            self._data_manager._reflections,
            "scaled.mtz",
            self._scaled.d_min,
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
                if name:
                    convert_unmerged_mtz_to_sca(name)

                # unmerged mmcif for multiple wavelength
                self._data_manager.export_unmerged_wave_mmcif(
                    wl, "scaled_unmerged", d_min=self._scaled.d_min
                )

            # now export merged of each
            for wl in self.wavelengths:
                name = self.export_merged_wave_mtz(
                    self._params,
                    self._data_manager,
                    wl,
                    "scaled",
                    self._scaled.d_min,
                )
                if name:
                    convert_merged_mtz_to_sca(name)

        else:
            self._data_manager.export_unmerged_mtz(
                "scaled_unmerged.mtz",
                d_min=self._scaled.d_min,
                wavelength_tolerance=self._params.wavelength_tolerance,
            )
            convert_merged_mtz_to_sca("scaled.mtz")
            convert_unmerged_mtz_to_sca("scaled_unmerged.mtz")

            self._data_manager.export_unmerged_mmcif(
                "scaled_unmerged.mmcif", d_min=self._scaled.d_min
            )

        with record_step("xia2.report(all-data)"):
            self._record_individual_report(self._scaled.report(), "All data")

        logger.notice(banner("Identifying intensity-based clusters"))  # type: ignore

        self._mca: MultiCrystalReport = (
            self.multi_crystal_analysis()
        )  # Sets up the analysis and reporting class
        self.cluster_analysis()  # Actually does the cluster analysis

        # now do cluster identification as in xia2.cluster_analysis.
        # Same code structure as MultiCrystalAnalysis/cluster_analysis.py but changes the call
        # from output_cluster to self._scale_and_report_cluster

        if self._params.clustering.output_clusters:
            logger.notice(  # type: ignore
                banner(
                    f"Scaling and merging {self._params.clustering.method[0]} clusters"
                )
            )
            subclusters = get_subclusters(
                self._params.clustering,
                self._data_manager.ids_to_identifiers_map,
                self._cos_angle_clusters,
                self._cc_clusters,
                self._coordinate_clusters,
            )

            # revert to sequential cluster scaling while reducing memory requirements elsewhere :(
            # move back to below code for pool later once other memory requirements reduced

            for cluster in subclusters:
                (
                    individual_report,
                    report,
                    dict_report,
                    cluster_name,
                ) = self._scale_and_report_cluster(
                    self._params,
                    self._data_manager.select_and_create(cluster.identifiers),
                    cluster,
                )
                self._individual_report_dicts[cluster_name] = individual_report
                self._update_comparison_graphs(report, dict_report, cluster_name)
                self._log_report_info(dict_report)

            """
            # To ensure that pools within pools aren't created

            parallel_nproc = copy.deepcopy(self._params.nproc)
            self._params.nproc = 1

            logger.debug(
                f"Using nproc = {parallel_nproc} for parallel scaling, PHIL nproc set to {self._params.nproc}"
            )

            with (
                record_step("dials.scale(parallel)"),
                concurrent.futures.ProcessPoolExecutor(
                    max_workers=min(parallel_nproc, len(subclusters))
                ) as pool,
            ):
                cluster_futures = {
                    pool.submit(
                        self._scale_and_report_cluster,
                        self._params,
                        self._data_manager.select_and_create(item.identifiers),
                        item,
                    ): index
                    for index, item in enumerate(subclusters)
                }
                for future in concurrent.futures.as_completed(cluster_futures):
                    idx = cluster_futures[future]
                    try:
                        (
                            info_stream,
                            debug_stream,
                            individual_report,
                            report,
                            dict_report,
                            cluster_name,
                        ) = future.result()
                    except Exception as e:
                        raise ValueError(
                            f"Cluster {idx} failed to scale and merge due to {e}"
                        )
                    else:
                        logger.info(info_stream)
                        logger.debug(debug_stream)
                        self._individual_report_dicts[cluster_name] = individual_report
                        self._update_comparison_graphs(
                            report, dict_report, cluster_name
                        )
                        self._log_report_info(dict_report)

            # Reset nproc
            self._params.nproc = parallel_nproc

            logger.debug(f"Reset PHIL nproc to {self._params.nproc}")

            """

        if self._params.filtering.method:
            logger.notice(banner("Rescaling with extra filtering"))  # type: ignore
            # Final round of scaling, this time filtering out any bad datasets
            data_manager = copy.deepcopy(self._data_manager)
            params = copy.deepcopy(self._params)
            params.unit_cell.refine = []
            params.resolution.d_min = self._params.resolution.d_min
            scaled = Scale(data_manager, params, filtering=True)
            self.scale_and_filter_results = scaled.scale_and_filter_results
            logger.info("Scale and filtering:\n%s", self.scale_and_filter_results)

            logger.notice(banner("Merging (Filtered)"))  # type: ignore

            if self._params.small_molecule.composition:
                self.export_shelx(
                    params,
                    data_manager._experiments,
                    data_manager._reflections,
                    "filtered",
                )

            self.export_merged_mtz(
                params,
                data_manager._experiments,
                data_manager._reflections,
                "filtered.mtz",
                scaled.d_min,
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

                    # unmerged mmcif for multiple wavelength
                    data_manager.export_unmerged_wave_mmcif(
                        wl, "filtered_unmerged", d_min=scaled.d_min
                    )

                # now export merged of each
                for wl in self.wavelengths:
                    name = self.export_merged_wave_mtz(
                        params,
                        data_manager,
                        wl,
                        "filtered",
                        scaled.d_min,
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

                data_manager.export_unmerged_mmcif(
                    "filtered_unmerged.mmcif", d_min=scaled.d_min
                )

            data_manager._set_batches()
            with record_step("xia2.report(filtered)"):
                self._record_individual_report(scaled.report(), "Filtered")
            data_manager.export_experiments("filtered.expt")
            data_manager.export_reflections("filtered.refl", d_min=scaled.d_min)

        self.report()

    @staticmethod
    def _scale_and_report_cluster(
        params: libtbx.phil.scope_extract,
        data_manager: DataManager,
        cluster_data: SubCluster,
    ) -> tuple[
        dict[str, Any], Report.Report, dict[str, Any], str
    ]:  # tuple[str, str, dict[str, Any], Report.Report, dict[str, Any], str]:
        # with redirect_xia2_logger() as iostream:
        cwd = pathlib.Path.cwd()
        if not os.path.exists(cluster_data.directory):
            os.mkdir(cluster_data.directory)
        os.chdir(cluster_data.directory)
        logger.notice(banner(f"{cluster_data.directory}"))  # type: ignore
        logger.info(cluster_data.cluster)
        output_name = f"{cluster_data.directory}_scaled"
        free_flags_in_full_set = True
        scaled = Scale(data_manager, params)
        data_manager.export_experiments(f"{output_name}.expt")
        data_manager.export_reflections(f"{output_name}.refl", d_min=scaled.d_min)

        # if we didn't have an external reference for the free_flags set, we need to make
        # and record one here.

        if params.small_molecule.composition:
            MultiCrystalScale.export_shelx(
                params,
                data_manager._experiments,
                data_manager._reflections,
                output_name,
            )

        MultiCrystalScale.export_merged_mtz(
            params,
            data_manager._experiments,
            data_manager._reflections,
            f"{output_name}.mtz",
            scaled.d_min,
        )

        if (not free_flags_in_full_set) and (params.r_free_flags.extend is True):
            params.r_free_flags.reference = os.path.join(
                os.getcwd(), f"{output_name}.mtz"
            )
            free_flags_in_full_set = True

        wavelengths = match_wavelengths(
            data_manager.experiments, params.wavelength_tolerance
        )  # in experiments order

        if len(wavelengths) > 1:
            data_manager.split_by_wavelength(params.wavelength_tolerance)
            for wl in wavelengths:
                name = data_manager.export_unmerged_wave_mtz(
                    wl,
                    f"{output_name}_unmerged",
                    d_min=scaled.d_min,
                    wavelength_tolerance=params.wavelength_tolerance,
                )
                if name:
                    convert_unmerged_mtz_to_sca(name)

                # unmerged mmcif for multiple wavelength
                data_manager.export_unmerged_wave_mmcif(
                    wl, f"{output_name}_unmerged", d_min=scaled.d_min
                )

            for wl in wavelengths:
                name = MultiCrystalScale.export_merged_wave_mtz(
                    params,
                    data_manager,
                    wl,
                    f"{output_name}",
                    scaled.d_min,
                )
                if name:
                    convert_merged_mtz_to_sca(name)
        else:
            data_manager.export_unmerged_mtz(
                f"{output_name}_unmerged.mtz",
                d_min=scaled.d_min,
                wavelength_tolerance=params.wavelength_tolerance,
            )
            convert_merged_mtz_to_sca(f"{output_name}.mtz")
            convert_unmerged_mtz_to_sca(f"{output_name}_unmerged.mtz")

            data_manager.export_unmerged_mmcif(
                f"{output_name}_unmerged.mmcif", d_min=scaled.d_min
            )
        rep = scaled.report()

        d = MultiCrystalScale._report_as_dict(rep)

        # need this otherwise rep will not have merging_stats
        rep.resolution_plots_and_stats()

        individual_report = MultiCrystalScale._individual_report_dict(
            d, cluster_data.directory.replace("_", " ")
        )

        os.chdir(cwd)
        # info = iostream[0].getvalue()
        # debug = iostream[1].getvalue()
        return (
            # info,
            # debug,
            individual_report,
            rep,
            d,
            cluster_data.directory.replace("_", " "),
        )

    def _update_comparison_graphs(
        self, report: Report.Report, dict_report: dict[str, Any], cluster_name: str
    ) -> None:
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
                graph, {"layout": dict_report[graph]["layout"], "data": []}
            )
            data = copy.deepcopy(dict_report[graph]["data"][0])
            data["name"] = cluster_name
            data.pop("line", None)  # remove default color override
            self._comparison_graphs[graph]["data"].append(data)

    def _log_report_info(self, d: dict[str, Any]) -> None:
        def remove_html_tags(table):
            return [
                [
                    (
                        s.replace("<strong>", "")
                        .replace("</strong>", "")
                        .replace("<sub>", "")
                        .replace("</sub>", "")
                        if isinstance(s, str)
                        else s
                    )
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

    def _record_individual_report(
        self, report: Report.Report, cluster_name: str
    ) -> None:
        d = self._report_as_dict(report)

        self._individual_report_dicts[cluster_name] = self._individual_report_dict(
            d, cluster_name
        )

        self._update_comparison_graphs(report, d, cluster_name)

        self._log_report_info(d)

    @staticmethod
    def _report_as_dict(report: Report.Report) -> dict[str, Any]:
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
    def _individual_report_dict(
        report_d: dict[str, Any], cluster_name: str
    ) -> dict[str, Any]:
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

    def unit_cell_clustering(self, plot_name: str | None = None) -> None:
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
        if clustering:
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
                self._data_manager._set_batches()
            else:
                logger.info("Using all data sets for subsequent analysis")
        else:
            logger.info("Clustering unsuccessful")

    def unit_cell_histogram(self, plot_name: str | None = None) -> None:
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
                f"Five number summary: min {min_x:.2f}, q1 {q1_x:.2f}, med {med_x:.2f}, q3 {q3_x:.2f}, max {max_x:.2f}"
            )
            iqr_x = q3_x - q1_x
            if iqr_x < 1e-6:
                continue
            cut_x = iqr_ratio * iqr_x
            outliers.set_selected(p > q3_x + cut_x, True)
            outliers.set_selected(p < q1_x - cut_x, True)
        logger.info("Identified %i unit cell outliers" % outliers.count(True))

        plot_uc_histograms(uc_params, outliers)

    def cosym(self) -> None:
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
        cosym.set_relative_length_tolerance(
            self._params.symmetry.cosym.relative_length_tolerance
        )
        cosym.set_absolute_angle_tolerance(
            self._params.symmetry.cosym.absolute_angle_tolerance
        )
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
        self._data_manager._set_batches()

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
        elif self._params.symmetry.space_group:
            logger.info(f"Using input space group: {self._params.symmetry.space_group}")
        elif self._params.symmetry.laue_group:
            logger.info(f"Using input Laue group: {self._params.symmetry.laue_group}")

    def reindex(self) -> None:
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

    def decide_space_group(self) -> None:
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

    def multi_crystal_analysis(self) -> MultiCrystalReport:
        params = mca_phil.extract()
        params.prefix = "xia2.multiplex"
        params.title = "xia2.multiplex report"
        params.significant_clusters.xi = self._params.significant_clusters.xi
        params.significant_clusters.min_points_buffer = (
            self._params.significant_clusters.min_points_buffer
        )
        params.significant_clusters.min_points = (
            self._params.significant_clusters.min_points
        )
        params.significant_clusters.max_distance = (
            self._params.significant_clusters.max_distance
        )
        params.significant_clusters.optimise_input = (
            self._params.significant_clusters.optimise_input
        )
        data_manager = copy.deepcopy(self._data_manager)
        refl = data_manager.reflections
        data_manager.reflections = refl.select(refl["d"] >= self._scaled.d_min)
        # Sets up the analysis and  report class, but doesn't do the clustering analysis.
        mca = MultiCrystalReport(params=params, data_manager=data_manager)
        return mca

    def report(self) -> None:
        # Scale so that all the data are in the range 0->1
        radar_data = self._comparison_graphs["radar"]["data"]
        for i in range(len(radar_data[0]["r"])):
            max_r = max(data["r"][i] for data in radar_data)
            for data in radar_data:
                data["r"][i] /= max_r

        # if there is only one dataset (i.e. no clusters), don't
        # plot the comparison plots in the report.
        if len(self._comparison_graphs["cc_one_half"]["data"]) == 1:
            self._comparison_graphs = OrderedDict()

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

    def cluster_analysis(self) -> None:
        self._mca.cluster_analysis()
        self._cos_angle_clusters = self._mca.cos_clusters
        self._cc_clusters = self._mca.cc_clusters
        self._coordinate_clusters = self._mca.significant_coordinate_clusters

    @staticmethod
    def export_merged_mtz(
        params: libtbx.phil.scope_extract,
        expts: ExperimentList,
        refls: flex.reflection_table,
        file_name: str,
        d_min: float,
    ) -> None:
        merge = Merge()
        merge.output_filename = file_name
        merge.set_d_min(d_min)
        merge.set_wavelength_tolerance(params.wavelength_tolerance)
        merge.set_r_free_params(params.r_free_flags)
        merge.run(expts, refls)

    @staticmethod
    def export_merged_wave_mtz(
        params: libtbx.phil.scope_extract,
        data_manager: DataManager,
        wavelength: float,
        output_name: str,
        d_min: float,
    ) -> str | None:
        data = data_manager.data_split_by_wl[wavelength]
        if data["expt"]:
            fmt = "%%0%dd" % (math.log10(len(data_manager.wavelengths)) + 1)
            index = sorted(data_manager.wavelengths.keys()).index(wavelength)
            name = f"{output_name}_WAVE{fmt % (index + 1)}.mtz"

            MultiCrystalScale.export_merged_mtz(
                params, data["expt"], data["refl"], name, d_min
            )

            return name
        return None

    @staticmethod
    def export_shelx(
        params: libtbx.phil.scope_extract,
        expts: ExperimentList,
        refls: flex.reflection_table,
        output_name: str,
    ) -> None:
        export = ExportShelx()
        export.set_output_names(output_name)
        export.set_composition(params.small_molecule.composition)
        export.run(expts, refls)


class Scale:
    def __init__(
        self,
        data_manager: DataManager,
        params: iotbx.phil.scope_extract,
        filtering: bool = False,
    ):
        self._data_manager = data_manager
        self._params = params
        self._filtering = filtering

        self._experiments_filename: str = "models.expt"
        self._reflections_filename: str = "observations.refl"
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

    def refine(self) -> None:
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

    def two_theta_refine(self) -> None:
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
    def data_manager(self) -> DataManager:
        return self._data_manager

    @staticmethod
    def _dials_refine(
        experiments_filename: str, reflections_filename: str
    ) -> tuple[str, str]:
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
        experiments_filename: str,
        reflections_filename: str,
        combine_crystal_models: bool = True,
    ) -> str:
        tt_refiner = TwoThetaRefine()
        auto_logfiler(tt_refiner)
        tt_refiner.set_experiments([experiments_filename])
        tt_refiner.set_reflection_files([reflections_filename])
        tt_refiner.set_combine_crystal_models(combine_crystal_models)
        tt_refiner.run()
        uc = tt_refiner.get_unit_cell()
        uc_sd = tt_refiner.get_unit_cell_esd()
        cell_str = [
            format_float_with_standard_uncertainty(v, e, minimum=1.0e-5)
            for (v, e) in zip(uc, uc_sd)
        ]
        logger.info("Refined unit cell: " + ", ".join(cell_str))
        return tt_refiner.get_output_experiments()

    def scale(self, d_min: float | None = None, d_max: float | None = None) -> None:
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

    def estimate_resolution_limit(self) -> tuple[float, str]:
        # see also xia2/Modules/Scaler/CommonScaler.py: CommonScaler._estimate_resolution_limit()
        params = self._params.resolution
        m = EstimateResolution()
        auto_logfiler(m)
        # use the scaled .refl and .expt file
        assert self._experiments_filename and self._reflections_filename
        m.set_reflections(self._reflections_filename)
        m.set_experiments(self._experiments_filename)
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
            final_reasoning = ", ".join(reasoning)
        else:
            resolution = 0.0
            final_reasoning = ""

        return resolution, final_reasoning

    def report(self) -> Report.Report:
        params = Report.phil_scope.extract()
        params.dose.batch = []
        params.d_min = self.d_min
        params.anomalous = self._params.scaling.anomalous
        report = Report.Report.from_data_manager(self._data_manager, params=params)
        return report
