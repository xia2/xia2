from __future__ import annotations

import copy
import json
import logging
from collections import OrderedDict
from itertools import combinations
from typing import Any

import iotbx.phil
import pandas as pd
from dials.algorithms.clustering.unit_cell import ClusteringResult, cluster_unit_cells
from dials.algorithms.correlation.cluster import ClusterInfo
from dials.algorithms.scaling.scale_and_filter import (
    AnalysisResults,
    make_scaling_filtering_plots,
)
from dials.algorithms.symmetry.cosym import SymmetryAnalysis
from dials.array_family import flex
from dials.util import tabulate
from dxtbx.model import ExperimentList
from dxtbx.serialize import load
from libtbx import phil

from xia2.Modules.Analysis import batch_phil_scope
from xia2.Modules.MultiCrystal.data_manager import DataManager
from xia2.Wrappers.Dials.Functional.CorrelationMatrix import DialsCorrelationMatrix
from xia2.Wrappers.Dials.Functional.DeltaCCHalf import DeltaCCHalf
from xia2.Wrappers.Dials.Functional.StereographicProjection import (
    StereographicProjection,
)
from xia2.XIA2Version import Version

logger = logging.getLogger(__name__)


class MultiCrystalAnalysis:
    def __init__(
        self,
        params: iotbx.phil.scope_extract,
        experiments: ExperimentList | None = None,
        reflections: flex.reflection_table | None = None,
        data_manager: DataManager | None = None,
    ):
        self.params = params
        self._cluster_analysis_run: bool = False
        if data_manager is not None:
            self._data_manager = data_manager
        else:
            assert experiments is not None and reflections is not None
            self._data_manager = DataManager(experiments, reflections)

        self._intensities_separate = self._data_manager.reflections_as_miller_arrays()
        (
            self.intensities,
            self.batches,
            self.scales,
        ) = self._data_manager.reflections_as_miller_arrays(combined=True)
        self.params.batch = []
        scope = phil.parse(batch_phil_scope)
        for expt in self._data_manager.experiments:
            batch_params = scope.extract().batch[0]
            batch_params.id = self._data_manager.identifiers_to_ids_map[expt.identifier]

            if not self._data_manager.all_stills:
                batch_params.range = expt.scan.get_batch_range()
                self.params.batch.append(batch_params)

        self.intensities.set_observation_type_xray_intensity()

    @staticmethod
    def stereographic_projections(
        experiments_filename: str, labels: list[int] | None = None
    ) -> dict[tuple[int, int, int], str]:
        sp_json_files = {}
        sp = StereographicProjection()
        if labels:
            sp.labels = [str(i) for i in labels]
        expts = load.experiment_list(experiments_filename, check_format=False)
        for hkl in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
            sp.hkl = hkl
            sp.run(expts)
            sp_json_files[hkl] = str(sp.json_filename)

        return sp_json_files

    @staticmethod
    def unit_cell_clustering(
        experiments: ExperimentList,
        lattice_ids: list[int],
        threshold: float,
        log: bool = True,
        plot_name: str | None = None,
    ) -> ClusteringResult | None:
        crystal_symmetries = []
        for expt in experiments:
            crystal_symmetry = expt.crystal.get_crystal_symmetry(
                assert_is_compatible_unit_cell=False
            )
            crystal_symmetries.append(crystal_symmetry.niggli_cell())

        if plot_name is not None:
            import matplotlib

            matplotlib.use("Agg")
            from matplotlib import pyplot as plt

            plt.figure("Andrews-Bernstein distance dendogram", figsize=(12, 8))
            ax = plt.gca()
        else:
            ax = None

        clustering: ClusteringResult | None = cluster_unit_cells(
            crystal_symmetries,
            lattice_ids=lattice_ids,
            threshold=threshold,
            ax=ax,
            no_plot=plot_name is None,
        )

        if plot_name is not None:
            plt.tight_layout()
            plt.savefig(plot_name)
            plt.clf()

        return clustering

    def cluster_analysis(self) -> None:
        reflections = []
        identifiers = []
        filtered_ids_to_identifiers_map = copy.deepcopy(
            self._data_manager.ids_to_identifiers_map
        )

        for i in self._data_manager.experiments:
            selected = self._data_manager.reflections.select_on_experiment_identifiers(
                [i.identifier]
            )
            selected.reset_ids()
            reflections.append(selected)
            identifiers.append(i.identifier)

        to_delete = []
        for i in filtered_ids_to_identifiers_map:
            if filtered_ids_to_identifiers_map[i] not in identifiers:
                to_delete.append(i)

        for i in to_delete:
            filtered_ids_to_identifiers_map.pop(i)

        intensity_clustering = DialsCorrelationMatrix()
        intensity_clustering.ids_to_identifiers_map = filtered_ids_to_identifiers_map
        intensity_clustering.set_buffer(
            self.params.significant_clusters.min_points_buffer
        )
        intensity_clustering.set_xi(self.params.significant_clusters.xi)
        intensity_clustering.run(self._data_manager.experiments, reflections)

        self.cc_clusters: list[ClusterInfo] = intensity_clustering.correlation_clusters
        self.cos_clusters: list[ClusterInfo] = intensity_clustering.cos_angle_clusters
        self._cc_cluster_json: dict[str, Any] = intensity_clustering.cc_json
        self._cos_angle_cluster_json: dict[str, Any] = intensity_clustering.cos_json
        self._cc_cluster_table: list[list[str]] = intensity_clustering.cc_table
        self._cos_angle_cluster_table: list[list[str]] = intensity_clustering.cos_table
        self._cosym_graphs: OrderedDict[str, dict[str, Any]] = (
            intensity_clustering.rij_graphs
        )
        self.significant_coordinate_clusters: list[ClusterInfo] = (
            intensity_clustering.significant_clusters
        )
        self._pca_plot: dict[str, Any] = intensity_clustering.pca_plot

        data_in_clusters = 0
        for i in self.significant_coordinate_clusters:
            data_in_clusters += len(i.labels)

        outliers = len(self._data_manager.experiments) - data_in_clusters

        logger.info("\nIntensity correlation clustering summary:")
        logger.info(
            tabulate(self._cc_cluster_table, headers="firstrow", tablefmt="rst")
        )
        logger.info("\nCos(angle) clustering summary:")
        logger.info(
            tabulate(self._cos_angle_cluster_table, headers="firstrow", tablefmt="rst")
        )
        logger.info(
            f"OPTICS identified {len(self.significant_coordinate_clusters)} clusters and {outliers} outlier datasets."
        )
        for i in self.significant_coordinate_clusters:
            logger.info(i)

        # Need this here or else cos-angle dendrogram does not replicate original multiplex output
        self._cluster_analysis_run = True

    def unit_cell_analysis(self) -> OrderedDict:
        from dials.command_line.unit_cell_histogram import uc_params_from_experiments

        # from dials.command_line.unit_cell_histogram import panel_distances_from_experiments

        experiments = self._data_manager.experiments
        lattice_ids = [
            self._data_manager.identifiers_to_ids_map[i]
            for i in experiments.identifiers()
        ]
        uc_params = uc_params_from_experiments(experiments)
        # panel_distances = panel_distances_from_experiments(experiments)

        d = OrderedDict()
        from xia2.Modules.MultiCrystal.plots import plot_uc_histograms

        d.update(plot_uc_histograms(uc_params))
        # self._plot_uc_vs_detector_distance(uc_params, panel_distances, outliers, params.steps_per_angstrom)
        # self._plot_number_of_crystals(experiments)

        clustering = self.unit_cell_clustering(
            experiments,
            lattice_ids,
            threshold=self.params.unit_cell_clustering.threshold,
            log=self.params.unit_cell_clustering.log,
        )
        from dials.algorithms.clustering.plots import scipy_dendrogram_to_plotly_json

        if clustering:
            d["uc_clustering"] = scipy_dendrogram_to_plotly_json(
                clustering.dendrogram,
                title="Unit cell clustering",
                xtitle="Dataset",
                ytitle="Distance (Å<sup>2</sup>)",
                help="""\
    The results of single-linkage hierarchical clustering on the unit cell parameters using
    the Andrews–Bernstein NCDist distance metric (Andrews & Bernstein, 2014). The height at
    which two clusters are merged in the dendrogram is a measure of the similarity between
    the unit cells in each cluster. A larger separation between two clusters may be
    indicative of a higher degree of non-isomorphism between the clusters. Conversely, a
    small separation between two clusters suggests that their unit cell parameters are
    relatively isomorphous.
    """,
            )
        else:
            d["uc_clustering"] = {}
        return d

    def delta_cc_half_analysis(
        self,
    ) -> tuple[dict[str, dict[str, Any]], list[list[str]]]:
        deltacc = DeltaCCHalf()
        deltacc.run(self._data_manager.experiments, self._data_manager.reflections)
        return deltacc.delta_cc_half_graphs, deltacc.delta_cc_half_table

    @staticmethod
    def interesting_cluster_identification(
        clusters: list[ClusterInfo], params: iotbx.phil.scope_extract
    ) -> tuple[list[str], list[ClusterInfo]]:
        cluster_numbers = []
        heights = []
        labels = []
        number_of_datasets = []
        for cluster in clusters:
            # Because analysing each possible pair of clusters, to cut down computation time do initial filtering here

            if len(cluster.labels) >= params.min_cluster_size:
                cluster_numbers.append("cluster_" + str(cluster.cluster_id))
                heights.append(cluster.height)
                labels.append(cluster.labels)
                number_of_datasets.append(len(cluster.labels))

        c_data = {
            "Cluster Number": cluster_numbers,
            "Height": heights,
            "Datasets": labels,
            "Length": number_of_datasets,
        }

        cluster_data = pd.DataFrame(c_data)

        clusters_to_compare_unfiltered = []
        clusters_for_analysis = []

        if len(cluster_data["Cluster Number"]) > 0:
            # Find all combinations of pairs

            cluster_pairs = list(combinations(cluster_data["Cluster Number"], 2))

            # Add together length, and see if there are any common datasets

            for pair in cluster_pairs:
                length_1 = cluster_data.loc[
                    cluster_data["Cluster Number"] == pair[0], "Length"
                ].iloc[0]
                length_2 = cluster_data.loc[
                    cluster_data["Cluster Number"] == pair[1], "Length"
                ].iloc[0]
                datasets_1 = cluster_data.loc[
                    cluster_data["Cluster Number"] == pair[0], "Datasets"
                ].iloc[0]
                datasets_2 = cluster_data.loc[
                    cluster_data["Cluster Number"] == pair[1], "Datasets"
                ].iloc[0]
                c1 = set(datasets_1)
                c2 = set(datasets_2)
                duplicates = c1.intersection(c2)

                # If no common datasets, see if length AND combined dataset list match a real cluster

                if len(duplicates) == 0:
                    total_number_of_datasets = length_1 + length_2
                    datasets_to_look_for = sorted(datasets_1 + datasets_2)
                    try:
                        test = cluster_data.loc[
                            (cluster_data["Length"] == total_number_of_datasets)
                        ]
                    except ValueError:
                        print("Not a real cluster")
                    else:
                        for item in test["Datasets"]:
                            if sorted(item) == datasets_to_look_for:
                                clusters_to_compare_unfiltered.append(pair)

            # Finally filter by maximum number allowed to output

            logger.info(clusters_to_compare_unfiltered)

            # Check if clusters ordered largest -> smallest or vice versa

            if c_data["Length"][0] > c_data["Length"][-1]:
                final_clusters_to_compare = clusters_to_compare_unfiltered[
                    : params.max_output_clusters
                ]
            else:
                final_clusters_to_compare = clusters_to_compare_unfiltered[
                    -params.max_output_clusters :
                ]

            if len(final_clusters_to_compare) > 0:
                for pair in final_clusters_to_compare:
                    clusters_for_analysis.append(pair[0])
                    clusters_for_analysis.append(pair[1])

            elif len(final_clusters_to_compare) == 0:
                logger.info(
                    "No interesting clusters found, rerun with different parameters"
                )

            clusters_for_analysis = list(dict.fromkeys(clusters_for_analysis))

        else:
            logger.info(
                "Min cluster size of "
                + str(params.min_cluster_size)
                + " excludes all clusters. Please re-run using a smaller minimum size."
            )
            clusters_for_analysis = []
            final_clusters_to_compare = []

        file_data: list[str] = [
            "Compare each pair of clusters below",
            "They have no datasets in common",
        ]

        for item in final_clusters_to_compare:
            file_data.append(item[0] + " and " + item[1])

        file_data.extend(
            [
                "Selected with a maximum number of cluster pairs set at:"
                + str(params.max_output_clusters),
                "Total Number of Clusters for Analysis:"
                + str(len(clusters_for_analysis)),
                "Discrete list of clusters saved: ",
            ]
        )

        for item in clusters_for_analysis:
            file_data.append(item)

        for item in file_data:
            logger.info(item)

        return file_data, clusters_for_analysis


class MultiCrystalReport(MultiCrystalAnalysis):
    def report(
        self,
        individual_dataset_reports: dict[str, dict[str, Any]],
        comparison_graphs: dict[str, dict[str, Any]],
        cosym_analysis: dict[str, Any],
        image_range_table: list[list[str]],
        scale_and_filter_results: AnalysisResults | None = None,
        scale_and_filter_mode: str | None = None,
    ) -> None:
        self._data_manager.export_experiments("tmp.expt")
        unit_cell_graphs = self.unit_cell_analysis()

        if not self._cluster_analysis_run:
            self.cluster_analysis()

        labels = [
            self._data_manager.identifiers_to_ids_map[i]
            for i in self._data_manager.experiments.identifiers()
        ]
        self._stereographic_projection_files = self.stereographic_projections(
            "tmp.expt", labels=labels
        )

        delta_cc_half_graphs, delta_cc_half_table = self.delta_cc_half_analysis()

        if scale_and_filter_results:
            filter_plots = self.make_scale_and_filter_plots(
                scale_and_filter_results, scale_and_filter_mode
            )["filter_plots"]
        else:
            filter_plots = None

        symmetry_analysis = {}
        if "sym_op_scores" in cosym_analysis:
            symmetry_analysis["sym_ops_table"] = SymmetryAnalysis.sym_ops_table(
                cosym_analysis
            )
            symmetry_analysis["subgroups_table"] = SymmetryAnalysis.subgroups_table(
                cosym_analysis
            )
            symmetry_analysis["summary_table"] = SymmetryAnalysis.summary_table(
                cosym_analysis
            )

        styles = {}
        orientation_graphs = OrderedDict()
        for hkl in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
            with open(self._stereographic_projection_files[hkl], "rb") as f:
                d = json.load(f)
                d["layout"]["title"] = "Stereographic projection (hkl=%i%i%i)" % hkl
                d["help"] = (
                    """\
Stereographic projections of hkl=%i%i%i directions (and symmetry equivalents) for each
crystal in the laboratory frame perpendicular to the beam. Directions that are close to
the centre are close to parallel with the beam vector, whereas directions at the edge of
the circle are perpendicular with the beam vector. A random distribution of points
within the circle would suggest a random distribution of crystal orientations, whereas
any systematic grouping of points may suggest a preferential crystal orientation.
"""
                    % hkl
                )
                key = "stereographic_projection_{}{}{}".format(*hkl)
                orientation_graphs[key] = d
                styles[key] = "square-plot"

        from jinja2 import ChoiceLoader, Environment, PackageLoader

        loader = ChoiceLoader(
            [PackageLoader("xia2", "templates"), PackageLoader("dials", "templates")]
        )
        env = Environment(loader=loader)
        template = env.get_template("multiplex.html")
        html = template.render(
            page_title=self.params.title,
            space_group=self.intensities.space_group_info().symbol_and_number(),
            unit_cell=str(self.intensities.unit_cell()),
            cc_half_significance_level=self.params.cc_half_significance_level,
            unit_cell_graphs=unit_cell_graphs,
            cosym_graphs=cosym_analysis["cosym_graphs"],
            orientation_graphs=orientation_graphs,
            cc_cluster_table=self._cc_cluster_table,
            cc_cluster_json=self._cc_cluster_json,
            cos_angle_cluster_table=self._cos_angle_cluster_table,
            cos_angle_cluster_json=self._cos_angle_cluster_json,
            cos_angle_cosym_graphs=self._cosym_graphs,
            pca_plot=self._pca_plot,
            delta_cc_half_graphs=delta_cc_half_graphs,
            delta_cc_half_table=delta_cc_half_table,
            filter_plots=filter_plots,
            image_range_tables=[image_range_table],
            individual_dataset_reports=individual_dataset_reports,
            comparison_graphs=comparison_graphs,
            symmetry_analysis=symmetry_analysis,
            styles=styles,
            xia2_version=Version,
        )

        json_data: dict = {}
        json_data.update(unit_cell_graphs)
        json_data.update(cosym_analysis["cosym_graphs"])
        json_data["cc_clustering"] = self._cc_cluster_json
        json_data["cos_angle_clustering"] = self._cos_angle_cluster_json
        json_data["pca_clustering"] = self._pca_plot
        json_data.update(self._cosym_graphs)
        json_data.update(delta_cc_half_graphs)
        json_data.update(orientation_graphs)
        if filter_plots:
            json_data.update(filter_plots)
        json_data["datasets"] = {}
        for report_name, report in individual_dataset_reports.items():
            json_data["datasets"][report_name] = {
                k: report[k]
                for k in (
                    "resolution_graphs",
                    "batch_graphs",
                    "xtriage",
                    "merging_stats",
                    "merging_stats_anom",
                    "misc_graphs",
                )
            }
        json_data["comparison"] = comparison_graphs

        with open("%s.json" % self.params.prefix, "w") as f:
            json.dump(json_data, f)

        with open("%s.html" % self.params.prefix, "wb") as f:
            f.write(html.encode("utf-8", "xmlcharrefreplace"))

    def make_scale_and_filter_plots(
        self, filtering_results: AnalysisResults, mode: str | None
    ) -> dict[str, dict]:
        data = {
            "merging_stats": filtering_results.get_merging_stats(),
            "initial_expids_and_image_ranges": filtering_results.initial_expids_and_image_ranges,
            "cycle_results": filtering_results.get_cycle_results(),
            "expids_and_image_ranges": filtering_results.expids_and_image_ranges,
            "mode": mode,
        }
        return {"filter_plots": make_scaling_filtering_plots(data)}
