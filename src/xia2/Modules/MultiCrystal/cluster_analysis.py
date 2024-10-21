from __future__ import annotations

import copy
import logging
import pathlib

import iotbx.phil
from dials.algorithms.correlation.analysis import CorrelationMatrix
from dials.algorithms.correlation.cluster import ClusterInfo
from dials.array_family import flex
from dxtbx.model import ExperimentList

from xia2.Modules.MultiCrystalAnalysis import MultiCrystalAnalysis

logger = logging.getLogger("")


cluster_phil_scope = """\
clustering
  .short_caption = "Clustering"
{
  output_clusters = False
    .type = bool
    .help = "Set this to true to enable scaling and merging of individual clusters"
    .short_caption = "Output individual clusters"

  method = *hierarchical coordinate
    .type = choice(multi=True)
    .short_caption = "Clustering method to use - analyse the clusters generated from"
                     "the hierarchical dendrograms or the density based"
                     "clustering analysis of the cosym coordinates."
  min_cluster_size = 5
    .type = int
    .short_caption = "Minimum number of datasets for an output cluster"
  min_completeness = 0
    .type = float(value_min=0, value_max=1)
    .short_caption = "Minimum completeness"
  min_multiplicity = 0
    .type = float(value_min=0)
    .short_caption = "Minimum multiplicity"
  max_output_clusters = 10
    .type = int(value_min=1)
    .short_caption = "Maximum number of clusters to be output"
  hierarchical
  {
    method = *cos_angle correlation
      .type = choice(multi=True)
      .short_caption = "Metric on which to perform hierarchical clustering"
    max_cluster_height = 100
      .type = float
      .short_caption = "Maximum height in dendrogram for clusters"
    max_cluster_height_cc = 100
      .type = float
      .short_caption = "Maximum height in correlation dendrogram for clusters"
    max_cluster_height_cos = 100
      .type = float
      .short_caption = "Maximum height in cos angle dendrogram for clusters"
    distinct_clusters = False
      .type = bool
      .help = "This will determine whether optional cluster analysis is undertaken."
            "To assist in decreasing computation time, only clusters that have"
            "no datasets in common but eventually combine to form a joined cluster"
            "in the output dendrogram will be scaled and merged."
            "These may contain interesting differences worth comparing in"
            "downstream analysis."
      .short_caption = "Find distinct clusters"
  }
}
"""


def clusters_and_types(
    cos_angle_clusters: list[ClusterInfo],
    cc_clusters: list[ClusterInfo],
    methods: list[str],
) -> tuple[list[ClusterInfo], list[str]]:
    if "cos_angle" in methods and "correlation" not in methods:
        clusters = cos_angle_clusters
        ctype = ["cos"] * len(clusters)
    elif "correlation" in methods and "cos_angle" not in methods:
        clusters = cc_clusters
        ctype = ["cc"] * len(clusters)
    elif "cos_angle" in methods and "correlation" in methods:
        clusters = cos_angle_clusters + cc_clusters
        ctype = ["cos"] * len(cos_angle_clusters) + ["cc"] * len(cc_clusters)
    else:
        raise ValueError("Invalid cluster method: %s" % methods)

    clusters.reverse()
    ctype.reverse()
    return clusters, ctype


def get_subclusters(
    params: iotbx.phil.scope_extract,
    ids_to_identifiers_map: dict[int, str],
    cos_angle_clusters: list[ClusterInfo],
    cc_clusters: list[ClusterInfo],
) -> list[tuple[str, list[str], ClusterInfo]]:
    subclusters = []

    min_completeness = params.min_completeness
    min_multiplicity = params.min_multiplicity
    max_clusters = params.max_output_clusters
    min_cluster_size = params.min_cluster_size
    max_cluster_height_cos = params.hierarchical.max_cluster_height_cos
    max_cluster_height_cc = params.hierarchical.max_cluster_height_cc
    max_cluster_height = params.hierarchical.max_cluster_height

    clusters, ctype = clusters_and_types(
        cos_angle_clusters, cc_clusters, params.hierarchical.method
    )

    n_processed_cos = 0
    n_processed_cc = 0

    for c, cluster in zip(ctype, clusters):
        # This simplifies max_cluster_height into cc and cos angle versions
        # But still gives the user the option of just selecting max_cluster_height
        # Which makes more sense when they only want one type of clustering
        if c == "cc" and max_cluster_height != 100 and max_cluster_height_cc == 100:
            max_cluster_height_cc = max_cluster_height
            # if user has weirdly set both max_cluster_height and max_cluster_height_cc
            # will still default to max_cluster_height_cc as intended
        if c == "cos" and max_cluster_height != 100 and max_cluster_height_cos == 100:
            max_cluster_height_cos = max_cluster_height

        if n_processed_cos == max_clusters and c == "cos":
            continue
        if n_processed_cc == max_clusters and c == "cc":
            continue
        if cluster.completeness < min_completeness:
            continue
        if cluster.multiplicity < min_multiplicity:
            continue
        if (
            len(cluster.labels)
            == len(ids_to_identifiers_map)  # was len(data_manager_original.experiments)
            and not params.hierarchical.distinct_clusters
        ):
            continue
        if cluster.height > max_cluster_height_cc and c == "cc":
            continue
        if cluster.height > max_cluster_height_cos and c == "cos":
            continue
        if len(cluster.labels) < min_cluster_size:
            continue

        cluster_identifiers = [ids_to_identifiers_map[l] for l in cluster.labels]
        subclusters.append((c, cluster_identifiers, cluster))
        if (
            not params.hierarchical.distinct_clusters
        ):  # increment so that we only get up to N clusters
            if c == "cos":
                n_processed_cos += 1
            elif c == "cc":
                n_processed_cc += 1

    return subclusters


def output_cluster(
    new_folder: pathlib.Path,
    experiments: ExperimentList,
    reflections: list[flex.reflection_table],
    ids: list[str],
) -> None:
    if not new_folder.parent.exists():
        pathlib.Path.mkdir(new_folder.parent)
    expts = copy.deepcopy(experiments)
    expts.select_on_experiment_identifiers(ids)

    refl = []
    for table in reflections:
        if table.experiment_identifiers().values()[0] in ids:
            refl.append(table)

    joint_refl = flex.reflection_table.concat(refl)

    if not new_folder.exists():
        pathlib.Path.mkdir(new_folder)

    expts.as_file(new_folder / "cluster.expt")
    joint_refl.as_file(new_folder / "cluster.refl")


def output_hierarchical_clusters(
    params: iotbx.phil.scope_extract,
    MCA: CorrelationMatrix,
    experiments: ExperimentList,
    reflections: list[flex.reflection_table],
) -> None:
    cwd = pathlib.Path.cwd()

    # First get subclusters that meet the required thresholds
    # - min size, completeness, multiplciity, dendrogram height etc.
    # subclusters will be of length max_output_clusters if distinct_clusters=False
    subclusters = get_subclusters(
        params.clustering,
        MCA.ids_to_identifiers_map,
        MCA.cos_angle_clusters,
        MCA.correlation_clusters,
    )

    # if not doing distinct cluster analysis, can now output clusters
    if not params.clustering.hierarchical.distinct_clusters:
        for c, cluster_identifiers, cluster in subclusters:
            output_dir = cwd / f"{c}_clusters/cluster_{cluster.cluster_id}"
            logger.info(f"Outputting {c} cluster {cluster.cluster_id}:")
            logger.info(cluster)
            output_cluster(
                output_dir,
                experiments,
                reflections,
                cluster_identifiers,
            )

    # if doing distinct cluster analysis, do the analysis and output clusters
    if params.clustering.hierarchical.distinct_clusters:
        cos_clusters = []
        cc_clusters = []
        cos_cluster_ids = {}
        cc_cluster_ids = {}
        for c, cluster_identifiers, cluster in subclusters:
            if c == "cos":
                cos_clusters.append(cluster)
                cos_cluster_ids[cluster.cluster_id] = cluster_identifiers
            elif c == "cc":
                cc_clusters.append(cluster)
                cc_cluster_ids[cluster.cluster_id] = cluster_identifiers

        for k, clusters in enumerate([cos_clusters, cc_clusters]):
            cty = "cc" if k == 1 else "cos"  # cluster type as a string
            logger.info("-" * 22 + f"\n{cty} cluster analysis\n" + "-" * 22)

            _, list_of_clusters = (
                MultiCrystalAnalysis.interesting_cluster_identification(
                    clusters, params
                )
            )
            for item in list_of_clusters:
                cluster_dir = f"{cty}_clusters/{item}"
                logger.info(f"Outputting: {cluster_dir}")
                output_dir = cwd / cluster_dir

                for cluster in clusters:
                    if f"cluster_{cluster.cluster_id}" == item:
                        ids = (
                            cc_cluster_ids[cluster.cluster_id]
                            if k
                            else cos_cluster_ids[cluster.cluster_id]
                        )
                        output_cluster(
                            output_dir,
                            experiments,
                            reflections,
                            ids,
                        )
                        break

    if params.clustering.hierarchical.distinct_clusters:
        logger.info(f"Clusters recommended for comparison in {params.output.log}")
    if params.clustering.output_clusters:
        logger.info("----------------")
        logger.info("Output given as DIALS .expt/.refl files:")
        logger.info("To merge rotation data: use dials.merge")
        logger.info(
            "To merge still data: use xia2.ssx_reduce with the option steps=merge"
        )
        logger.info("----------------")
