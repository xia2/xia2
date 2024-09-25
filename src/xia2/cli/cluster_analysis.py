from __future__ import annotations

import copy
import logging
import os
import random
import sys

import iotbx.phil
import numpy as np
from dials.algorithms.correlation.analysis import CorrelationMatrix
from dials.array_family import flex
from dials.util import tabulate
from dials.util.multi_dataset_handling import (
    assign_unique_identifiers,
    parse_multiple_datasets,
)
from dials.util.options import ArgumentParser, reflections_and_experiments_from_files
from dials.util.version import dials_version
from jinja2 import ChoiceLoader, Environment, PackageLoader

import xia2.Handlers.Streams
from xia2.Modules.Analysis import batch_phil_scope
from xia2.Modules.MultiCrystalAnalysis import MultiCrystalAnalysis
from xia2.XIA2Version import Version

logger = logging.getLogger("xia2.cluster_analysis")

cluster_phil_scope = """\
clustering
  .short_caption = "Clustering"
{
  output_clusters = False
    .type = bool
    .help = "Set this to true to enable scaling and merging of individual clusters"
    .short_caption = "Output individual clusters"
  method = *cos_angle correlation
    .type = choice(multi=True)
    .short_caption = "Metric on which to perform clustering"
  min_completeness = 0
    .type = float(value_min=0, value_max=1)
    .short_caption = "Minimum completeness"
  min_multiplicity = 0
    .type = float(value_min=0)
    .short_caption = "Minimum multiplicity"
  max_output_clusters = 10
    .type = int(value_min=1)
    .short_caption = "Maximum number of clusters to be output"
  min_cluster_size = 5
    .type = int
    .short_caption = "Minimum number of datasets for a cluster"
  max_cluster_height = 100
    .type = float
    .short_caption = "Maximum height in dendrogram for clusters"
  max_cluster_height_cc = 100
    .type = float
    .short_caption = "Maximum height in correlation dendrogram for clusters"
  max_cluster_height_cos = 100
    .type = float
    .short_caption = "Maximum height in cos angle dendrogram for clusters"
  find_distinct_clusters = False
    .type = bool
    .help = "This will determine whether optional cluster analysis is undertaken."
            "To assist in decreasing computation time, only clusters that have"
            "no datasets in common but eventually combine to form a joined cluster"
            "in the output dendrogram will be scaled and merged."
            "These may contain interesting differences worth comparing in"
            "downstream analysis."
    .short_caption = "Find distinct clusters"
}
"""

mca_phil = iotbx.phil.parse(
    """\
seed = 42
  .type = int(value_min=0)
  .help = "Seed value for random number generators used"

unit_cell_clustering {
  threshold = 5000
    .type = float(value_min=0)
    .help = 'Threshold value for the clustering'
  log = False
    .type = bool
    .help = 'Display the dendrogram with a log scale'
}
clustering {
  output_correlation_cluster_number = 0
    .type = int
    .short_caption = "Option to output a specific correlation cluster when re-running the code"
  output_cos_cluster_number = 0
    .type = int
    .short_caption = "Option to output a specific cos cluster when re-running the code"
  exclude_correlation_cluster_number = 0
    .type = int
    .short_caption = "Option to output all data excluding a specific correlation cluster"
  exclude_cos_cluster_number = 0
    .type = int
    .short_caption = "option to output all data excluding a specific cos cluster"
}

include scope dials.algorithms.correlation.analysis.phil_scope

output {
  log = xia2.cluster_analysis.log
    .type = str
  json = xia2.cluster_analysis.json
    .type = str
}
%s
%s
"""
    % (batch_phil_scope, cluster_phil_scope),
    process_includes=True,
)


def run(args=sys.argv[1:]):
    # Create the parser

    usage = "xia2.cluster_analysis [options] [param.phil] scaled.expt scaled.refl"

    help_message = """
    Will run the intensity and cos angle clustering methods on a multi-crystal dataset.
    """
    parser = ArgumentParser(
        usage=usage,
        phil=mca_phil,
        read_reflections=True,
        read_experiments=True,
        check_format=False,
        epilog=help_message,
    )

    # Parse the command line
    params, options = parser.parse_args(args=args, show_diff_phil=False)

    xia2.Handlers.Streams.setup_logging(
        logfile=params.output.log, verbose=options.verbose
    )

    logger.info(dials_version())

    # Log the diff phil
    diff_phil = parser.diff_phil.as_str()
    if diff_phil != "":
        logger.info("The following parameters have been modified:\n")
        logger.info(diff_phil)

    if len(params.input.experiments) == 0:
        logger.info("No Experiments found in the input")
        parser.print_help()
        return
    if len(params.input.reflections) == 0:
        logger.info("No reflection data found in the input")
        parser.print_help()
        return

    if params.seed is not None:
        flex.set_random_seed(params.seed)
        np.random.seed(params.seed)
        random.seed(params.seed)

    reflections, experiments = reflections_and_experiments_from_files(
        params.input.reflections, params.input.experiments
    )

    reflections = parse_multiple_datasets(reflections)
    if len(experiments) != len(reflections):
        sys.exit(
            "Mismatched number of experiments and reflection tables found: %s & %s."
            % (len(experiments), len(reflections))
        )
    if len(experiments) < 2:
        sys.exit(
            "At least 2 datasets are needed for cluster analysis. Please re-run with more datasets."
        )
    experiments, reflections = assign_unique_identifiers(experiments, reflections)

    try:
        MCA = CorrelationMatrix(experiments, reflections, params)

    except ValueError as e:
        sys.exit(str(e))

    else:
        MCA.calculate_matrices()
        MCA.convert_to_html_json()

        logger.info("\nIntensity correlation clustering summary:")
        logger.info(tabulate(MCA.cc_table, headers="firstrow", tablefmt="rst"))
        logger.info("\nCos(angle) clustering summary:")
        logger.info(tabulate(MCA.cos_table, headers="firstrow", tablefmt="rst"))

        min_completeness = params.clustering.min_completeness
        min_multiplicity = params.clustering.min_multiplicity
        max_clusters = params.clustering.max_output_clusters
        min_cluster_size = params.clustering.min_cluster_size
        max_cluster_height_cos = params.clustering.max_cluster_height_cos
        max_cluster_height_cc = params.clustering.max_cluster_height_cc
        max_cluster_height = params.clustering.max_cluster_height

        if not os.path.exists("cc_clusters"):
            os.mkdir("cc_clusters")
        if not os.path.exists("cos_angle_clusters"):
            os.mkdir("cos_angle_clusters")

        if (
            "cos_angle" in params.clustering.method
            and "correlation" not in params.clustering.method
        ):
            clusters = MCA.cos_angle_clusters
            ctype = ["cos" for i in clusters]
        elif (
            "correlation" in params.clustering.method
            and "cos_angle" not in params.clustering.method
        ):
            clusters = MCA.correlation_clusters
            ctype = ["cc" for i in clusters]
        elif (
            "cos_angle" in params.clustering.method
            and "correlation" in params.clustering.method
        ):
            clusters = MCA.cos_angle_clusters + MCA.correlation_clusters
            ctype = ["cos" for i in MCA.cos_angle_clusters] + [
                "cc" for i in MCA.correlation_clusters
            ]

        clusters.reverse()
        ctype.reverse()
        cos_clusters = []
        cc_clusters = []
        cos_cluster_ids = {}
        cc_cluster_ids = {}

        if params.clustering.output_clusters:
            n_processed_cos = 0
            n_processed_cc = 0

            for c, cluster in zip(ctype, clusters):
                # This simplifies max_cluster_height into cc and cos angle versions
                # But still gives the user the option of just selecting max_cluster_height
                # Which makes more sense when they only want one type of clustering

                if (
                    c == "cc"
                    and max_cluster_height != 100
                    and max_cluster_height_cc == 100
                ):
                    max_cluster_height_cc = max_cluster_height
                    # if user has weirdly set both max_cluster_height and max_cluster_height_cc
                    # will still default to max_cluster_height_cc as intended
                if (
                    c == "cos"
                    and max_cluster_height != 100
                    and max_cluster_height_cos == 100
                ):
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
                    len(cluster.labels) == len(experiments)
                    and not params.clustering.find_distinct_clusters
                ):
                    continue
                if cluster.height > max_cluster_height_cc and c == "cc":
                    continue
                if cluster.height > max_cluster_height_cos and c == "cos":
                    continue
                if len(cluster.labels) < min_cluster_size:
                    continue

                cluster_identifiers = [
                    MCA.ids_to_identifiers_map[l] for l in cluster.labels
                ]

                if params.clustering.find_distinct_clusters:
                    if c == "cos":
                        cos_clusters.append(cluster)
                        cos_cluster_ids[cluster.cluster_id] = cluster_identifiers
                    elif c == "cc":
                        cc_clusters.append(cluster)
                        cc_cluster_ids[cluster.cluster_id] = cluster_identifiers

                else:
                    if c == "cos":
                        n_processed_cos += 1
                        cluster_dir = (
                            "cos_angle_clusters/cluster_%i" % cluster.cluster_id
                        )
                        if (
                            params.clustering.output_cos_cluster_number == 0
                            or params.clustering.output_cos_cluster_number
                            == cluster.cluster_id
                        ):
                            logger.info(
                                "Outputting cos cluster %i:" % cluster.cluster_id
                            )
                            logger.info(cluster)
                            output_cluster(
                                cluster_dir,
                                experiments,
                                reflections,
                                cluster_identifiers,
                                cluster,
                            )
                    elif c == "cc":
                        n_processed_cc += 1
                        cluster_dir = "cc_clusters/cluster_%i" % cluster.cluster_id
                        if (
                            params.clustering.output_correlation_cluster_number == 0
                            or params.clustering.output_correlation_cluster_number
                            == cluster.cluster_id
                        ):
                            logger.info(
                                "Outputting cc cluster %i:" % cluster.cluster_id
                            )
                            logger.info(cluster)
                            output_cluster(
                                cluster_dir,
                                experiments,
                                reflections,
                                cluster_identifiers,
                                cluster,
                            )

            for c, cluster in zip(ctype, clusters):
                # Specific Clusters to output

                if (
                    params.clustering.output_correlation_cluster_number
                    == cluster.cluster_id
                    and c == "cc"
                ):
                    logger.info("Outputting cluster number %i:" % cluster.cluster_id)
                    new_folder = "cc_clusters/cluster_%i" % cluster.cluster_id
                    identifiers = [
                        MCA.ids_to_identifiers_map[l] for l in cluster.labels
                    ]
                    output_cluster(
                        new_folder,
                        experiments,
                        reflections,
                        identifiers,
                        cluster,
                    )
                if (
                    params.clustering.output_cos_cluster_number == cluster.cluster_id
                    and c == "cos"
                ):
                    logger.info("Outputting cluster number %i:" % cluster.cluster_id)
                    new_folder = "cos_angle_clusters/cluster_%i" % cluster.cluster_id
                    identifiers = [
                        MCA.ids_to_identifiers_map[l] for l in cluster.labels
                    ]
                    output_cluster(
                        new_folder,
                        experiments,
                        reflections,
                        identifiers,
                        cluster,
                    )

                # Excluded Clusters

                if (
                    params.clustering.exclude_correlation_cluster_number
                    == cluster.cluster_id
                    and c == "cc"
                ):
                    logger.info(
                        "Outputting data excluding cc cluster %i:" % cluster.cluster_id
                    )
                    new_folder = "cc_clusters/excluded_cluster_" + str(
                        cluster.cluster_id
                    )
                    overall_cluster = MCA.correlation_clusters[-1]
                    identifiers_overall_cluster = [
                        MCA.ids_to_identifiers_map[l] for l in overall_cluster.labels
                    ]
                    identifiers_to_exclude = [
                        MCA.ids_to_identifiers_map[l] for l in cluster.labels
                    ]
                    identifiers_to_output = [
                        i
                        for i in identifiers_overall_cluster
                        if i not in identifiers_to_exclude
                    ]
                    output_cluster(
                        new_folder,
                        experiments,
                        reflections,
                        identifiers_to_output,
                        cluster,
                    )

                if (
                    params.clustering.exclude_cos_cluster_number == cluster.cluster_id
                    and c == "cos"
                ):
                    logger.info(
                        "Outputting data excluding cos angle cluster %i:"
                        % cluster.cluster_id
                    )
                    new_folder = "cos_angle_clusters/excluded_cluster_" + str(
                        cluster.cluster_id
                    )
                    overall_cluster = MCA._cluster_analysis.cos_angle_clusters[-1]
                    identifiers_overall_cluster = [
                        MCA.ids_to_identifiers_map[l] for l in overall_cluster.labels
                    ]
                    identifiers_to_exclude = [
                        MCA.ids_to_identifiers_map[l] for l in cluster.labels
                    ]
                    identifiers_to_output = [
                        i
                        for i in identifiers_overall_cluster
                        if i not in identifiers_to_exclude
                    ]
                    output_cluster(
                        new_folder,
                        experiments,
                        reflections,
                        identifiers_to_output,
                        cluster,
                    )

        if params.clustering.find_distinct_clusters:
            for k, clusters in enumerate([cos_clusters, cc_clusters]):
                if k == 0:
                    cty = "cos"
                elif k == 1:
                    cty = "cc"
                logger.info("----------------------")
                logger.info(f"{cty} cluster analysis")
                logger.info("----------------------")

                (
                    file_data,
                    list_of_clusters,
                ) = MultiCrystalAnalysis.interesting_cluster_identification(
                    clusters, params
                )

                if len(list_of_clusters) > 0:
                    for item in list_of_clusters:
                        if k == 0:
                            cluster_dir = "cos_angle_clusters/" + item
                        elif k == 1:
                            cluster_dir = "cc_clusters/" + item
                        logger.info("Outputting: %s" % cluster_dir)

                        for cluster in clusters:
                            if "cluster_" + str(cluster.cluster_id) == item:
                                if k == 0:
                                    ids = cos_cluster_ids[cluster.cluster_id]
                                elif k == 1:
                                    ids = cc_cluster_ids[cluster.cluster_id]

                                output_cluster(
                                    cluster_dir,
                                    experiments,
                                    reflections,
                                    ids,
                                    cluster,
                                )

        if params.clustering.find_distinct_clusters:
            logger.info(f"Clusters recommended for comparison in {params.output.log}")
        if params.clustering.output_clusters:
            logger.info("----------------")
            logger.info("Output given as DIALS .expt/.refl files:")
            logger.info("To merge rotation data: use dials.merge")
            logger.info(
                "To merge still data: use xia2.ssx_reduce with the option steps=merge"
            )
            logger.info("----------------")

        loader = ChoiceLoader(
            [PackageLoader("xia2", "templates"), PackageLoader("dials", "templates")]
        )
        env = Environment(loader=loader)

        template = env.get_template("clusters.html")
        html = template.render(
            page_title="xia2 cluster analysis",
            cc_cluster_table=MCA.cc_table,
            cc_cluster_json=MCA.cc_json,
            cos_angle_cluster_table=MCA.cos_table,
            cos_angle_cluster_json=MCA.cos_json,
            image_range_tables=[MCA.table_list],
            cosym_graphs=MCA.rij_graphs,
            xia2_version=Version,
        )

        with open("xia2.cluster_analysis.html", "wb") as f:
            f.write(html.encode("utf-8", "xmlcharrefreplace"))

        MCA.output_json()


def output_cluster(new_folder, experiments, reflections, ids, cluster):
    expts = copy.deepcopy(experiments)
    expts.select_on_experiment_identifiers(ids)

    refl = []
    for idx, i in enumerate(reflections):
        if idx in cluster.labels:
            refl.append(i)

    joint_refl = flex.reflection_table.concat(refl)

    if not os.path.exists(new_folder):
        os.mkdir(new_folder)

    expts.as_file(new_folder + "/cluster_" + str(cluster.cluster_id) + ".expt")
    joint_refl.as_file(new_folder + "/cluster_" + str(cluster.cluster_id) + ".refl")
