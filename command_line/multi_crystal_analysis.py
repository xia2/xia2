# -*- coding: utf-8 -*-
#!/usr/bin/env xia2.python
from __future__ import absolute_import, division, print_function

import logging

from dials.util import Sorry
import iotbx.phil

from dials.array_family import flex
from dials.util import log
from dials.util.options import OptionParser
from dials.util.options import flatten_experiments, flatten_reflections
from dials.util.multi_dataset_handling import parse_multiple_datasets
from xia2.Modules.MultiCrystalAnalysis import MultiCrystalReport

logger = logging.getLogger("xia2.multi_crystal_analysis")

help_message = """
"""

phil_scope = iotbx.phil.parse(
    """
include scope xia2.command_line.report.phil_scope

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

output {
  log = xia2.multi_crystal_analysis.log
    .type = str
  debug_log = xia2.multi_crystal_analysis.debug.log
    .type = str
}
""",
    process_includes=True,
)

phil_overrides = iotbx.phil.parse(
    """
prefix = xia2-multi-crystal-report
title = 'xia2 multi-crystal report'
"""
)

phil_scope = phil_scope.fetch(sources=[phil_overrides])


try:
    import matplotlib

    # http://matplotlib.org/faq/howto_faq.html#generate-images-without-having-a-window-appear
    matplotlib.use("Agg")  # use a non-interactive backend
    from matplotlib import pyplot  # noqa: F401
except ImportError:
    raise Sorry("matplotlib must be installed to generate a plot.")


def run():
    # The script usage
    usage = (
        "usage: xia2.multi_crystal_analysis [options] [param.phil] "
        "models.expt observations.refl"
    )

    # Create the parser
    parser = OptionParser(
        usage=usage,
        phil=phil_scope,
        read_reflections=True,
        read_experiments=True,
        check_format=False,
        epilog=help_message,
    )

    # Parse the command line
    params, options = parser.parse_args(show_diff_phil=False)

    # Configure the logging

    for name in ("xia2", "dials"):
        log.config(info=params.output.log, debug=params.output.debug_log, name=name)
    from dials.util.version import dials_version

    logger.info(dials_version())

    # Log the diff phil
    diff_phil = parser.diff_phil.as_str()
    if diff_phil != "":
        logger.info("The following parameters have been modified:\n")
        logger.info(diff_phil)

    # Try to load the models and data
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
        raise Sorry(
            "The number of input reflections files does not match the "
            "number of input experiments"
        )

    if params.seed is not None:
        import random

        flex.set_random_seed(params.seed)
        random.seed(params.seed)

    experiments = flatten_experiments(params.input.experiments)
    reflections = flatten_reflections(params.input.reflections)
    reflections = parse_multiple_datasets(reflections)

    joint_table = flex.reflection_table()
    for i in range(len(reflections)):
        joint_table.extend(reflections[i])
    reflections = joint_table

    MultiCrystalReport(
        params, experiments=experiments, reflections=reflections
    ).report()


if __name__ == "__main__":
    run()
