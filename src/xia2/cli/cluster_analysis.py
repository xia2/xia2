from __future__ import annotations

import copy
import logging
import pathlib
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

  output_correlation_cluster_number = None
    .type = int
    .short_caption = "Option to output a specific correlation cluster when re-running the code"
  output_cos_cluster_number = None
    .type = int
    .short_caption = "Option to output a specific cos cluster when re-running the code"
  exclude_correlation_cluster_number = None
    .type = int
    .short_caption = "Option to output all data excluding a specific correlation cluster"
  exclude_cos_cluster_number = None
    .type = int
    .short_caption = "option to output all data excluding a specific cos cluster"

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

mca_phil = iotbx.phil.parse(
    """

include scope dials.algorithms.correlation.analysis.working_phil

run_cluster_identification = True
  .type = bool
  .short_caption = "If True, in addition to running clustering analysis, identify"
                   "clusters of interest for further analysis."

max_cluster_height_difference = 0.5
  .type = float
  .short_caption = "Maximum hight difference between clusters"

%s

output {
  log = xia2.cluster_analysis.log
    .type = str
  json = xia2.cluster_analysis.json
    .type = str
}
"""
    % cluster_phil_scope,
    process_includes=True,
)  # batch_phil_scope


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

        cwd = pathlib.Path.cwd()
        if not pathlib.Path.exists(cwd / "cos_clusters"):
            pathlib.Path.mkdir(cwd / "cos_clusters")
        if not pathlib.Path.exists(cwd / "cc_clusters"):
            pathlib.Path.mkdir(cwd / "cc_clusters")

        # First get any specific requested/excluded clusters

        # These are options that are only available to xia2.cluster_analysis
        if params.clustering.output_cos_cluster_number:
            for cluster in MCA.cos_angle_clusters:
                if params.clustering.output_cos_cluster_number == cluster.cluster_id:
                    logger.info(
                        f"Outputting cos angle cluster number {cluster.cluster_id}"
                    )
                    new_folder = cwd / "cos_clusters" / f"cluster_{cluster.cluster_id}"
                    identifiers = [
                        MCA.ids_to_identifiers_map[l] for l in cluster.labels
                    ]
                    output_cluster(
                        new_folder,
                        experiments,
                        reflections,
                        identifiers,
                    )
        if params.clustering.output_correlation_cluster_number:
            for cluster in MCA.correlation_clusters:
                if (
                    params.clustering.output_correlation_cluster_number
                    == cluster.cluster_id
                ):
                    logger.info(f"Outputting cc cluster number {cluster.cluster_id}")
                    new_folder = cwd / "cc_clusters" / f"cluster_{cluster.cluster_id}"
                    identifiers = [
                        MCA.ids_to_identifiers_map[l] for l in cluster.labels
                    ]
                    output_cluster(
                        new_folder,
                        experiments,
                        reflections,
                        identifiers,
                    )

        if params.clustering.exclude_correlation_cluster_number:
            for cluster in MCA.correlation_clusters:
                if (
                    params.clustering.exclude_correlation_cluster_number
                    == cluster.cluster_id
                ):
                    logger.info(
                        f"Outputting data excluding cc cluster {cluster.cluster_id}"
                    )
                    new_folder = (
                        cwd / "cc_clusters" / f"excluded_cluster_{cluster.cluster_id}"
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
                    )
        if params.clustering.exclude_cos_cluster_number:
            for cluster in MCA.cos_angle_clusters:
                if params.clustering.exclude_cos_cluster_number == cluster.cluster_id:
                    logger.info(
                        f"Outputting data excluding cos angle cluster {cluster.cluster_id}"
                    )
                    new_folder = (
                        cwd / "cos_clusters" / f"excluded_cluster_{cluster.cluster_id}"
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
                    )
        # End of include/exclude options that are only available to xia2.cluster_analysis

        # all under if params.clustering.output_clusters:?
        from xia2.Modules.MultiCrystal.ScaleAndMerge import get_subclusters

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
                cluster_dir = cwd / f"{c}_clusters/cluster_{cluster.cluster_id}"
                logger.info(f"Outputting {c} cluster {cluster.cluster_id}:")
                logger.info(cluster)
                output_cluster(
                    cluster_dir,
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
                logger.info("----------------------")
                logger.info(f"{cty} cluster analysis")
                logger.info("----------------------")

                (
                    file_data,
                    list_of_clusters,
                ) = MultiCrystalAnalysis.interesting_cluster_identification(
                    clusters, params
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


def output_cluster(new_folder, experiments, reflections, ids):
    expts = copy.deepcopy(experiments)
    expts.select_on_experiment_identifiers(ids)

    refl = []
    for table in reflections:
        if table.experiment_identifiers().values()[0] in ids:
            refl.append(table)

    joint_refl = flex.reflection_table.concat(refl)

    if not pathlib.Path.exists(new_folder):
        pathlib.Path.mkdir(new_folder)

    expts.as_file(new_folder / "cluster.expt")
    joint_refl.as_file(new_folder / "cluster.refl")
