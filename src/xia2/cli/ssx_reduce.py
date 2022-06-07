"""
xia2.ssx_reduce: A data reduction pipeline for synchrotron serial crystallography
data, using tools from the DIALS package. This pipeline is the data reduction
section of xia2.ssx.

The input to the program is a set of dials integrated data files (.expt and .refl)
The easiest way to run is to specify directories containing integrated data files:
    xia2.ssx_reduce directory=batch_1 directory=batch_2
Alternatively, specify integrated data files:
    xia2.ssx_reduce reflections=batch_1/integrated.refl experiments=batch_1/integrated.expt

This processing runs unit cell filtering, dials.cosym, dials.scale and dials.merge.
Refer to the individual DIALS program documentation or
https://dials.github.io/ssx_processing_guide.html for more details.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import iotbx.phil
from dials.util.options import ArgumentParser

from xia2.Modules.SSX.xia2_ssx_reduce import full_phil_str, run_xia2_ssx_reduce

phil_scope = iotbx.phil.parse(full_phil_str)

xia2_logger = logging.getLogger(__name__)

import xia2.Handlers.Streams


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
