# -*- coding: utf-8 -*-
#!/usr/bin/env xia2.python
from __future__ import absolute_import, division, print_function

import json
import logging
from collections import OrderedDict

from xia2.XIA2Version import Version
from xia2.Modules.MultiCrystal.ScaleAndMerge import DataManager
from xia2.Modules.Analysis import batch_phil_scope

from libtbx import phil


logger = logging.getLogger(__name__)


class MultiCrystalAnalysis(object):
    def __init__(self, params, experiments=None, reflections=None, data_manager=None):
        self.params = params
        self._cluster_analysis = None
        if data_manager is not None:
            self._data_manager = data_manager
        else:
            assert experiments is not None and reflections is not None
            self._data_manager = DataManager(experiments, reflections)

        self._intensities_separate = self._data_manager.reflections_as_miller_arrays()

        self.intensities, self.batches, self.scales = self._data_manager.reflections_as_miller_arrays(
            combined=True
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

    def radiation_damage_analysis(self):
        from dials.pychef import Statistics

        intensities_all, batches_all, _ = self._data_manager.reflections_as_miller_arrays(
            combined=False
        )

        intensities_combined = None
        dose_combined = None
        for i, (intensities, batches) in enumerate(zip(intensities_all, batches_all)):
            dose = batches.array(
                batches.data()
                - self._data_manager.experiments[i].scan.get_batch_offset()
            ).set_info(batches.info())
            if intensities_combined is None:
                intensities_combined = intensities
                dose_combined = dose
            else:
                intensities_combined = intensities_combined.concatenate(
                    intensities, assert_is_similar_symmetry=False
                )
                dose_combined = dose_combined.concatenate(
                    dose, assert_is_similar_symmetry=False
                )

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
        mca = multi_crystal_analysis(
            self._intensities_separate[0], labels=labels, prefix=None
        )

        self._cc_cluster_json = mca.to_plotly_json(
            mca.cc_matrix, mca.cc_linkage_matrix, labels=labels
        )
        self._cc_cluster_table = mca.as_table(mca.cc_clusters)

        self._cos_angle_cluster_json = mca.to_plotly_json(
            mca.cos_angle_matrix, mca.cos_angle_linkage_matrix, labels=labels
        )
        self._cos_angle_cluster_table = mca.as_table(mca.cos_angle_clusters)
        self._cluster_analysis = mca
        return self._cluster_analysis

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


class MultiCrystalReport(MultiCrystalAnalysis):
    def report(self, individual_dataset_reports, comparison_graphs):
        unit_cell_graphs = self.unit_cell_analysis()
        if self._cluster_analysis is None:
            self._cluster_analysis = self.cluster_analysis()

        self._data_manager.export_experiments("tmp_experiments.expt")

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
            cc_cluster_table=self._cc_cluster_table,
            cc_cluster_json=self._cc_cluster_json,
            cos_angle_cluster_table=self._cos_angle_cluster_table,
            cos_angle_cluster_json=self._cos_angle_cluster_json,
            individual_dataset_reports=individual_dataset_reports,
            comparison_graphs=comparison_graphs,
            styles={},
            xia2_version=Version,
        )

        # with open("%s.json" % self.params.prefix, "wb") as f:
        # json.dump(json_data, f)

        with open("%s.html" % self.params.prefix, "wb") as f:
            f.write(html.encode("ascii", "xmlcharrefreplace"))
