import logging
import random
import sys

import iotbx.phil

import xia2.Handlers.Streams
from dials.array_family import flex
from dials.util.exclude_images import exclude_image_ranges_for_scaling
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
xia2.multiplex performs symmetry analysis, scaling and merging of multi-crystal data
sets, as well as analysis of various pathologies that typically affect multi-crystal
data sets, including non-isomorphism, radiation damage and preferred orientation.

It uses a number of DIALS programs internally, including dials.cosym,
dials.two_theta_refine, dials.scale and dials.symmetry:

- Preliminary filtering of datasets using hierarchical unit cell clustering
- Laue group determination and resolution of indexing ambiguities with dials.cosym
- Determination of "best" overall unit cell with dials.two_theta_refine
- Initial round of scaling with dials.scale
- Estimation of resolution limit with dials.estimate_resolution
- Final round of scaling after application of the resolution limit
- Analysis of systematic absences with dials.symmetry
- Optional ΔCC½ filtering to remove outlier data sets
- Analysis of non-isomorphism, radiation damage and preferred orientation

Examples use cases
------------------

Multiple integrated experiments and reflections in combined files::

  xia2.multiplex integrated.expt integrated.refl

Integrated experiments and reflections in separate input files::

  xia2.multiplex integrated_1.expt integrated_1.refl \\
    integrated_2.expt integrated_2.refl

Override the automatic space group determination and resolution estimation::

  xia2.multiplex space_group=C2 resolution.d_min=2.5 \\
    integrated_1.expt integrated_1.refl \\
    integrated_2.expt integrated_2.refl

Filter potential outlier data sets using the ΔCC½ method::

  xia2.multiplex filtering.method=deltacchalf \\
    integrated.expt integrated.refl

"""

phil_scope = iotbx.phil.parse(
    """
include scope xia2.Modules.MultiCrystal.ScaleAndMerge.phil_scope

include scope dials.util.exclude_images.phil_scope

seed = 42
  .type = int(value_min=0)

output {
  log = xia2.multiplex.log
    .type = str
}
""",
    process_includes=True,
)


def run(args):
    usage = "xia2.multiplex [options] [param.phil] integrated.expt integrated.refl"

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
    params, options = parser.parse_args(args=args, show_diff_phil=False)

    # Configure the logging
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
        raise sys.exit(
            "The number of input reflections files does not match the "
            "number of input experiments"
        )

    if params.seed is not None:
        flex.set_random_seed(params.seed)
        random.seed(params.seed)

    experiments = flatten_experiments(params.input.experiments)
    reflections = flatten_reflections(params.input.reflections)
    if len(experiments) < 2:
        sys.exit("xia2.multiplex requires a minimum of two experiments")
    reflections = parse_multiple_datasets(reflections)
    experiments, reflections = assign_unique_identifiers(experiments, reflections)

    reflections, experiments = exclude_image_ranges_for_scaling(
        reflections, experiments, params.exclude_images
    )

    reflections_all = flex.reflection_table()
    assert len(reflections) == 1 or len(reflections) == len(experiments)
    for i, (expt, refl) in enumerate(zip(experiments, reflections)):
        reflections_all.extend(refl)
    reflections_all.assert_experiment_identifiers_are_consistent(experiments)

    if params.identifiers is not None:
        identifiers = []
        for identifier in params.identifiers:
            identifiers.extend(identifier.split(","))
        params.identifiers = identifiers

    try:
        ScaleAndMerge.MultiCrystalScale(experiments, reflections_all, params)
    except ValueError as e:
        sys.exit(str(e))


if __name__ == "__main__":
    run(sys.argv[1:])
