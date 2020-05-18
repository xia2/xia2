import copy
import json
import logging
from collections import OrderedDict

import iotbx.phil
from scipy.cluster import hierarchy
from scitbx.array_family import flex

from dials.util import tabulate

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
n_bins = 20
  .type = int(value_min=1)
d_min = None
  .type = float(value_min=0)
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

        d = self.to_plotly_json(correlation_matrix, linkage_matrix, labels=labels)

        with open("%sintensity_clusters.json" % self._prefix, "w") as f:
            json.dump(d, f, indent=2)

        d = self.to_plotly_json(
            cos_angle_matrix, ca_linkage_matrix, labels=labels, matrix_type="cos_angle"
        )

        with open("%scos_angle_clusters.json" % self._prefix, "w") as f:
            json.dump(d, f, indent=2)

        self.cos_angle_linkage_matrix = ca_linkage_matrix
        self.cos_angle_matrix = cos_angle_matrix
        self.cos_angle_clusters = self.cluster_info(
            self.linkage_matrix_to_dict(self.cos_angle_linkage_matrix)
        )
        self.cc_linkage_matrix = linkage_matrix
        self.cc_matrix = correlation_matrix
        self.cc_clusters = self.cluster_info(
            self.linkage_matrix_to_dict(self.cc_linkage_matrix)
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

    @staticmethod
    def linkage_matrix_to_dict(linkage_matrix):
        tree = hierarchy.to_tree(linkage_matrix, rd=False)

        d = {}

        # http://w3facility.org/question/scipy-dendrogram-to-json-for-d3-js-tree-visualisation/
        # https://gist.github.com/mdml/7537455

        def add_node(node):
            if node.is_leaf():
                return
            cluster_id = node.get_id() - len(linkage_matrix) - 1
            row = linkage_matrix[cluster_id]
            d[cluster_id + 1] = {
                "datasets": [i + 1 for i in sorted(node.pre_order())],
                "height": row[2],
            }

            # Recursively add the current node's children
            if node.left:
                add_node(node.left)
            if node.right:
                add_node(node.right)

        add_node(tree)

        return OrderedDict(sorted(d.items()))

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
        params.cluster.method = "dbscan"

        self.cosym = CosymAnalysis(datasets, params)
        self.cosym.run()

    def compute_correlation_coefficient_matrix(self):
        import scipy.spatial.distance as ssd

        correlation_matrix = self.cosym.target.rij_matrix

        for i in range(correlation_matrix.all()[0]):
            correlation_matrix[i, i] = 1

        # clip values of correlation matrix to account for floating point errors
        correlation_matrix.set_selected(correlation_matrix < -1, -1)
        correlation_matrix.set_selected(correlation_matrix > 1, 1)
        diffraction_dissimilarity = 1 - correlation_matrix

        dist_mat = diffraction_dissimilarity.as_numpy_array()

        assert ssd.is_valid_dm(dist_mat, tol=1e-12)
        # convert the redundant n*n square matrix form into a condensed nC2 array
        dist_mat = ssd.squareform(dist_mat, checks=False)

        linkage_matrix = hierarchy.linkage(dist_mat, method="average")

        return correlation_matrix, linkage_matrix

    def compute_cos_angle_matrix(self):
        import scipy.spatial.distance as ssd

        dist_mat = ssd.pdist(self.cosym.coords.as_numpy_array(), metric="cosine")
        cos_angle = 1 - ssd.squareform(dist_mat)
        linkage_matrix = hierarchy.linkage(dist_mat, method="average")
        return flex.double(cos_angle), linkage_matrix

    @staticmethod
    def to_plotly_json(
        correlation_matrix, linkage_matrix, labels=None, matrix_type="correlation"
    ):
        assert matrix_type in ("correlation", "cos_angle")

        ddict = hierarchy.dendrogram(
            linkage_matrix, color_threshold=0.05, labels=labels, show_leaf_counts=False
        )

        y2_dict = scipy_dendrogram_to_plotly_json(ddict)  # above heatmap
        x2_dict = copy.deepcopy(y2_dict)  # left of heatmap, rotated
        for d in y2_dict["data"]:
            d["yaxis"] = "y2"
            d["xaxis"] = "x2"

        for d in x2_dict["data"]:
            x = d["x"]
            y = d["y"]
            d["x"] = y
            d["y"] = x
            d["yaxis"] = "y3"
            d["xaxis"] = "x3"

        D = correlation_matrix.as_numpy_array()
        index = ddict["leaves"]
        D = D[index, :]
        D = D[:, index]
        ccdict = {
            "data": [
                {
                    "name": "%s_matrix" % matrix_type,
                    "x": list(range(D.shape[0])),
                    "y": list(range(D.shape[1])),
                    "z": D.tolist(),
                    "type": "heatmap",
                    "colorbar": {
                        "title": (
                            "Correlation coefficient"
                            if matrix_type == "correlation"
                            else "cos(angle)"
                        ),
                        "titleside": "right",
                        "xpad": 0,
                    },
                    "colorscale": "YIOrRd",
                    "xaxis": "x",
                    "yaxis": "y",
                }
            ],
            "layout": {
                "autosize": False,
                "bargap": 0,
                "height": 1000,
                "hovermode": "closest",
                "margin": {"r": 20, "t": 50, "autoexpand": True, "l": 20},
                "showlegend": False,
                "title": "Dendrogram Heatmap",
                "width": 1000,
                "xaxis": {
                    "domain": [0.2, 0.9],
                    "mirror": "allticks",
                    "showgrid": False,
                    "showline": False,
                    "showticklabels": True,
                    "tickmode": "array",
                    "ticks": "",
                    "ticktext": y2_dict["layout"]["xaxis"]["ticktext"],
                    "tickvals": list(
                        range(len(y2_dict["layout"]["xaxis"]["ticktext"]))
                    ),
                    "tickangle": 300,
                    "title": "",
                    "type": "linear",
                    "zeroline": False,
                },
                "yaxis": {
                    "domain": [0, 0.78],
                    "anchor": "x",
                    "mirror": "allticks",
                    "showgrid": False,
                    "showline": False,
                    "showticklabels": True,
                    "tickmode": "array",
                    "ticks": "",
                    "ticktext": y2_dict["layout"]["xaxis"]["ticktext"],
                    "tickvals": list(
                        range(len(y2_dict["layout"]["xaxis"]["ticktext"]))
                    ),
                    "title": "",
                    "type": "linear",
                    "zeroline": False,
                },
                "xaxis2": {
                    "domain": [0.2, 0.9],
                    "anchor": "y2",
                    "showgrid": False,
                    "showline": False,
                    "showticklabels": False,
                    "zeroline": False,
                },
                "yaxis2": {
                    "domain": [0.8, 1],
                    "anchor": "x2",
                    "showgrid": False,
                    "showline": False,
                    "zeroline": False,
                },
                "xaxis3": {
                    "domain": [0.0, 0.1],
                    "anchor": "y3",
                    "range": [max(max(d["x"]) for d in x2_dict["data"]), 0],
                    "showgrid": False,
                    "showline": False,
                    "tickangle": 300,
                    "zeroline": False,
                },
                "yaxis3": {
                    "domain": [0, 0.78],
                    "anchor": "x3",
                    "showgrid": False,
                    "showline": False,
                    "showticklabels": False,
                    "zeroline": False,
                },
            },
        }
        d = ccdict
        d["data"].extend(y2_dict["data"])
        d["data"].extend(x2_dict["data"])

        d["clusters"] = multi_crystal_analysis.linkage_matrix_to_dict(linkage_matrix)

        return d


def scipy_dendrogram_to_plotly_json(ddict):
    colors = {
        "b": "rgb(31, 119, 180)",
        "g": "rgb(44, 160, 44)",
        "o": "rgb(255, 127, 14)",
        "r": "rgb(214, 39, 40)",
    }

    dcoord = ddict["dcoord"]
    icoord = ddict["icoord"]
    color_list = ddict["color_list"]
    ivl = ddict["ivl"]

    data = []
    xticktext = []
    xtickvals = []

    for k, y in enumerate(dcoord):
        x = icoord[k]

        if y[0] == 0:
            xtickvals.append(x[0])
        if y[3] == 0:
            xtickvals.append(x[3])

        data.append(
            {
                "x": x,
                "y": y,
                "marker": {"color": colors.get(color_list[k])},
                "mode": "lines",
            }
        )

    xtickvals = sorted(xtickvals)
    xticktext = ivl
    d = {
        "data": data,
        "layout": {
            "barmode": "group",
            "legend": {"x": 100, "y": 0.5, "bordercolor": "transparent"},
            "margin": {"r": 10},
            "showlegend": False,
            "title": "dendrogram",
            "xaxis": {
                "showline": False,
                "showgrid": False,
                "showticklabels": True,
                "tickangle": 300,
                "title": "Individual datasets",
                "titlefont": {"color": "none"},
                "type": "linear",
                "ticktext": xticktext,
                "tickvals": xtickvals,
                "tickorientation": "vertical",
            },
            "yaxis": {
                "showline": False,
                "showgrid": False,
                "showticklabels": True,
                "tickangle": 0,
                "title": "Ward distance",
                "type": "linear",
            },
            "hovermode": "closest",
        },
    }
    return d
