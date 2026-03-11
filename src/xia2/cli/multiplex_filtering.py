from __future__ import annotations

import logging
import pathlib
import random
import sys

import iotbx.cif
import iotbx.phil
import numpy as np
from dials.array_family import flex
from dials.util.options import ArgumentParser
from dials.util.version import dials_version
from dxtbx.model.experiment_list import ExperimentList

import xia2.Handlers.Streams
from xia2.Applications.xia2_main import write_citations
from xia2.Handlers.Citations import Citations
from xia2.Modules.MultiCrystal.filter import FilterExistingMultiplex
from xia2.Modules.SSX.util import report_timing

logger = logging.getLogger("xia2.multiplex_filtering")

help_message = """
xia2.multiplex performs symmetry analysis, scaling and merging of multi-crystal data
sets, as well as analysis of various pathologies that typically affect multi-crystal
data sets, including non-isomorphism, radiation damage and preferred orientation.

xia2.multiplex_filtering applies the filtering algorithms to an existing directory
containing a finished multiplex job. This means that the entire program does not need
to be re-run if you decide later you want filtering applied to your dataset.

There are two modes possible (both using changes in CCHalf to include/exclude)

- filtering.mode=dataset
    This will filter out entire datasets based on changes in CCHalf.
- filtering.mode=image_group
    This will filter out ranges of images instead of datasets.
    Tailor size with filtering.group_size

For further details, and to cite usage, please see:
`Gildea, R. J. et al. (2022) Acta Cryst. D78, 752-769 <https://doi.org/10.1107/S2059798322004399>`_.

Examples use cases
------------------

Run this module on an existing multiplex_folder::

  xia2.multiplex_filtering multiplex_folder

Customise filtering parameters::

  xia2.multiplex_filtering multiplex_folder \\
    filtering.mode=image_group \\
    filtering.group_size=50

"""
filtering_scope = iotbx.phil.parse(
    """
include scope xia2.Modules.MultiCrystal.filter_phil.filtering_scope

output {
  log = xia2.multiplex_filtering.log
    .type = str
}
""",
    process_includes=True,
)

mplx_scope = iotbx.phil.parse(
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
mplx_scope = mplx_scope.fetch(
    source=iotbx.phil.parse(
        """\
r_free_flags.extend = True
"""
    )
)


@report_timing
def run(args=sys.argv[1:]):
    Citations.cite("xia2.multiplex")

    usage = "xia2.multiplex_filtering [options] [param.phil] multiplex_directory"

    mplx_directory = None

    for i in args:
        input_directory = pathlib.Path(i).resolve()
        if input_directory.is_dir():
            args.remove(i)
            mplx_directory = input_directory

    try:
        assert mplx_directory
    except AssertionError:
        raise sys.exit(
            "Please provide a path to a directory containing a completed multiplex job."
        )

    # Check multiplex directory has all the files this module needs

    required_files = [
        mplx_directory / "models.expt",
        mplx_directory / "observations.refl",
        mplx_directory / "scaled.mtz",
        mplx_directory / "xia2-multiplex-working.phil",
        mplx_directory / "xia2.multiplex.json",
    ]
    for file in required_files:
        try:
            assert file.is_file()
        except AssertionError:
            raise sys.exit(
                "Make sure xia2.multiplex has finished running and the following files are present: scaled.expt, scaled.refl, scaled.mtz, xia2-multiplex-working.phil, xia2.multiplex.json."
            )

    # Create the parser
    filter_parser = ArgumentParser(
        usage=usage,
        phil=filtering_scope,
        read_reflections=False,
        read_experiments=False,
        check_format=False,
        epilog=help_message,
    )

    mplx_parser = ArgumentParser(
        usage=usage,
        phil=mplx_scope,
        read_reflections=False,
        read_experiments=False,
        check_format=False,
        epilog=help_message,
    )

    # Parse the command line
    filter_params, filter_options = filter_parser.parse_args(
        args=args, show_diff_phil=False
    )

    full_params, _ = mplx_parser.parse_args(
        args=[f"{mplx_directory / 'xia2-multiplex-working.phil'}"], show_diff_phil=False
    )

    full_params.filtering.method = "deltacchalf"
    full_params.filtering.deltacchalf.max_cycles = (
        filter_params.filtering.deltacchalf.max_cycles
    )
    full_params.filtering.deltacchalf.max_percent_removed = (
        filter_params.filtering.deltacchalf.max_percent_removed
    )
    full_params.filtering.deltacchalf.min_completeness = (
        filter_params.filtering.deltacchalf.min_completeness
    )
    full_params.filtering.deltacchalf.mode = filter_params.filtering.deltacchalf.mode
    full_params.filtering.deltacchalf.group_size = (
        filter_params.filtering.deltacchalf.group_size
    )
    full_params.filtering.deltacchalf.stdcutoff = (
        filter_params.filtering.deltacchalf.stdcutoff
    )

    full_params.__inject__(
        "multiplex_json", str(mplx_directory / "xia2.multiplex.json")
    )

    # Configure the logging
    xia2.Handlers.Streams.setup_logging(
        logfile=filter_params.output.log,
        verbose=filter_options.verbose,
        debugfile="xia2.multiplex_filtering.debug.log",
    )

    dials_logger = logging.getLogger("dials")
    dials_logger.handlers.clear()
    logger.info(dials_version())

    logger.info(f"Using {mplx_directory} as previous multiplex job.")

    # Log the diff phil
    diff_phil = filter_parser.diff_phil.as_str()
    if diff_phil != "":
        logger.info("The following parameters have been modified:\n")
        logger.info(diff_phil)

    if full_params.seed is not None:
        flex.set_random_seed(full_params.seed)
        np.random.seed(full_params.seed)
        random.seed(full_params.seed)

    experiments = ExperimentList.from_file(
        mplx_directory / "models.expt", check_format=False
    )
    reflections = flex.reflection_table.from_file(mplx_directory / "observations.refl")

    if not full_params.r_free_flags.reference:
        full_params.r_free_flags.reference = str(mplx_directory / "scaled.mtz")

    try:
        filtering = FilterExistingMultiplex(experiments, reflections, full_params)
        filtering.filter_and_record()
    except ValueError as e:
        sys.exit(str(e))

    write_citations(program="xia2.multiplex")
