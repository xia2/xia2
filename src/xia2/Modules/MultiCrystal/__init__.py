from __future__ import annotations

import json
import logging

import numpy as np
from scipy.cluster import hierarchy

import iotbx.phil
from dials.algorithms.correlation.plots import linkage_matrix_to_dict, to_plotly_json
from dials.util import tabulate
from scitbx.array_family import flex

logger = logging.getLogger(__name__)

batch_phil_scope = """\
batch
  .multiple = True
{
  id = None
    .type = str
  range = None
    .type = ints(size=2, value_min=0)
}
"""

master_phil_scope = iotbx.phil.parse(
    """\
unit_cell = None
  .type = unit_cell
  .short_caption = "Unit cell"
n_bins = 20
  .type = int(value_min=1)
  .short_caption = "Number of bins"
d_min = None
  .type = float(value_min=0)
  .short_caption = "High resolution cutoff"
%s
"""
    % batch_phil_scope
)


class ClusterInfo:
    def __init__(
        self, cluster_id, labels, multiplicity, completeness, unit_cell, height=None
    ):
        self.cluster_id = cluster_id
        self.labels = labels
        self.multiplicity = multiplicity
        self.completeness = completeness
        self.unit_cell = unit_cell
        self.height = height

    def __str__(self):
        lines = [
            "Cluster %i" % self.cluster_id,
            "  Number of datasets: %i" % len(self.labels),
            "  Completeness: %.1f %%" % (self.completeness * 100),
            "  Multiplicity: %.2f" % self.multiplicity,
            "  Datasets:" + ",".join("%s" % s for s in self.labels),
        ]
        if self.height is not None:
            lines.append("  height: %f" % self.height)
        return "\n".join(lines)


class multi_crystal_analysis:
    def __init__(self, unmerged_intensities, labels=None, prefix=None):

        self.unmerged_intensities = unmerged_intensities
        self._intensities_all = None
        self._labels_all = flex.size_t()
        if prefix is None:
            prefix = ""
        self._prefix = prefix

        self.intensities = unmerged_intensities
        self.individual_merged_intensities = []
        if labels is None:
            labels = ["%i" % (i + 1) for i in range(len(self.intensities))]
        assert len(labels) == len(self.intensities)
        self.labels = labels

        for i, unmerged in enumerate(self.intensities):
            self.individual_merged_intensities.append(
                unmerged.merge_equivalents().array().set_info(unmerged.info())
            )
            if self._intensities_all is None:
                self._intensities_all = unmerged.deep_copy()
            else:
                self._intensities_all = self._intensities_all.concatenate(
                    unmerged, assert_is_similar_symmetry=False
                )
            self._labels_all.extend(flex.size_t(unmerged.size(), i))

        self.run_cosym()

        (
            correlation_matrix,
            linkage_matrix,
        ) = self.compute_correlation_coefficient_matrix()

        cos_angle_matrix, ca_linkage_matrix = self.compute_cos_angle_matrix()

        d = to_plotly_json(correlation_matrix, linkage_matrix, labels=labels)

        with open("%sintensity_clusters.json" % self._prefix, "w") as f:
            json.dump(d, f, indent=2)

        d = to_plotly_json(
            cos_angle_matrix, ca_linkage_matrix, labels=labels, matrix_type="cos_angle"
        )

        with open("%scos_angle_clusters.json" % self._prefix, "w") as f:
            json.dump(d, f, indent=2)

        self.cos_angle_linkage_matrix = ca_linkage_matrix
        self.cos_angle_matrix = cos_angle_matrix
        self.cos_angle_clusters = self.cluster_info(
            linkage_matrix_to_dict(self.cos_angle_linkage_matrix)
        )
        self.cc_linkage_matrix = linkage_matrix
        self.cc_matrix = correlation_matrix
        self.cc_clusters = self.cluster_info(
            linkage_matrix_to_dict(self.cc_linkage_matrix)
        )

        logger.info("\nIntensity correlation clustering summary:")
        logger.info(
            tabulate(
                self.as_table(self.cc_clusters), headers="firstrow", tablefmt="rst"
            )
        )
        logger.info("\nCos(angle) clustering summary:")
        logger.info(
            tabulate(
                self.as_table(self.cos_angle_clusters),
                headers="firstrow",
                tablefmt="rst",
            )
        )

    def cluster_info(self, cluster_dict):
        info = []
        for cluster_id, cluster in cluster_dict.items():
            sel_cluster = flex.bool(self._labels_all.size(), False)
            uc_params = [flex.double() for i in range(6)]
            for j in cluster["datasets"]:
                sel_cluster |= self._labels_all == j
                uc_j = self.intensities[j - 1].unit_cell().parameters()
                for i in range(6):
                    uc_params[i].append(uc_j[i])
            average_uc = [flex.mean(uc_params[i]) for i in range(6)]
            intensities_cluster = self._intensities_all.select(sel_cluster)
            merging = intensities_cluster.merge_equivalents()
            merged_intensities = merging.array()
            multiplicities = merging.redundancies()
            dataset_ids = cluster["datasets"]
            labels = [self.labels[i - 1] for i in dataset_ids]
            info.append(
                ClusterInfo(
                    cluster_id,
                    labels,
                    flex.mean(multiplicities.data().as_double()),
                    merged_intensities.completeness(),
                    unit_cell=average_uc,
                    height=cluster.get("height"),
                )
            )
        return info

    def as_table(self, cluster_info):
        from libtbx.str_utils import wordwrap

        headers = [
            "Cluster",
            "No. datasets",
            "Datasets",
            "Height",
            "Multiplicity",
            "Completeness",
        ]
        rows = []
        for info in cluster_info:
            rows.append(
                [
                    "%i" % info.cluster_id,
                    "%i" % len(info.labels),
                    wordwrap(" ".join("%s" % l for l in info.labels)),
                    "%.2g" % info.height,
                    "%.1f" % info.multiplicity,
                    "%.2f" % info.completeness,
                ]
            )

        rows.insert(0, headers)
        return rows

    def run_cosym(self):
        from dials.algorithms.symmetry.cosym import phil_scope

        params = phil_scope.extract()
        from dials.algorithms.symmetry.cosym import CosymAnalysis

        datasets = [
            d.eliminate_sys_absent(integral_only=True).primitive_setting()
            for d in self.individual_merged_intensities
        ]
        params.lattice_group = self.individual_merged_intensities[0].space_group_info()
        params.space_group = self.individual_merged_intensities[0].space_group_info()

        self.cosym = CosymAnalysis(datasets, params)
        self.cosym.run()

    def compute_correlation_coefficient_matrix(self):
        import scipy.spatial.distance as ssd

        correlation_matrix = self.cosym.target.rij_matrix

        for i in range(correlation_matrix.shape[0]):
            correlation_matrix[i, i] = 1

        # clip values of correlation matrix to account for floating point errors
        correlation_matrix[np.where(correlation_matrix < -1)] = -1
        correlation_matrix[np.where(correlation_matrix > 1)] = 1
        diffraction_dissimilarity = 1 - correlation_matrix

        assert ssd.is_valid_dm(diffraction_dissimilarity, tol=1e-12)
        # convert the redundant n*n square matrix form into a condensed nC2 array
        dist_mat = ssd.squareform(diffraction_dissimilarity, checks=False)

        linkage_matrix = hierarchy.linkage(dist_mat, method="average")

        return correlation_matrix, linkage_matrix

    def compute_cos_angle_matrix(self):
        import scipy.spatial.distance as ssd

        dist_mat = ssd.pdist(self.cosym.coords, metric="cosine")
        cos_angle = 1 - ssd.squareform(dist_mat)
        return cos_angle, hierarchy.linkage(dist_mat, method="average")
