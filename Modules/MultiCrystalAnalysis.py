import json
import logging
from collections import OrderedDict

from dials.algorithms.scaling.scale_and_filter import make_scaling_filtering_plots
from dials.algorithms.symmetry.cosym import SymmetryAnalysis
from dials.algorithms.symmetry.cosym.plots import plot_coords, plot_rij_histogram
from dials.util.filter_reflections import filtered_arrays_from_experiments_reflections
from dials.util.multi_dataset_handling import parse_multiple_datasets

from xia2.Modules.MultiCrystal.ScaleAndMerge import DataManager
from xia2.Modules.Analysis import batch_phil_scope
from xia2.Modules.DeltaCcHalf import DeltaCcHalf
from xia2.XIA2Version import Version

from libtbx import phil


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
        from dials.algorithms.clustering.unit_cell import UnitCellCluster

        crystal_symmetries = []
        for expt in experiments:
            crystal_symmetry = expt.crystal.get_crystal_symmetry(
                assert_is_compatible_unit_cell=False
            )
            crystal_symmetries.append(crystal_symmetry.niggli_cell())
        ucs = UnitCellCluster.from_crystal_symmetries(
            crystal_symmetries, lattice_ids=lattice_ids
        )
        if plot_name is not None:
            import matplotlib

            matplotlib.use("Agg")
            from matplotlib import pyplot as plt

            plt.figure("Andrews-Bernstein distance dendogram", figsize=(12, 8))
            ax = plt.gca()
        else:
            ax = None
        clusters, dendrogram, _ = ucs.ab_cluster(
            threshold,
            log=log,
            labels="lattice_id",
            write_file_lists=False,
            schnell=False,
            doplot=(plot_name is not None),
            ax=ax,
        )
        if plot_name is not None:
            plt.tight_layout()
            plt.savefig(plot_name)
            plt.clf()
        return clusters, dendrogram

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
            plot_coords(
                mca.cosym.coords, mca.cosym.cluster_labels, key="cosym_coordinates_sg"
            )
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

        clustering, dendrogram = self.unit_cell_clustering(
            experiments,
            lattice_ids,
            threshold=self.params.unit_cell_clustering.threshold,
            log=self.params.unit_cell_clustering.log,
        )
        from dials.algorithms.clustering.plots import scipy_dendrogram_to_plotly_json

        d["uc_clustering"] = scipy_dendrogram_to_plotly_json(
            dendrogram,
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


class MultiCrystalReport(MultiCrystalAnalysis):
    def report(
        self,
        individual_dataset_reports,
        comparison_graphs,
        cosym_analysis,
        image_range_table,
        scale_and_filter_results=None,
    ):
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
            filter_plots = self.make_scale_and_filter_plots(scale_and_filter_results)[
                "filter_plots"
            ]
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

        self._data_manager.export_experiments("tmp.expt")

        from jinja2 import Environment, ChoiceLoader, PackageLoader

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
                )
            }
        json_data["comparison"] = comparison_graphs

        with open("%s.json" % self.params.prefix, "w") as f:
            json.dump(json_data, f)

        with open("%s.html" % self.params.prefix, "wb") as f:
            f.write(html.encode("utf-8", "xmlcharrefreplace"))

    def make_scale_and_filter_plots(self, filtering_results):
        data = {
            "merging_stats": filtering_results.get_merging_stats(),
            "initial_expids_and_image_ranges": filtering_results.initial_expids_and_image_ranges,
            "cycle_results": filtering_results.get_cycle_results(),
            "expids_and_image_ranges": filtering_results.expids_and_image_ranges,
            "mode": "dataset",
        }
        return {"filter_plots": make_scaling_filtering_plots(data)}
