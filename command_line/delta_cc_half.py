from __future__ import absolute_import, division, print_function

import logging
import os
import sys

from cctbx import crystal
from iotbx.reflection_file_reader import any_reflection_file
import libtbx.phil

from dials.util.filter_reflections import filtered_arrays_from_experiments_reflections
from dials.util.multi_dataset_handling import (
    assign_unique_identifiers,
    parse_multiple_datasets,
)
from dials.util.options import OptionParser
from dials.util.options import flatten_experiments, flatten_reflections
from dials.util.version import dials_version

import xia2.Handlers.Streams
from xia2.Handlers.Citations import Citations
from xia2.Modules.DeltaCcHalf import DeltaCcHalf

logger = logging.getLogger("xia2.delta_cc_half")

phil_scope = libtbx.phil.parse(
    """
include scope xia2.Modules.DeltaCcHalf.phil_scope

output {
  log = xia2.delta_cc_half.log
    .type = path
}
""",
    process_includes=True,
)


def run(args):
    # Create the parser
    parser = OptionParser(
        # usage=usage,
        phil=phil_scope,
        read_reflections=True,
        read_experiments=True,
        check_format=False,
        # epilog=help_message,
    )

    # Parse the command line
    params, options, args = parser.parse_args(
        args=args, show_diff_phil=False, return_unhandled=True
    )

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

    if params.unit_cell is not None:
        unit_cell = params.unit_cell
        crystal_symmetry = crystal.symmetry(unit_cell=unit_cell)
    else:
        crystal_symmetry = None

    if params.unit_cell is not None:
        unit_cell = params.unit_cell
        crystal_symmetry = crystal.symmetry(unit_cell=unit_cell)
    else:
        crystal_symmetry = None

    if len(params.input.experiments):

        experiments = flatten_experiments(params.input.experiments)
        reflections = flatten_reflections(params.input.reflections)

        reflections = parse_multiple_datasets(reflections)
        if len(experiments) != len(reflections):
            raise sys.exit(
                "Mismatched number of experiments and reflection tables found: %s & %s."
                % (len(experiments), len(reflections))
            )
        experiments, reflections = assign_unique_identifiers(experiments, reflections)

        # transform models into miller arrays
        datasets, batches = filtered_arrays_from_experiments_reflections(
            experiments,
            reflections,
            outlier_rejection_after_filter=False,
            partiality_threshold=0.99,
            return_batches=True,
        )

        unmerged_intensities = None
        batches_all = None
        for intensities, batches_ in zip(datasets, batches):
            if unmerged_intensities is None:
                unmerged_intensities = intensities
                batches_all = batches_
            else:
                unmerged_intensities = unmerged_intensities.concatenate(
                    intensities
                ).set_observation_type(intensities.observation_type())
                batches_all = batches_all.concatenate(batches_)

    if len(args) and os.path.isfile(args[0]):
        result = any_reflection_file(args[0])
        unmerged_intensities = None
        batches_all = None

        for ma in result.as_miller_arrays(
            merge_equivalents=False, crystal_symmetry=crystal_symmetry
        ):
            if ma.info().labels == ["I(+)", "SIGI(+)", "I(-)", "SIGI(-)"]:
                assert ma.anomalous_flag()
                unmerged_intensities = ma
            elif ma.info().labels == ["I", "SIGI"]:
                assert not ma.anomalous_flag()
                unmerged_intensities = ma
            elif ma.info().labels == ["BATCH"]:
                batches_all = ma

        assert batches_all is not None
        assert unmerged_intensities is not None

    id_to_batches = None

    if len(params.batch) > 0:
        id_to_batches = {}
        for b in params.batch:
            assert b.id is not None
            assert b.range is not None
            assert b.id not in id_to_batches, "Duplicate batch id: %s" % b.id
            id_to_batches[b.id] = b.range

    result = DeltaCcHalf(
        unmerged_intensities,
        batches_all,
        n_bins=params.n_bins,
        d_min=params.d_min,
        cc_one_half_method=params.cc_one_half_method,
        id_to_batches=id_to_batches,
    )
    hist_filename = "delta_cc_hist.png"
    logger.info("Saving histogram to %s" % hist_filename)
    result.plot_histogram(hist_filename)
    logger.info(result.get_table())

    Citations.cite("delta_cc_half")
    for citation in Citations.get_citations_acta():
        logger.info(citation)


if __name__ == "__main__":
    xia2.Handlers.Streams.setup_logging()
    run(sys.argv[1:])
