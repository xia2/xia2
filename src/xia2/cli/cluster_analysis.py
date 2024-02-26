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

mca_phil = iotbx.phil.parse(
    """
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

clustering
  .short_caption = "Clustering"
{
  max_output_clusters = 10
    .type = int(value_min=1)
    .short_caption = "Maximum number of clusters to be output"
  min_cluster_size = 5
    .type = int
    .short_caption = "Minimum number of datasets for a cluster"
  analysis = False
    .type = bool
    .help = "This will determine whether optional cluster analysis is undertaken."
            "To assist in decreasing computation time, only clusters that appear"
            "scientifically interesting to compare will be scaled and merged."
            "Pairs of clusters that are interesting to compare are currently"
            "defined as two clusters with no datasets in common that eventually"
            "join on the output dendrogram."
    .short_caption = "Cluster Analysis"
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

output {
  log = xia2.cluster_analysis.log
    .type = str
  json = xia2.cluster_analysis.json
    .type = str
}
%s
"""
    % batch_phil_scope,
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

        if params.clustering.analysis:
            logger.info("Correlation Clusters:")
            (
                cc_file_data,
                cc_list,
            ) = MultiCrystalAnalysis.interesting_cluster_identification(
                MCA.correlation_clusters, params
            )
            logger.info("===================================================")
            logger.info("Cos Angle Clusters:")
            (
                cos_file_data,
                cos_list,
            ) = MultiCrystalAnalysis.interesting_cluster_identification(
                MCA.cos_angle_clusters, params
            )

            if not os.path.exists("cc_clusters"):
                os.mkdir("cc_clusters")
            if not os.path.exists("cos_angle_clusters"):
                os.mkdir("cos_angle_clusters")

            for cluster in MCA.correlation_clusters:
                if (
                    "cluster_" + str(cluster.cluster_id) in cc_list
                    or cluster.cluster_id
                    == params.clustering.output_correlation_cluster_number
                ):
                    new_folder = "cc_clusters/" + "cluster_" + str(cluster.cluster_id)
                    cluster_identifiers = [
                        MCA.ids_to_identifiers_map[l] for l in cluster.labels
                    ]
                    output_cluster(
                        new_folder,
                        experiments,
                        reflections,
                        cluster_identifiers,
                        cluster,
                    )

                if (
                    params.clustering.exclude_correlation_cluster_number
                    == cluster.cluster_id
                ):
                    new_folder = (
                        "cc_clusters/" + "excluded_cluster_" + str(cluster.cluster_id)
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

            for cluster in MCA.cos_angle_clusters:
                if (
                    "cluster_" + str(cluster.cluster_id) in cos_list
                    or cluster.cluster_id == params.clustering.output_cos_cluster_number
                ):
                    new_folder = (
                        "cos_angle_clusters/" + "cluster_" + str(cluster.cluster_id)
                    )
                    cluster_identifiers = [
                        MCA.ids_to_identifiers_map[l] for l in cluster.labels
                    ]
                    output_cluster(
                        new_folder,
                        experiments,
                        reflections,
                        cluster_identifiers,
                        cluster,
                    )

                if params.clustering.exclude_cos_cluster_number == cluster.cluster_id:
                    new_folder = (
                        "cos_angle_clusters/"
                        + "excluded_cluster_"
                        + str(cluster.cluster_id)
                    )
                    overall_cluster = MCA.cos_angle_clusters[-1]
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
            logger.info(f"Clusters recommended for comparison in {params.output.log}")
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
