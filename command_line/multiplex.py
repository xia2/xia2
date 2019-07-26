#!/usr/bin/env dials.python
from __future__ import absolute_import, division, print_function

import logging
import random
from collections import OrderedDict

import iotbx.phil
from dials.util import Sorry

import xia2.Handlers.Streams
from dials.array_family import flex
from dials.util.multi_dataset_handling import (
    assign_unique_identifiers,
    parse_multiple_datasets,
)
from dials.util.options import OptionParser
from dials.util.options import flatten_experiments, flatten_reflections
from dials.util.version import dials_version
from xia2.Modules.MultiCrystal import ScaleAndMerge

logger = logging.getLogger("xia2.multiplex")

help_message = """
"""

phil_scope = iotbx.phil.parse(
    """
include scope xia2.Modules.MultiCrystal.ScaleAndMerge.phil_scope

seed = 42
  .type = int(value_min=0)

output {
  log = xia2.multiplex.log
    .type = str
}
""",
    process_includes=True,
)


def run():
    usage = (
        "xia2.multiplex [options] [param.phil] "
        "models1.expt models2.expt observations1.refl "
        "observations2.refl..."
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
    xia2.Handlers.Streams.streams_off()
    xia2.Handlers.Streams.setup_logging(
        logfile=params.output.log, verbose=options.verbose
    )

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
        flex.set_random_seed(params.seed)
        random.seed(params.seed)

    expt_filenames = OrderedDict((e.filename, e.data) for e in params.input.experiments)
    refl_filenames = OrderedDict((r.filename, r.data) for r in params.input.reflections)

    experiments = flatten_experiments(params.input.experiments)
    reflections = flatten_reflections(params.input.reflections)
    reflections = parse_multiple_datasets(reflections)
    experiments, reflections = assign_unique_identifiers(experiments, reflections)

    reflections_all = flex.reflection_table()
    assert len(reflections) == 1 or len(reflections) == len(experiments)
    if len(reflections) > 1:
        for i, (expt, refl) in enumerate(zip(experiments, reflections)):
            reflections_all.extend(refl)
    else:
        reflections_all = reflections
    reflections_all.assert_experiment_identifiers_are_consistent(experiments)

    if params.identifiers is not None:
        identifiers = []
        for identifier in params.identifiers:
            identifiers.extend(identifier.split(","))
        params.identifiers = identifiers
    scaled = ScaleAndMerge.MultiCrystalScale(experiments, reflections_all, params)


if __name__ == "__main__":
    run()
