"""
xia2.ssx_reduce: A data reduction pipeline for synchrotron serial crystallography
data, using tools from the DIALS package. This pipeline is the data reduction
segment of xia2.ssx.
To run, provide directories containing integrated data file and a space group:
    xia2.ssx_reduce directory=batch_{1..5} space_group=x
This processing runs dials.cluster_unit_cell, dials.cosym, dials.reindex,
dials.scale and dials.merge. Refer to the individual DIALS program documentation
or https://dials.github.io/ssx_processing_guide.html for more details.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import iotbx.phil
from dials.util.options import ArgumentParser
from libtbx import Auto
from libtbx.introspection import number_of_processors

from xia2.Modules.SSX.data_reduction_simple import (
    SimpleDataReduction,
    SimpleReductionParams,
)
from xia2.Modules.SSX.util import report_timing

phil_str = """
directory = None
  .type = str
  .multiple = True
  .help = "Path to directory containing integrated_*.{refl,expt} files"
reflections = None
  .type = str
  .multiple = True
  .help = "Path to an integrated reflections file"
experiments = None
  .type = str
  .multiple = True
  .help = "Path to an integrated experiments file"
nproc = Auto
  .type = int
batch_size = 1000
  .type = int
  .help = "The minimum batch size for consistent reindexing of data with cosym"
d_min = None
  .type = float
"""

data_reduction_phil_str = """
clustering {
  threshold=None
    .type = float(value_min=0, allow_none=True)
    .help = "If no data has previously been reduced, then unit cell clustering"
            "is performed. This threshold is the value at which the dendrogram"
            "will be split in dials.cluster_unit_cell (the default value there"
            "is 5000). A higher threshold value means that unit cells with greater"
            "differences will be retained."
            "Only the largest cluster obtained from cutting at this threshold is"
            "used for data reduction. Setting the threshold to None/0 will"
            "skip this unit cell clustering and proceed to filtering based on"
            "the absolute angle/length tolerances."
  absolute_angle_tolerance = 1.0
    .type = float(value_min=0, allow_none=True)
    .help = "Filter the integrated data based on the median unit cell angles"
            "and this tolerance. If set to None/0, filtering will be skipped."
  absolute_length_tolerance = 1.0
    .type = float(value_min=0, allow_none=True)
    .help = "Filters the integrated data based on the median unit cell lengths"
            "and this tolerance. If set to None/0, filtering will be skipped."
  central_unit_cell = None
    .type = unit_cell
    .help = "Filter the integrated data based on the tolerances about these cell"
            "parameters, rather than the median cell."
}
symmetry {
  space_group = None
    .type = space_group
    .expert_level = 1
}
scaling {
  anomalous = False
    .type = bool
    .help = "If True, keep anomalous pairs separate during scaling."
  model = None
    .type = path
    .help = "A model pdb file to use as a reference for scaling."
}
"""


phil_scope = iotbx.phil.parse(phil_str + data_reduction_phil_str)

xia2_logger = logging.getLogger(__name__)

import xia2.Handlers.Streams


@report_timing
def run_xia2_ssx_reduce(
    root_working_directory: Path, params: iotbx.phil.scope_extract
) -> None:

    if params.nproc is Auto:
        params.nproc = number_of_processors(return_value_if_unknown=1)
    reduction_params = SimpleReductionParams.from_phil(params)

    if params.directory:
        if params.reflections or params.experiments:
            xia2_logger.warning(
                "Only a directory or reflections+experiments can be given\n"
                "as input. Proceeding using only directories"
            )
        directories = [Path(i).resolve() for i in params.directory]
        reducer = SimpleDataReduction.from_directories(
            root_working_directory, directories
        )
    elif params.reflections or params.experiments:
        if not (params.reflections and params.experiments):
            raise ValueError("Reflections and experiments files must both be specified")
        reflections = [Path(i).resolve() for i in params.reflections]
        experiments = [Path(i).resolve() for i in params.experiments]
        reducer = SimpleDataReduction.from_files(
            root_working_directory, reflections, experiments
        )
    else:
        raise ValueError("Reflections and experiments files must both be specified")

    reducer.run(reduction_params)


def run(args=sys.argv[1:]):

    parser = ArgumentParser(
        usage="xia2.ssx_reduce directory=/path/to/integrated/directory/",
        read_experiments=False,
        read_reflections=False,
        phil=phil_scope,
        check_format=False,
        epilog=__doc__,
    )
    params, _ = parser.parse_args(args=args, show_diff_phil=False)

    xia2.Handlers.Streams.setup_logging(
        logfile="xia2.ssx_reduce.log", debugfile="xia2.ssx_reduce.debug.log"
    )
    # remove the xia2 handler from the dials logger.
    dials_logger = logging.getLogger("dials")
    dials_logger.handlers.clear()

    diff_phil = parser.diff_phil.as_str()
    if diff_phil:
        xia2_logger.info("The following parameters have been modified:\n%s", diff_phil)

    cwd = Path.cwd()
    try:
        run_xia2_ssx_reduce(cwd, params)
    except ValueError as e:
        xia2_logger.info(f"Error: {e}")
