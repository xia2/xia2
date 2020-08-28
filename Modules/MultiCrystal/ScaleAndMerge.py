import copy
import logging
import math
import os
from collections import OrderedDict

from libtbx import Auto
import iotbx.phil
from cctbx import miller
from cctbx import sgtbx
from dxtbx.serialize import load
from dxtbx.model import ExperimentList


from dials.array_family import flex
from dials.command_line import export
from dials.command_line import merge
from dials.command_line.unit_cell_histogram import plot_uc_histograms
from dials.util import tabulate

from scitbx.math import five_number_summary

from xia2.lib.bits import auto_logfiler
from xia2.Handlers.Phil import PhilIndex
from xia2.Handlers.Environment import get_number_cpus
from xia2.Modules import Report
from xia2.Modules.Scaler.DialsScaler import scaling_model_auto_rules
from xia2.Wrappers.Dials.Cosym import DialsCosym
from xia2.Wrappers.Dials.EstimateResolution import EstimateResolution
from xia2.Wrappers.Dials.Refine import Refine
from xia2.Wrappers.Dials.Scale import DialsScale
from xia2.Wrappers.Dials.Symmetry import DialsSymmetry
from xia2.Wrappers.Dials.TwoThetaRefine import TwoThetaRefine


logger = logging.getLogger(__name__)


# The phil scope
phil_scope = iotbx.phil.parse(
    """
unit_cell_clustering {
  threshold = 5000
    .type = float(value_min=0)
    .help = 'Threshold value for the clustering'
  log = False
    .type = bool
    .help = 'Display the dendrogram with a log scale'
}

scaling
{
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
  }
  model = physical dose_decay array KB *auto
    .type = choice
  outlier_rejection = simple *standard
    .type = choice
  Isigma_range = 2.0,100000
    .type = floats(size=2)
  min_partiality = None
    .type = float(value_min=0, value_max=1)
  partiality_cutoff = None
    .type = float(value_min=0, value_max=1)
}

symmetry {
  resolve_indexing_ambiguity = True
    .type = bool
  cosym {
    include scope dials.algorithms.symmetry.cosym.phil_scope
  }
  le_page_max_delta = 5
    .type = float(value_min=0)
  laue_group = None
    .type = space_group
    .help = "Specify the Laue group. If None, then the Laue group will be determined "
            "by dials.cosym."
  space_group = None
    .type = space_group
    .help = "Specify the space group. If None, then the dials.symmetry will perform "
            "analysis of systematically absent reflections to determine the space group."
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
  include scope dials.util.resolution_analysis.phil_str
}

rescale_after_resolution_cutoff = False
  .help = "Re-scale the data after application of a resolution cutoff"
  .type = bool

filtering {
  method = None deltacchalf
    .type = choice
    .help = "Choice of whether to do any filtering cycles, default None."
  deltacchalf {
    max_cycles = 6
      .type = int(value_min=1)
    min_completeness = None
      .type = float(value_min=0, value_max=100)
      .help = "Desired minimum completeness, as a percentage (0 - 100)."
    stdcutoff = 4.0
      .type = float
      .help = "Datasets with a ΔCC½ below (mean - stdcutoff*std) are removed"
  }
}

multi_crystal_analysis {
  include scope xia2.Modules.MultiCrystal.master_phil_scope
}

unit_cell {
  refine = *two_theta
    .type = choice(multi=True)
}

two_theta_refine {
  combine_crystal_models = True
    .type = bool
}

min_completeness = None
  .type = float(value_min=0, value_max=1)
min_multiplicity = None
  .type = float(value_min=0)
max_clusters = None
  .type = int(value_min=1)
cluster_method = *cos_angle correlation unit_cell
  .type = choice

identifiers = None
  .type = strings

dose = None
  .type = ints(size=2, value_min=0)

nproc = Auto
  .type = int(value_min=1)
  .help = "The number of processors to use"
  .expert_level = 0
remove_profile_fitting_failures = True
  .type = bool

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


class DataManager:
    def __init__(self, experiments, reflections):
        self._input_experiments = experiments
        self._input_reflections = reflections

        self._experiments = copy.deepcopy(experiments)
        self._reflections = copy.deepcopy(reflections)
        self.ids_to_identifiers_map = dict(self._reflections.experiment_identifiers())
        self.identifiers_to_ids_map = {
            value: key for key, value in self.ids_to_identifiers_map.items()
        }

        self._set_batches()

    def _set_batches(self):
        max_batches = max(e.scan.get_image_range()[1] for e in self._experiments)
        max_batches += 10  # allow some head room

        n = int(math.ceil(math.log10(max_batches)))

        for i, expt in enumerate(self._experiments):
            expt.scan.set_batch_offset(i * 10 ** n)
            # This may be a different scan instance ¯\_(ツ)_/¯
            expt.imageset.get_scan().set_batch_offset(expt.scan.get_batch_offset())
            logger.debug(
                f"{expt.scan.get_batch_offset()} {expt.scan.get_batch_range()}"
            )

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
            [
                expt
                for expt in self._experiments
                if expt.identifier in experiment_identifiers
            ]
        )
        self.reflections = self.reflections.select_on_experiment_identifiers(
            experiment_identifiers
        )
        self.reflections.reset_ids()
        self.reflections.assert_experiment_identifiers_are_consistent(self.experiments)

    def filter_dose(self, dose_min, dose_max):
        from dials.command_line.slice_sequence import (
            slice_experiments,
            slice_reflections,
        )

        image_range = [
            (
                max(dose_min, expt.scan.get_image_range()[0]),
                min(dose_max, expt.scan.get_image_range()[1]),
            )
            for expt in self._experiments
        ]
        n_refl_before = self._reflections.size()
        self._experiments = slice_experiments(self._experiments, image_range)
        flex.min_max_mean_double(self._reflections["xyzobs.px.value"].parts()[2]).show()
        self._reflections = slice_reflections(self._reflections, image_range)
        flex.min_max_mean_double(self._reflections["xyzobs.px.value"].parts()[2]).show()
        logger.info(
            "%i reflections out of %i remaining after filtering for dose"
            % (self._reflections.size(), n_refl_before)
        )

    def reflections_as_miller_arrays(self, combined=False):
        from dials.util.batch_handling import (
            # calculate_batch_offsets,
            # get_batch_ranges,
            assign_batches_to_reflections,
        )
        from dials.report.analysis import scaled_data_as_miller_array

        # offsets = calculate_batch_offsets(experiments)
        reflection_tables = []
        for id_ in set(self._reflections["id"]).difference({-1}):
            reflection_tables.append(
                self._reflections.select(self._reflections["id"] == id_)
            )

        offsets = [expt.scan.get_batch_offset() for expt in self._experiments]
        reflection_tables = assign_batches_to_reflections(reflection_tables, offsets)

        if combined:
            # filter bad refls and negative scales
            batches = flex.int()
            scales = flex.double()

            for r in reflection_tables:
                sel = ~r.get_flags(r.flags.bad_for_scaling, all=False)
                sel &= r["inverse_scale_factor"] > 0
                batches.extend(r["batch"].select(sel))
                scales.extend(r["inverse_scale_factor"].select(sel))
            scaled_array = scaled_data_as_miller_array(
                reflection_tables, self._experiments
            )
            batch_array = miller.array(scaled_array, data=batches)
            scale_array = miller.array(scaled_array, data=scales)
            return scaled_array, batch_array, scale_array

        else:
            scaled_arrays = []
            batch_arrays = []
            scale_arrays = []
            for expt, r in zip(self._experiments, reflection_tables):
                sel = ~r.get_flags(r.flags.bad_for_scaling, all=False)
                sel &= r["inverse_scale_factor"] > 0
                batches = r["batch"].select(sel)
                scales = r["inverse_scale_factor"].select(sel)
                scaled_arrays.append(scaled_data_as_miller_array([r], [expt]))
                batch_arrays.append(miller.array(scaled_arrays[-1], data=batches))
                scale_arrays.append(miller.array(scaled_arrays[-1], data=scales))
            return scaled_arrays, batch_arrays, scale_arrays

    def reindex(self, cb_op, space_group=None):
        logger.info("Reindexing: %s" % cb_op)
        self._reflections["miller_index"] = cb_op.apply(
            self._reflections["miller_index"]
        )

        for expt in self._experiments:
            cryst_reindexed = expt.crystal.change_basis(cb_op)
            if space_group is not None:
                cryst_reindexed.set_space_group(space_group)
            expt.crystal.update(cryst_reindexed)

    def export_reflections(self, filename, d_min=None):
        reflections = self._reflections
        if d_min:
            reflections = reflections.select(reflections["d"] >= d_min)
        reflections.as_file(filename)
        return filename

    def export_experiments(self, filename):
        self._experiments.as_file(filename)
        return filename

    def export_unmerged_mtz(self, filename, d_min=None):
        params = export.phil_scope.extract()
        params.mtz.d_min = d_min
        params.mtz.hklout = filename
        params.intensity = ["scale"]
        export.export_mtz(params, self._experiments, [self._reflections])

    def export_merged_mtz(self, filename, d_min=None):
        params = merge.phil_scope.extract()
        params.d_min = d_min
        params.assess_space_group = False
        mtz_obj = merge.merge_data_to_mtz(
            params, self._experiments, [self._reflections]
        )
        mtz_obj.write(filename)


class MultiCrystalScale:
    def __init__(self, experiments, reflections, params):

        self._data_manager = DataManager(experiments, reflections)

        self._params = params
        if all([params.symmetry.laue_group, params.symmetry.space_group]):
            raise ValueError("Can not specify both laue_group and space_group")

        if self._params.nproc is Auto:
            self._params.nproc = get_number_cpus()
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
                if (
                    reflections.select(profile_fitted_mask)
                    .select_on_experiment_identifiers([expt.identifier])
                    .size()
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
            if (
                reflections.select(used_in_refinement_mask)
                .select_on_experiment_identifiers([expt.identifier])
                .size()
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

        self.decide_space_group()

        self._data_manager.export_unmerged_mtz(
            "scaled_unmerged.mtz", d_min=self._scaled.d_min
        )
        self._data_manager.export_merged_mtz("scaled.mtz", d_min=self._scaled.d_min)
        self._data_manager.export_experiments("scaled.expt")
        self._data_manager.export_reflections("scaled.refl", d_min=self._scaled.d_min)

        self._record_individual_report(
            self._data_manager, self._scaled.report(), "All data"
        )

        self._mca = self.multi_crystal_analysis()
        self.cluster_analysis()

        min_completeness = self._params.min_completeness
        min_multiplicity = self._params.min_multiplicity
        max_clusters = self._params.max_clusters
        if self._params.cluster_method == "cos_angle":
            clusters = self._cos_angle_clusters
        elif self._params.cluster_method == "correlation":
            clusters = self._cc_clusters
        else:
            raise ValueError("Invalid cluster method: %s" % self._params.cluster_method)
        if max_clusters or min_completeness is not None or min_multiplicity is not None:
            self._data_manager_original = self._data_manager
            cwd = os.path.abspath(os.getcwd())
            n_processed = 0
            for cluster in reversed(clusters):
                if max_clusters is not None and n_processed == max_clusters:
                    break
                if (
                    min_completeness is not None
                    and cluster.completeness < min_completeness
                ):
                    continue
                if (
                    min_multiplicity is not None
                    and cluster.multiplicity < min_multiplicity
                ):
                    continue
                if len(cluster.labels) == len(self._data_manager_original.experiments):
                    continue
                n_processed += 1

                logger.info("Scaling cluster %i:" % cluster.cluster_id)
                logger.info(cluster)
                cluster_dir = "cluster_%i" % cluster.cluster_id
                if not os.path.exists(cluster_dir):
                    os.mkdir(cluster_dir)
                os.chdir(cluster_dir)
                data_manager = copy.deepcopy(self._data_manager_original)
                cluster_identifiers = [
                    self._data_manager.ids_to_identifiers_map[l] for l in cluster.labels
                ]
                data_manager.select(cluster_identifiers)
                scaled = Scale(data_manager, self._params)

                data_manager.export_unmerged_mtz(
                    "scaled_unmerged.mtz", d_min=scaled.d_min
                )
                data_manager.export_merged_mtz("scaled.mtz", d_min=scaled.d_min)
                data_manager.export_experiments("scaled.expt")
                data_manager.export_reflections("scaled.refl", d_min=scaled.d_min)

                self._record_individual_report(
                    data_manager, scaled.report(), cluster_dir.replace("_", " ")
                )
                os.chdir(cwd)
        if self._params.filtering.method:
            # Final round of scaling, this time filtering out any bad datasets
            data_manager = copy.deepcopy(self._data_manager)
            params = copy.deepcopy(self._params)
            params.unit_cell.refine = []
            params.resolution.d_min = self._params.resolution.d_min
            scaled = Scale(data_manager, params, filtering=True)
            self.scale_and_filter_results = scaled.scale_and_filter_results
            logger.info("Scale and filtering:\n%s", self.scale_and_filter_results)

            data_manager.export_unmerged_mtz(
                "filtered_unmerged.mtz", d_min=scaled.d_min
            )
            data_manager.export_merged_mtz("filtered.mtz", d_min=scaled.d_min)

            self._record_individual_report(data_manager, scaled.report(), "Filtered")
            data_manager.export_experiments("filtered.expt")
            data_manager.export_reflections("filtered.refl", d_min=scaled.d_min)
        else:
            self.scale_and_filter_results = None

        self.report()

    def _record_individual_report(self, data_manager, report, cluster_name):
        d = self._report_as_dict(report)

        self._individual_report_dicts[cluster_name] = self._individual_report_dict(
            d, cluster_name
        )

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
        from xia2.Modules.MultiCrystalAnalysis import MultiCrystalAnalysis
        from xfel.clustering.cluster_groups import unit_cell_info

        lattice_ids = [
            self._data_manager.identifiers_to_ids_map[i]
            for i in self._data_manager.experiments.identifiers()
        ]

        clusters, dendrogram = MultiCrystalAnalysis.unit_cell_clustering(
            self._data_manager.experiments,
            lattice_ids=lattice_ids,
            threshold=self._params.unit_cell_clustering.threshold,
            log=self._params.unit_cell_clustering.log,
            plot_name=plot_name,
        )
        logger.info(unit_cell_info(clusters))
        largest_cluster_lattice_ids = None
        for cluster in clusters:
            cluster_lattice_ids = [m.lattice_id for m in cluster.members]
            if largest_cluster_lattice_ids is None:
                largest_cluster_lattice_ids = cluster_lattice_ids
            elif len(cluster_lattice_ids) > len(largest_cluster_lattice_ids):
                largest_cluster_lattice_ids = cluster_lattice_ids

        if len(largest_cluster_lattice_ids) < len(self._data_manager.experiments):
            logger.info(
                "Selecting subset of data sets for subsequent analysis: %s"
                % str(largest_cluster_lattice_ids)
            )
            cluster_identifiers = [
                self._data_manager.ids_to_identifiers_map[l]
                for l in largest_cluster_lattice_ids
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
        from xia2.command_line.multi_crystal_analysis import phil_scope as mca_phil

        params = mca_phil.extract()
        params.prefix = "xia2.multiplex"
        params.title = "xia2.multiplex report"
        mca = MultiCrystalReport(params=params, data_manager=self._data_manager)
        return mca

    def report(self):
        self._mca.report(
            self._individual_report_dicts,
            self._comparison_graphs,
            self._cosym_analysis,
            image_range_table=self._individual_report_dicts["All data"][
                "image_range_table"
            ],
            scale_and_filter_results=self.scale_and_filter_results,
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
    def scaled_mtz(self):
        return self._scaled_mtz

    @property
    def scaled_unmerged_mtz(self):
        return self._scaled_unmerged_mtz

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

        # need to set unmerged_mtz, merged_mtz in Scale wrapper
        unmerged_mtz = os.path.join(
            scaler.get_working_directory(), "%i_scaled_unmerged.mtz" % scaler.get_xpid()
        )
        merged_mtz = os.path.join(
            scaler.get_working_directory(), "%i_scaled.mtz" % scaler.get_xpid()
        )
        scaler.set_scaled_unmerged_mtz(unmerged_mtz)
        scaler.set_scaled_mtz(merged_mtz)

        # Set default scaling model
        if self._params.scaling.model in (None, "auto", Auto):
            self._params.scaling.model = "physical"
        scaler.set_model(self._params.scaling.model)

        lmax = self._params.scaling.secondary.lmax
        if lmax:
            scaler.set_absorption_correction(True)
            scaler.set_lmax(lmax)
        else:
            scaler.set_absorption_correction(False)

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
        if self._params.scaling.Isigma_range is not None:
            scaler.set_isigma_selection(self._params.scaling.Isigma_range)
        if self._params.scaling.min_partiality is not None:
            scaler.set_min_partiality(self._params.scaling.min_partiality)
        if self._params.scaling.partiality_cutoff is not None:
            scaler.set_partiality_cutoff(self._params.scaling.partiality_cutoff)

        scaler.set_full_matrix(False)

        scaler.set_outlier_rejection(self._params.scaling.outlier_rejection)

        if self._filtering:
            scaler.set_filtering_method(self._params.filtering.method)
            scaler.set_deltacchalf_max_cycles(
                self._params.filtering.deltacchalf.max_cycles
            )
            scaler.set_deltacchalf_min_completeness(
                self._params.filtering.deltacchalf.min_completeness
            )
            scaler.set_deltacchalf_stdcutoff(
                self._params.filtering.deltacchalf.stdcutoff
            )

        scaler.scale()
        self._scaled_mtz = scaler.get_scaled_mtz()
        self._scaled_unmerged_mtz = scaler.get_scaled_unmerged_mtz()
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

        if len(resolution_limits):
            resolution = max(resolution_limits)
            reasoning = [
                reason
                for limit, reason in zip(resolution_limits, reasoning)
                if limit >= resolution
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
        report = Report.Report.from_data_manager(self._data_manager, params=params)
        return report
