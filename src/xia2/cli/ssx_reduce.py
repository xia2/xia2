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

from xia2.cli.ssx import report_timing
from xia2.Modules.SSX.data_reduction_simple import (
    SimpleDataReduction,
    SimpleReductionParams,
)

phil_str = """
directory = None
  .type = str
  .multiple = True
  .help = "Path to directory containing integrated_*.{refl,expt} files"
space_group = None
  .type = space_group
nproc = 1
  .type = int
batch_size = 1000
  .type = int
  .help = "The minimum batch size for consistent reindexing of data with cosym"
clustering {
  threshold=1000
    .type = float(value_min=0)
}
scaling {
  anomalous = False
    .type = bool
    .help = "If True, keep anomalous pairs separate during scaling."
  model = None
    .type = path
    .help = "A model pdb file to use as a reference for scaling."
}

d_min = None
  .type = float
"""

phil_scope = iotbx.phil.parse(phil_str)

xia2_logger = logging.getLogger(__name__)

import xia2.Handlers.Streams


@report_timing
def run_xia2_ssx_reduce(
    root_working_directory: Path, params: iotbx.phil.scope_extract
) -> None:
    directories = [Path(i).resolve() for i in params.directory]

    reduction_params = SimpleReductionParams.from_phil(params)
    reducer = SimpleDataReduction(root_working_directory, directories)
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
    run_xia2_ssx_reduce(cwd, params)
