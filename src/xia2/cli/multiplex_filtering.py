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
from dials.util.exclude_images import (
    exclude_image_ranges_for_scaling,
    get_valid_image_ranges,
)
from dials.util.export_mtz import match_wavelengths
from dials.util.multi_dataset_handling import (
    assign_unique_identifiers,
    parse_multiple_datasets,
)
from dials.util.options import ArgumentParser, flatten_experiments, flatten_reflections
from dials.util.reference import intensities_from_reference_file
from dials.util.version import dials_version

import xia2.Handlers.Streams
from xia2.Applications.xia2_main import write_citations
from xia2.Driver.timing import record_step
from xia2.Handlers.Citations import Citations
from xia2.Handlers.Streams import banner
from xia2.Modules.MultiCrystal.data_manager import DataManager
from xia2.Modules.MultiCrystal.ScaleAndMerge import MultiCrystalScale, Scale
from xia2.Modules.Scaler.DialsScaler import (
    convert_merged_mtz_to_sca,
    convert_unmerged_mtz_to_sca,
)
from xia2.Modules.SSX.util import report_timing
from xia2.XIA2Version import Version

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
  log = xia2.multiplex_filtering.log
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


def filter_existing_multiplex(expts, refls, params):
    data_manager = DataManager(expts, refls)
    d_spacings: flex.double = data_manager._reflections["d"]
    params.r_free_flags.d_min = flex.min(d_spacings.select(d_spacings > 0))
    params.r_free_flags.d_max = flex.max(d_spacings)
    params.unit_cell.refine = []
    logger.notice(banner("Rescaling with extra filtering"))  # type: ignore
    filtered = Scale(data_manager, params, filtering=True)
    results = filtered.scale_and_filter_results
    logger.info("Scale and filtering:\n%s", results)
    logger.notice(banner("Merging (Filtered)"))  # type: ignore
    logger.info(f"Datasets merged after filtering: {len(data_manager._experiments)}")

    if params.small_molecule.composition:
        MultiCrystalScale.export_shelx(
            params,
            data_manager._experiments,
            data_manager._reflections,
            "filtered",
        )
    MultiCrystalScale.export_merged_mtz(
        params,
        data_manager._experiments,
        data_manager._reflections,
        "filtered.mtz",
        filtered.d_min,
    )

    wavelengths = match_wavelengths(
        data_manager.experiments, params.wavelength_tolerance
    )  # in experiments order

    if len(wavelengths) > 1:
        data_manager.split_by_wavelength(params.wavelength_tolerance)
        for wl in wavelengths:
            name = data_manager.export_unmerged_wave_mtz(
                wl,
                "filtered_unmerged",
                d_min=filtered.d_min,
                wavelength_tolerance=params.wavelength_tolerance,
            )
            if name:
                convert_unmerged_mtz_to_sca(name)

            # unmerged mmcif for multiple wavelength
            data_manager.export_unmerged_wave_mmcif(
                wl, "filtered_unmerged", d_min=filtered.d_min
            )

        # now export merged of each
        for wl in wavelengths:
            name = MultiCrystalScale.export_merged_wave_mtz(
                params,
                data_manager,
                wl,
                "filtered",
                filtered.d_min,
            )
            if name:
                convert_merged_mtz_to_sca(name)
    else:
        data_manager.export_unmerged_mtz(
            "filtered_unmerged.mtz",
            d_min=filtered.d_min,
            wavelength_tolerance=params.wavelength_tolerance,
        )
        convert_merged_mtz_to_sca("filtered.mtz")
        convert_unmerged_mtz_to_sca("filtered_unmerged.mtz")

        data_manager.export_unmerged_mmcif(
            "filtered_unmerged.mmcif", d_min=filtered.d_min
        )

    data_manager._set_batches()
    data_manager.export_experiments("filtered.expt")
    data_manager.export_reflections("filtered.refl", d_min=filtered.d_min)

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

    usage = "xia2.multiplex_filtering [options] [param.phil] scaled.expt scaled.refl"

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
        debugfile="xia2.multiplex_filtering.debug.log",
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

    try:
        assert len(params.input.reflections) == 1
    except AssertionError:
        raise sys.exit(
            "Provide only the path to the models.expt and observations.refl file from a previous xia2.multiplex run."
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

    if not params.r_free_flags.reference:
        mplx_directory = (
            pathlib.Path(params.input.experiments[0].filename).resolve().parent
        )
        reference_mtz = mplx_directory / "scaled.mtz"
        try:
            assert reference_mtz.is_file()
        except AssertionError:
            raise sys.exit(
                "Provide the path to the scaled.mtz file from multiplex using the commandline input r_free_flags.reference."
            )
        params.r_free_flags.reference = reference_mtz

    if not params.filtering.method:
        # Since whole point is filtering, set this as defailt
        params.filtering.method = "deltacchalf"
        logger.info(
            "No filtering options specified, defaulting to filtering.method=deltacchalf"
        )

    try:
        multiplex_json = mplx_directory / "xia2.multiplex.json"
        assert multiplex_json.is_file()
    except AssertionError:
        logger.info("Can't find existing json. Comparisons not available in HTML")
        params.__inject__("multiplex_json", None)
    else:
        params.__inject__("multiplex_json", multiplex_json)

    try:
        filter_existing_multiplex(experiments, reflections_all, params)
    except ValueError as e:
        sys.exit(str(e))

    write_citations(program="xia2.multiplex")
