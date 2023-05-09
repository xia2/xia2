from __future__ import annotations

import copy
import logging
import os
import random
import sys

import numpy as np
from jinja2 import ChoiceLoader, Environment, PackageLoader

import iotbx.phil
from dials.array_family import flex
from dials.util.multi_dataset_handling import (
    assign_unique_identifiers,
    parse_multiple_datasets,
)
from dials.util.options import ArgumentParser, flatten_experiments, flatten_reflections
from dials.util.version import dials_version

import xia2.Handlers.Streams
from xia2.Modules.Analysis import batch_phil_scope
from xia2.Modules.MultiCrystalAnalysis import MultiCrystalReport
from xia2.XIA2Version import Version

logger = logging.getLogger("xia2.cluster_analysis")

# phil_scope = iotbx.phil.parse(
#    """
# include scope xia2.Modules.MultiCrystal.ScaleAndMerge.phil_scope
#
# include scope dials.util.exclude_images.phil_scope
#
# seed = 42
#  .type = int(value_min=0)
#
# ssx_flag = False
#    .type = bool
#    .help = "Set this to true for analysing clusters of ssx_data"
#    .short_caption = "SSX flag"
#
# output {
#  log = xia2.cluster_analysis.log
#    .type = str
# }
# """,
#    process_includes=True,
# )

mca_phil = iotbx.phil.parse(
    """
title = 'xia2 report'
    .type = str
prefix = 'xia2'
    .type = str

seed = 42
  .type = int(value_min=0)

unit_cell_clustering {
  threshold = 5000
    .type = float(value_min=0)
    .help = 'Threshold value for the clustering'
  log = False
    .type = bool
    .help = 'Display the dendrogram with a log scale'
}

max_cluster_height_difference = 0.5
  .type = float
  .short_caption = "Maximum hight difference between clusters"
max_output_clusters = 10
  .type = int
  .short_caption = "Maximum number of important clusters to be output"
min_cluster_size = 5
  .type = int
  .short_caption = "Minimum number of datasets for an important cluster"

output {
  log = xia2.multi_crystal_analysis.log
    .type = str
}
%s
"""
    % batch_phil_scope
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

    # params_mca = mca_phil.extract()

    # params_mca.ssx_flag = params.ssx_flag

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
    try:
        assert len(params.input.reflections) == len(params.input.experiments)
    except AssertionError:
        raise sys.exit(
            "The number of input reflections files does not match the "
            "number of input experiments"
        )

    if params.seed is not None:
        flex.set_random_seed(params.seed)
        np.random.seed(params.seed)
        random.seed(params.seed)

    experiments = flatten_experiments(params.input.experiments)
    reflections = flatten_reflections(params.input.reflections)
    if len(experiments) < 2:
        sys.exit("xia2.cluster_analysis requires a minimum of two experiments")
    reflections = parse_multiple_datasets(reflections)
    experiments, reflections = assign_unique_identifiers(experiments, reflections)

    reflections_all = flex.reflection_table()
    assert len(reflections) == 1 or len(reflections) == len(experiments)
    for i, (expt, refl) in enumerate(zip(experiments, reflections)):
        reflections_all.extend(refl)
    reflections_all.assert_experiment_identifiers_are_consistent(experiments)

    try:
        MCA = MultiCrystalReport(params, experiments, reflections_all)

    except ValueError as e:
        sys.exit(str(e))
    else:

        MCA.cluster_analysis()

        logger.info("Correlation Clusters:")
        cc_file_data, cc_list = MCA.interesting_cluster_identification(
            MCA._cluster_analysis.cc_clusters, params
        )
        logger.info("===================================================")
        logger.info("Cos Angle Clusters:")
        cos_file_data, cos_list = MCA.interesting_cluster_identification(
            MCA._cluster_analysis.cos_angle_clusters, params
        )

        if not os.path.exists("cc_clusters"):
            os.mkdir("cc_clusters")
        if not os.path.exists("cos_angle_clusters"):
            os.mkdir("cos_angle_clusters")

        for cluster in MCA._cluster_analysis.cc_clusters:
            if "cluster_" + str(cluster.cluster_id) in cc_list:
                new_folder = "cc_clusters/" + "cluster_" + str(cluster.cluster_id)
                data_manager = copy.deepcopy(MCA._data_manager)
                if not os.path.exists(new_folder):
                    os.mkdir(new_folder)
                cluster_identifiers = [
                    MCA._data_manager.ids_to_identifiers_map[l] for l in cluster.labels
                ]
                data_manager.select(cluster_identifiers)

                MCA._data_manager.export_experiments(
                    new_folder + "/cluster_" + str(cluster.cluster_id) + ".expt"
                )
                MCA._data_manager.export_reflections(
                    new_folder + "/cluster_" + str(cluster.cluster_id) + ".refl"
                )

        for cluster in MCA._cluster_analysis.cos_angle_clusters:
            if "cluster_" + str(cluster.cluster_id) in cos_list:
                new_folder = (
                    "cos_angle_clusters/" + "cluster_" + str(cluster.cluster_id)
                )
                data_manager = copy.deepcopy(MCA._data_manager)
                if not os.path.exists(new_folder):
                    os.mkdir(new_folder)
                cluster_identifiers = [
                    MCA._data_manager.ids_to_identifiers_map[l] for l in cluster.labels
                ]
                data_manager.select(cluster_identifiers)

                MCA._data_manager.export_experiments(
                    new_folder + "/cluster_" + str(cluster.cluster_id) + ".expt"
                )
                MCA._data_manager.export_reflections(
                    new_folder + "/cluster_" + str(cluster.cluster_id) + ".refl"
                )

        id_list = []
        table_list = [["Experiment/Image Number", "Image Template"]]

        el = MCA._data_manager.experiments
        ids = list(el.identifiers())
        for item in el:
            id = MCA._data_manager.identifiers_to_ids_map[item.identifier]
            id_list.append(id)

        for j, item in enumerate(ids):
            expt = el[ids.index(item)]
            i = expt.imageset
            table_list.append([id_list[j], i.paths()[0]])

        loader = ChoiceLoader(
            [PackageLoader("xia2", "templates"), PackageLoader("dials", "templates")]
        )
        env = Environment(loader=loader)

        template = env.get_template("clusters.html")
        html = template.render(
            page_title=params.title,
            cc_cluster_table=MCA._cc_cluster_table,
            cc_cluster_json=MCA._cc_cluster_json,
            cos_angle_cluster_table=MCA._cos_angle_cluster_table,
            cos_angle_cluster_json=MCA._cos_angle_cluster_json,
            image_range_tables=[table_list],
            xia2_version=Version,
        )

        with open("xia2.cluster_analysis.html", "wb") as f:
            f.write(html.encode("utf-8", "xmlcharrefreplace"))

        print("Clusters recommended for comparison in xia2.cluster_analysis.log")
