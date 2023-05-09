from __future__ import annotations

import json
import logging
from collections import OrderedDict
from statistics import mean

import pandas as pd

from dials.algorithms.clustering.unit_cell import cluster_unit_cells
from dials.algorithms.scaling.scale_and_filter import make_scaling_filtering_plots
from dials.algorithms.symmetry.cosym import SymmetryAnalysis
from dials.algorithms.symmetry.cosym.plots import plot_coords, plot_rij_histogram
from dials.util.filter_reflections import filtered_arrays_from_experiments_reflections
from dials.util.multi_dataset_handling import parse_multiple_datasets
from libtbx import phil

from xia2.Modules.Analysis import batch_phil_scope
from xia2.Modules.DeltaCcHalf import DeltaCcHalf
from xia2.Modules.MultiCrystal.data_manager import DataManager
from xia2.XIA2Version import Version

logger = logging.getLogger(__name__)


class MultiCrystalAnalysis:
    def __init__(self, params, experiments=None, reflections=None, data_manager=None):
        self.params = params
        self._cluster_analysis = None
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
    def stereographic_projections(experiments_filename, labels=None):
        from xia2.Wrappers.Dials.StereographicProjection import StereographicProjection

        sp_json_files = {}
        for hkl in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
            sp = StereographicProjection()
            sp.add_experiments(experiments_filename)
            sp.set_hkl(hkl)
            if labels:
                sp.set_labels(labels)
            sp.run()
            sp_json_files[hkl] = sp.get_json_filename()
        return sp_json_files

    @staticmethod
    def unit_cell_clustering(
        experiments, lattice_ids, threshold, log=True, plot_name=None
    ):
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

        clustering = cluster_unit_cells(
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

    def cluster_analysis(self):
        from xia2.Modules.MultiCrystal import multi_crystal_analysis

        labels = [
            self._data_manager.identifiers_to_ids_map[i]
            for i in self._data_manager.experiments.identifiers()
        ]
        mca = multi_crystal_analysis(
            self._intensities_separate[0], labels=labels, prefix=None
        )

        self._cc_cluster_json = mca.to_plotly_json(
            mca.cc_matrix, mca.cc_linkage_matrix, labels=labels
        )
        self._cc_cluster_table = mca.as_table(mca.cc_clusters)

        self._cos_angle_cluster_json = mca.to_plotly_json(
            mca.cos_angle_matrix,
            mca.cos_angle_linkage_matrix,
            labels=labels,
            matrix_type="cos_angle",
        )
        self._cos_angle_cluster_table = mca.as_table(mca.cos_angle_clusters)

        self._cosym_graphs = OrderedDict()
        self._cosym_graphs.update(
            plot_rij_histogram(
                mca.cosym.target.rij_matrix, key="cosym_rij_histogram_sg"
            )
        )
        self._cosym_graphs.update(
            plot_coords(mca.cosym.coords, key="cosym_coordinates_sg")
        )

        self._cluster_analysis = mca
        return self._cluster_analysis

    def unit_cell_analysis(self):
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

        return d

    def delta_cc_half_analysis(self):
        # transform models into miller arrays
        intensities, batches = filtered_arrays_from_experiments_reflections(
            self._data_manager.experiments,
            parse_multiple_datasets([self._data_manager.reflections]),
            outlier_rejection_after_filter=False,
            partiality_threshold=0.99,
            return_batches=True,
        )
        result = DeltaCcHalf(intensities, batches)
        d = {}
        d.update(result.histogram())
        d.update(result.normalised_scores())
        return d, result.get_table(html=True)

    @staticmethod
    def interesting_cluster_identification(clusters, params):

        # Note: this algorithm could do with a second opinion and some work... but does an ok job on the test cases looked at

        cluster_numbers = []
        heights = []
        labels = []
        for cluster in clusters:
            cluster_numbers.append("cluster_" + str(cluster.cluster_id))
            heights.append(cluster.height)
            labels.append(cluster.labels)

        c_data = {
            "Cluster Number": cluster_numbers,
            "Height": heights,
            "Datasets": labels,
        }

        cluster_data = pd.DataFrame(c_data)

        dataset_dict = {}

        for i, j in zip(cluster_data["Cluster Number"], cluster_data["Datasets"]):
            dataset_dict[i] = j

        reversed_dataset_dict = dict(reversed(list(dataset_dict.items())))

        array_of_clusters_and_heights = []
        for item in sorted(
            reversed_dataset_dict,
            key=lambda k: len(reversed_dataset_dict[k]),
            reverse=False,
        ):
            new_cluster_data = [
                set(dataset_dict[item]),
                float(
                    cluster_data.loc[
                        cluster_data["Cluster Number"] == item, "Height"
                    ].iloc[0]
                ),
                item,
            ]
            array_of_clusters_and_heights.append(new_cluster_data)

        series_of_covering_clusters = []

        for x, i in enumerate(array_of_clusters_and_heights):
            do_i_need_a_new_series = True
            for j in series_of_covering_clusters:
                if i[0].issuperset(j[-1][0]):
                    j.append(i)
                    do_i_need_a_new_series = False
                    break
            if do_i_need_a_new_series:
                series_of_covering_clusters.append([i])

        final_clusters_to_compare = []
        clusters_for_analysis = []
        first_ones = []

        for f, i in enumerate(series_of_covering_clusters):
            for j in series_of_covering_clusters[f:]:
                if set.intersection(i[0][0], j[0][0]) == set():
                    flag = False
                    for x in reversed(i):
                        for y in reversed(j):
                            if set.intersection(x[0], y[0]) == set():
                                if (
                                    abs(x[1] - y[1])
                                    <= params.max_cluster_height_difference
                                ):
                                    if (
                                        len(x[0]) >= params.min_cluster_size
                                        and len(y[0]) >= params.min_cluster_size
                                    ):
                                        final_clusters_to_compare.append(
                                            (x[2], y[2], mean([len(x[0]), len(y[0])]))
                                        )
                                        clusters_for_analysis.append(x[2])
                                        first_ones.append(x[2])
                                        clusters_for_analysis.append(y[2])
                                        flag = True
                                        break
                        if flag:
                            break

        # Getting rid of cases of sub clusters - first, find all that have subsets - then choose the one closest in height to the parent

        first_ones = sorted(dict.fromkeys(first_ones))

        dict_for_sub_clusters = {}

        for item in first_ones:
            clusters = []
            for j in final_clusters_to_compare:
                if j[0] == item:
                    clusters.append(j[1])
            dict_for_sub_clusters[item] = clusters

        for key in dict_for_sub_clusters:
            good_clusters = []
            for idx, item in enumerate(dict_for_sub_clusters[key]):
                if idx > 0:
                    subset_flag = False
                    for j in good_clusters:
                        if set(dataset_dict[item]).issubset(set(dataset_dict[j])):
                            subset_flag = True
                            height_in_list = cluster_data.loc[
                                cluster_data["Cluster Number"] == j, "Height"
                            ].iloc[0]
                            height_of_new = cluster_data.loc[
                                cluster_data["Cluster Number"] == item, "Height"
                            ].iloc[0]
                            height_of_parent = cluster_data.loc[
                                cluster_data["Cluster Number"] == key, "Height"
                            ].iloc[0]
                            list_diff = abs(height_in_list - height_of_parent)
                            new_diff = abs(height_of_new - height_of_parent)

                            if list_diff > new_diff:
                                good_clusters.remove(j)
                                good_clusters.append(item)
                    if not subset_flag:
                        good_clusters.append(item)
                elif idx == 0:
                    good_clusters.append(item)

            dict_for_sub_clusters[key] = good_clusters

        real_final_clusters_to_compare = []

        for item in final_clusters_to_compare:
            if item[1] in dict_for_sub_clusters[item[0]]:
                real_final_clusters_to_compare.append(item)

        if len(real_final_clusters_to_compare) > params.max_output_clusters:
            limited_clusters_to_compare = sorted(
                real_final_clusters_to_compare, key=lambda x: x[2], reverse=True
            )
            real_final_clusters_to_compare = limited_clusters_to_compare[
                0 : params.max_output_clusters
            ]
            clusters_for_analysis = []
            for i in real_final_clusters_to_compare:
                for idx, j in enumerate(i):
                    if idx == 0 or idx == 1:
                        clusters_for_analysis.append(j)
        elif len(real_final_clusters_to_compare) == 0:
            logger.info(
                "No interesting clusters found, rerun with different parameters"
            )
            clusters_for_analysis = []

        clusters_for_analysis = list(dict.fromkeys(clusters_for_analysis))

        list_of_clusters = []
        file_data = [
            "Compare each pair of clusters below",
            "They have no datasets in common",
        ]

        for item in real_final_clusters_to_compare:
            file_data.append(item[0] + " and " + item[1])

        file_data.extend(
            [
                "Selected with heights required to be closer than:"
                + str(params.max_cluster_height_difference),
                "And a maximum number of cluster pairs set at:"
                + str(params.max_output_clusters),
                "Total Number of Clusters for Analysis:"
                + str(len(clusters_for_analysis)),
                "Discrete list of clusters saved: ",
            ]
        )

        for item in clusters_for_analysis:
            file_data.append(item)
            list_of_clusters.append(item)

        for item in file_data:
            logger.info(item)

        return file_data, list_of_clusters


class MultiCrystalReport(MultiCrystalAnalysis):
    def report(
        self,
        individual_dataset_reports,
        comparison_graphs,
        cosym_analysis,
        image_range_table,
        scale_and_filter_results=None,
        scale_and_filter_mode=None,
    ):
        self._data_manager.export_experiments("tmp.expt")
        unit_cell_graphs = self.unit_cell_analysis()
        if self._cluster_analysis is None:
            self._cluster_analysis = self.cluster_analysis()

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
                key = "stereographic_projection_%s%s%s" % hkl
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

        json_data = {}
        json_data.update(unit_cell_graphs)
        json_data.update(cosym_analysis["cosym_graphs"])
        json_data["cc_clustering"] = self._cc_cluster_json
        json_data["cos_angle_clustering"] = self._cos_angle_cluster_json
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

    def make_scale_and_filter_plots(self, filtering_results, mode):
        data = {
            "merging_stats": filtering_results.get_merging_stats(),
            "initial_expids_and_image_ranges": filtering_results.initial_expids_and_image_ranges,
            "cycle_results": filtering_results.get_cycle_results(),
            "expids_and_image_ranges": filtering_results.expids_and_image_ranges,
            "mode": mode,
        }
        return {"filter_plots": make_scaling_filtering_plots(data)}
