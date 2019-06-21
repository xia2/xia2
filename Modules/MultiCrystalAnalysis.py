# -*- coding: utf-8 -*-
#!/usr/bin/env xia2.python
from __future__ import absolute_import, division, print_function

import json
import logging
import sys
from collections import OrderedDict

from xia2.Modules.Report import xia2_report_base
from xia2.XIA2Version import Version
from xia2.Modules.MultiCrystal.ScaleAndMerge import DataManager
from xia2.Modules.Analysis import batch_phil_scope

from libtbx import phil


logger = logging.getLogger(__name__)


class multi_crystal_analysis(xia2_report_base):
    def __init__(self, params, experiments=None, reflections=None, data_manager=None):
        super(multi_crystal_analysis, self).__init__(params)
        if data_manager is not None:
            self._data_manager = data_manager
        else:
            assert experiments is not None and reflections is not None
            self._data_manager = DataManager(experiments, reflections)

        self._intensities_separate = self._data_manager.reflections_as_miller_arrays(
            intensity_key="intensity.scale.value", return_batches=True
        )
        self.intensities = self._intensities_separate[0][0].deep_copy()
        self.batches = self._intensities_separate[0][1].deep_copy()
        for intensities, batches in self._intensities_separate[1:]:
            self.intensities = self.intensities.concatenate(
                intensities, assert_is_similar_symmetry=False
            )
            self.batches = self.batches.concatenate(
                batches, assert_is_similar_symmetry=False
            )

        self.params.batch = []
        scope = phil.parse(batch_phil_scope)
        for expt in self._data_manager.experiments:
            batch_params = scope.extract().batch[0]
            batch_params.id = expt.identifier
            batch_params.range = expt.scan.get_batch_range()
            self.params.batch.append(batch_params)

        self.intensities.set_observation_type_xray_intensity()

    @staticmethod
    def stereographic_projections(experiments_filename):
        from xia2.Wrappers.Dials.StereographicProjection import StereographicProjection

        sp_json_files = {}
        for hkl in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
            sp = StereographicProjection()
            sp.add_experiments(experiments_filename)
            sp.set_hkl(hkl)
            sp.run()
            sp_json_files[hkl] = sp.get_json_filename()
        return sp_json_files

    @staticmethod
    def unit_cell_clustering(experiments, threshold, log=True, plot_name=None):
        from dials.algorithms.clustering.unit_cell import UnitCellCluster

        crystal_symmetries = []
        for expt in experiments:
            crystal_symmetry = expt.crystal.get_crystal_symmetry(
                assert_is_compatible_unit_cell=False
            )
            crystal_symmetries.append(crystal_symmetry.niggli_cell())
        lattice_ids = [expt.identifier for expt in experiments]
        ucs = UnitCellCluster.from_crystal_symmetries(
            crystal_symmetries, lattice_ids=lattice_ids
        )
        if plot_name is not None:
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

    def radiation_damage_analysis(self):
        from dials.pychef import Statistics

        miller_arrays = self._data_manager.reflections_as_miller_arrays(
            return_batches=True
        )
        for i, (intensities, batches) in enumerate(miller_arrays):
            # convert batches to dose
            data = (
                batches.data()
                - self._data_manager.experiments[i].scan.get_batch_offset()
            )
            miller_arrays[i][1] = batches.array(data=data).set_info(batches.info())
        intensities, dose = miller_arrays[0]
        for (i, d) in miller_arrays[1:]:
            intensities = intensities.concatenate(i, assert_is_similar_symmetry=False)
            dose = dose.concatenate(d, assert_is_similar_symmetry=False)

        stats = Statistics(intensities, dose.data())

        logger.debug(stats.completeness_vs_dose_str())
        logger.debug(stats.rcp_vs_dose_str())
        logger.debug(stats.scp_vs_dose_str())
        logger.debug(stats.rd_vs_dose_str())

        with open("chef.json", "wb") as f:
            json.dump(stats.to_dict(), f)

        self._chef_stats = stats
        return stats

    def cluster_analysis(self):
        from xia2.Modules.MultiCrystal import multi_crystal_analysis

        labels = self._data_manager.experiments.identifiers()
        intensities = [i[0] for i in self._intensities_separate]
        mca = multi_crystal_analysis(intensities, labels=labels, prefix=None)

        self._cc_cluster_json = mca.to_plotly_json(
            mca.cc_matrix, mca.cc_linkage_matrix, labels=labels
        )
        self._cc_cluster_table = mca.as_table(mca.cc_clusters)

        self._cos_angle_cluster_json = mca.to_plotly_json(
            mca.cos_angle_matrix, mca.cos_angle_linkage_matrix, labels=labels
        )
        self._cos_angle_cluster_table = mca.as_table(mca.cos_angle_clusters)

        return mca

    def unit_cell_analysis(self):
        from dials.command_line.unit_cell_histogram import uc_params_from_experiments

        # from dials.command_line.unit_cell_histogram import panel_distances_from_experiments

        experiments = self._data_manager.experiments
        uc_params = uc_params_from_experiments(experiments)
        # panel_distances = panel_distances_from_experiments(experiments)

        d = OrderedDict()
        from xia2.Modules.MultiCrystal.plots import plot_uc_histograms

        d.update(plot_uc_histograms(uc_params))
        # self._plot_uc_vs_detector_distance(uc_params, panel_distances, outliers, params.steps_per_angstrom)
        # self._plot_number_of_crystals(experiments)

        clustering, dendrogram = self.unit_cell_clustering(
            experiments,
            threshold=self.params.unit_cell_clustering.threshold,
            log=self.params.unit_cell_clustering.log,
        )
        from dials.algorithms.clustering.plots import scipy_dendrogram_to_plotly_json

        d["uc_clustering"] = scipy_dendrogram_to_plotly_json(
            dendrogram,
            title="Unit cell clustering",
            xtitle="Dataset",
            ytitle="Distance (Å^2)",
        )

        return d

    def report(self):
        super(multi_crystal_analysis, self).report()

        unit_cell_graphs = self.unit_cell_analysis()
        self.radiation_damage_analysis()
        self._cluster_analysis = self.cluster_analysis()

        overall_stats_table, merging_stats_table, stats_plots = (
            self.merging_stats_data()
        )

        json_data = {}
        json_data.update(self.intensity_stats_plots())
        json_data.update(self.batch_dependent_plots())
        json_data.update(stats_plots)
        json_data.update(self._chef_stats.to_dict())
        json_data.update(unit_cell_graphs)

        # return

        self._data_manager.export_experiments("tmp.expt")
        self._stereographic_projection_files = self.stereographic_projections(
            "tmp.expt"
        )

        styles = {}
        for hkl in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
            with open(self._stereographic_projection_files[hkl], "rb") as f:
                d = json.load(f)
                d["layout"]["title"] = "Stereographic projection (hkl=%i%i%i)" % hkl
                key = "stereographic_projection_%s%s%s" % hkl
                json_data[key] = d
                styles[key] = "square-plot"

        resolution_graphs = OrderedDict(
            (k, json_data[k])
            for k in (
                "cc_one_half",
                "i_over_sig_i",
                "second_moments",
                "wilson_intensity_plot",
                "completeness",
                "multiplicity_vs_resolution",
            )
            if k in json_data
        )

        batch_graphs = OrderedDict(
            (k, json_data[k])
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
            (k, json_data[k])
            for k in ("cumulative_intensity_distribution", "l_test", "multiplicities")
            if k in json_data
        )

        for k, v in self.multiplicity_plots().iteritems():
            misc_graphs[k] = {"img": v}

        for k in (
            "stereographic_projection_100",
            "stereographic_projection_010",
            "stereographic_projection_001",
        ):
            misc_graphs[k] = json_data[k]

        for axis in ("h", "k", "l"):
            styles["multiplicity_%s" % axis] = "square-plot"

        from jinja2 import Environment, ChoiceLoader, PackageLoader

        loader = ChoiceLoader(
            [PackageLoader("xia2", "templates"), PackageLoader("dials", "templates")]
        )
        env = Environment(loader=loader)

        template = env.get_template("multi_crystal.html")
        html = template.render(
            page_title=self.params.title,
            # filename=os.path.abspath(unmerged_mtz),
            space_group=self.intensities.space_group_info().symbol_and_number(),
            unit_cell=str(self.intensities.unit_cell()),
            # mtz_history=[h.strip() for h in report.mtz_object.history()],
            overall_stats_table=overall_stats_table,
            merging_stats_table=merging_stats_table,
            cc_half_significance_level=self.params.cc_half_significance_level,
            resolution_graphs=resolution_graphs,
            batch_graphs=batch_graphs,
            misc_graphs=misc_graphs,
            unit_cell_graphs=unit_cell_graphs,
            cc_cluster_table=self._cc_cluster_table,
            cc_cluster_json=self._cc_cluster_json,
            cos_angle_cluster_table=self._cos_angle_cluster_table,
            cos_angle_cluster_json=self._cos_angle_cluster_json,
            styles=styles,
            xia2_version=Version,
        )

        with open("%s-report.json" % self.params.prefix, "wb") as f:
            json.dump(json_data, f)

        with open("%s-report.html" % self.params.prefix, "wb") as f:
            f.write(html.encode("ascii", "xmlcharrefreplace"))


if __name__ == "__main__":
    import sys

    run(sys.argv[1:])
