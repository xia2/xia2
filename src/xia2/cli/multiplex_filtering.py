from __future__ import annotations

import json
import logging
import pathlib
import random
import sys
from collections import OrderedDict

import iotbx.cif
import iotbx.phil
import numpy as np
from dials.algorithms.scaling.scaling_library import determine_best_unit_cell
from dials.array_family import flex
from dials.util.export_mtz import match_wavelengths
from dials.util.options import ArgumentParser
from dials.util.version import dials_version
from dxtbx.model.experiment_list import ExperimentList

import xia2.Handlers.Streams
from xia2.Applications.xia2_main import write_citations
from xia2.Driver.timing import record_step
from xia2.Handlers.Citations import Citations
from xia2.Modules.MultiCrystal.data_manager import DataManager
from xia2.Modules.MultiCrystal.ScaleAndMerge import MultiCrystalScale
from xia2.Modules.SSX.util import report_timing
from xia2.XIA2Version import Version

logger = logging.getLogger("xia2.multiplex")

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
filtering
  .short_caption = "Filtering"
{
  max_cycles = None
    .type = int(value_min=1)
    .short_caption = "Maximum number of cycles"
  max_percent_removed = None
    .type = float
    .short_caption = "Maximum percentage removed"
  min_completeness = None
    .type = float(value_min=0, value_max=100)
    .help = "Desired minimum completeness, as a percentage (0 - 100)."
    .short_caption = "Minimum completeness"
  mode = dataset image_group
    .type = choice
    .help = "Perform analysis on whole datasets or batch groups"
  group_size = None
    .type = int(value_min=1)
    .help = "The number of images to group together when calculating delta"
            "cchalf in image_group mode"
    .short_caption = "Group size"
  stdcutoff = None
    .type = float
    .help = "Datasets with a ΔCC½ below (mean - stdcutoff*std) are removed"
    .short_caption = "Standard deviation cutoff"
}
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


def filter_existing_multiplex(expts, refls, params):
    data_manager = DataManager(expts, refls)
    d_spacings: flex.double = data_manager._reflections["d"]
    params.r_free_flags.d_min = flex.min(d_spacings.select(d_spacings > 0))
    params.r_free_flags.d_max = flex.max(d_spacings)
    wavelengths = match_wavelengths(
        data_manager.experiments, params.wavelength_tolerance
    )
    free_flags_in_full_set = True  # ???
    results, _, filtered, data_manager = MultiCrystalScale.filter(
        data_manager, params, free_flags_in_full_set, wavelengths
    )

    with record_step("xia2.report(filtered)"):
        individual_report_dicts = OrderedDict()
        d = MultiCrystalScale._report_as_dict(
            filtered.report(), len(data_manager._experiments)
        )
        individual_report_dicts["Filtered"] = MultiCrystalScale._individual_report_dict(
            d, "Filtered"
        )
        MultiCrystalScale._log_report_info(d)

        if params.multiplex_json:
            with open(params.multiplex_json, "r") as f:
                parent_data = json.load(f)

            for i in parent_data["datasets"]:
                individual_report_dicts[i] = parent_data["datasets"][i]

        from jinja2 import ChoiceLoader, Environment, PackageLoader

        space_group = (
            data_manager.experiments[0]
            .crystal.get_space_group()
            .info()
            .symbol_and_number()
        )
        unit_cell = determine_best_unit_cell(data_manager.experiments)
        image_range_table = individual_report_dicts["Filtered"]["image_range_table"]
        styles = {}

        loader = ChoiceLoader(
            [PackageLoader("xia2", "templates"), PackageLoader("dials", "templates")]
        )
        env = Environment(loader=loader)
        template = env.get_template("multiplex_filtering.html")
        html = template.render(
            page_title="xia2.multiplex-filtering report",
            space_group=space_group,
            unit_cell=str(unit_cell),
            cc_half_significance_level=params.resolution.cc_half_significance_level,
            image_range_tables=[image_range_table],
            individual_dataset_reports=individual_report_dicts,
            styles=styles,
            xia2_version=Version,
        )
        json_data: dict = {}
        json_data["datasets"] = {}
        for report_name, report in individual_report_dicts.items():
            json_data["datasets"][report_name] = {
                k: report[k]
                for k in (
                    "resolution_graphs",
                    "batch_graphs",
                    "xtriage",
                    "merging_stats",
                    "merging_stats_anom",
                    "misc_graphs",
                )
            }

        with open("xia2.multiplex-filtering.json", "w") as f:
            json.dump(json_data, f)

        with open("xia2.multiplex-filtering.html", "wb") as f:
            f.write(html.encode("utf-8", "xmlcharrefreplace"))


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
    parser = ArgumentParser(
        usage=usage,
        phil=filtering_scope,
        read_reflections=False,
        read_experiments=False,
        check_format=False,
        epilog=help_message,
    )

    fake_parser = ArgumentParser(
        usage=usage,
        phil=mplx_scope,
        read_reflections=False,
        read_experiments=False,
        check_format=False,
        epilog=help_message,
    )

    # Parse the command line
    filter_params, filter_options = parser.parse_args(args=args, show_diff_phil=False)

    full_params, full_options = fake_parser.parse_args(
        args=[f"{mplx_directory / 'xia2-multiplex-working.phil'}"], show_diff_phil=False
    )

    full_params.filtering.method = "deltacchalf"
    full_params.filtering.deltacchalf.max_cycles = filter_params.filtering.max_cycles
    full_params.filtering.deltacchalf.max_percent_removed = (
        filter_params.filtering.max_percent_removed
    )
    full_params.filtering.deltacchalf.min_completeness = (
        filter_params.filtering.min_completeness
    )
    full_params.filtering.deltacchalf.mode = filter_params.filtering.mode
    full_params.filtering.deltacchalf.group_size = filter_params.filtering.group_size
    full_params.filtering.deltacchalf.stdcutoff = filter_params.filtering.stdcutoff

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
    diff_phil = parser.diff_phil.as_str()
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
        filter_existing_multiplex(experiments, reflections, full_params)
    except ValueError as e:
        sys.exit(str(e))

    write_citations(program="xia2.multiplex")
