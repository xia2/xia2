from __future__ import annotations

import logging
import random
import sys

import iotbx.cif
import iotbx.phil
import numpy as np
from dials.array_family import flex
from dials.util.exclude_images import (
    exclude_image_ranges_for_scaling,
    get_valid_image_ranges,
)
from dials.util.multi_dataset_handling import (
    assign_unique_identifiers,
    parse_multiple_datasets,
)
from dials.util.options import ArgumentParser, flatten_experiments, flatten_reflections
from dials.util.reference import intensities_from_reference_file
from dials.util.version import dials_version

import xia2.Handlers.Streams
from xia2.Applications.xia2_main import write_citations
from xia2.Handlers.Citations import Citations
from xia2.Modules.MultiCrystal.ScaleAndMerge import MultiCrystalScale
from xia2.Modules.SSX.util import report_timing

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

For further details, and to cite usage, please see:
`Gildea, R. J. et al. (2022) Acta Cryst. D78, 752-769 <https://doi.org/10.1107/S2059798322004399>`_.

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

wavelength_tolerance = 0.0001
  .type = float
  .help = "Absolute tolerance, in Angstroms, for determining whether to merge data from different"
          "wavelengths in the output mtz/sca files. Increasing this number significantly may reduce"
          "downstream data quality due to loss of information on wavelength."

seed = 42
  .type = int(value_min=0)

output {
  log = xia2.multiplex.log
    .type = str
}
""",
    process_includes=True,
)

# override default parameters
phil_scope = phil_scope.fetch(
    source=iotbx.phil.parse(
        """\
r_free_flags.extend = True
"""
    )
)


@report_timing
def run(args=sys.argv[1:]):
    Citations.cite("xia2.multiplex")

    usage = "xia2.multiplex [options] [param.phil] integrated.expt integrated.refl"

    # Create the parser
    parser = ArgumentParser(
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
        logfile=params.output.log,
        verbose=options.verbose,
        debugfile="xia2.multiplex.debug.log",
    )

    dials_logger = logging.getLogger("dials")
    dials_logger.handlers.clear()
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
        np.random.seed(params.seed)
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

    image_ranges = get_valid_image_ranges(experiments)
    for i in image_ranges:
        if i is None:
            raise sys.exit(
                "Still images detected. Multiplex is only designed for merging multi-crystal rotation datasets. Please re-run with rotation data only."
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

    # If a reference file is defined, will make sure that multiplex output is consistent space group
    # dials.reindex is later used on the scaled and merged result to retain consistent setting

    if params.reference is not None:
        intensity_array = intensities_from_reference_file(params.reference)
        if params.symmetry.space_group is not None:
            intensity_sg_no = intensity_array.space_group().type().number()
            params_sg_no = params.symmetry.space_group.type().number()
            if intensity_sg_no != params_sg_no:
                raise sys.exit(
                    f"The input space group (#{params_sg_no}) does not match the reference file (#{intensity_sg_no})"
                )
        else:
            params.symmetry.space_group = intensity_array.space_group_info()
            logger.info(
                f"symmetry.space_group has been set to: {params.symmetry.space_group}"
            )

    if (
        len(params.clustering.hierarchical.method) == 2
        and params.clustering.hierarchical.max_cluster_height != 100
        and params.clustering.hierarchical.max_cluster_height_cc == 100
        and params.clustering.hierarchical.max_cluster_height_cos == 100
    ):
        # This means user has changed max_cluster_height from default
        # BUT wants both cos and cc clustering
        # AND didn't change the max_cluster_height for these two specifically
        raise sys.exit(
            "\nBoth correlation and cos angle clustering have been chosen "
            "but only one maximum cluster height has been specified.\n"
            "Please set clustering.max_cluster_height_cc and/or "
            "clustering.max_cluster_height_cos and re-run xia2.multiplex to differentiate."
        )

    try:
        runner = MultiCrystalScale(experiments, reflections_all, params)
        runner.run()
    except ValueError as e:
        sys.exit(str(e))

    write_citations(program="xia2.multiplex")
