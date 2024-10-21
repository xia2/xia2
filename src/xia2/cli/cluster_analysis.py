from __future__ import annotations

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
from dxtbx.model import ExperimentList
from jinja2 import ChoiceLoader, Environment, PackageLoader

import xia2.Handlers.Streams
from xia2.Modules.MultiCrystal.cluster_analysis import (
    cluster_phil_scope,
    output_cluster,
    output_hierarchical_clusters,
)
from xia2.XIA2Version import Version

logger = logging.getLogger("xia2.cluster_analysis")

xia2_cluster_phil_scope = """\
clustering
  .short_caption = "Clustering"
{
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
}
"""

mca_phil = iotbx.phil.parse(
    """

include scope dials.algorithms.correlation.analysis.working_phil

%s
%s

output {
  log = xia2.cluster_analysis.log
    .type = str
  json = xia2.cluster_analysis.json
    .type = str
}
"""
    % (cluster_phil_scope, xia2_cluster_phil_scope),
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

        cwd = pathlib.Path.cwd()
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
        if params.clustering.output_clusters:
            if "hierarchical" in params.clustering.method:
                output_hierarchical_clusters(params, MCA, experiments, reflections)
            if "coordinate" in params.clustering.method:
                clusters = MCA.significant_clusters
                count = 0
                for c in clusters:
                    if c.completeness < params.clustering.min_completeness:
                        continue
                    if c.multiplicity < params.clustering.min_multiplicity:
                        continue
                    if len(c.labels) < params.clustering.min_cluster_size:
                        continue
                    if count >= params.clustering.max_output_clusters:
                        continue
                    # for the first cluster, make the directory if not exists
                    if not count and not pathlib.Path.exists(
                        cwd / "coordinate_clusters"
                    ):
                        pathlib.Path.mkdir(cwd / "coordinate_clusters")
                    cluster_dir = f"coordinate_clusters/cluster_{c.cluster_id}"
                    logger.info(f"Outputting: {cluster_dir}")
                    if not pathlib.Path.exists(cwd / cluster_dir):
                        pathlib.Path.mkdir(cwd / cluster_dir)
                    expts = ExperimentList()
                    tables = []
                    for idx in c.labels:
                        expts.append(MCA._experiments[idx])
                        tables.append(MCA._reflections[idx])
                    joint_refl = flex.reflection_table.concat(tables)
                    expts.as_file(cwd / cluster_dir / "cluster.expt")
                    joint_refl.as_file(cwd / cluster_dir / "cluster.refl")
                    count += 1

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
