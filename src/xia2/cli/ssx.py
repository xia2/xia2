"""
xia2.ssx: A processing pipeline for data integration of synchrotron
serial crystallography images, using tools from the DIALS package.

To explore the unit cell/space group of your data, run with just the image data, e.g.:
    xia2.ssx template=images_####.cbf
    xia2.ssx image=image_master.h5
Accurate data integration requires an accurate reference geometry determined from
a joint refinement in DIALS (a refined.expt file).
With a known unit cell & space group, to determine a reference geometry without further processing steps, run e.g.:
    xia2.ssx template=images_####.cbf unit_cell=x space_group=y steps=None
To run full processing with a reference geometry, run e.g.:
    xia2.ssx template=images_####.cbf unit_cell=x space_group=y reference_geometry=geometry_refinement/refined.expt

Refer to the individual DIALS program documentation or
https://dials.github.io/ssx_processing_guide.html for more details on SSX processing
in DIALS, and https://xia2.github.io/serial_crystallography.html for more details
on this pipeline.
"""

from __future__ import annotations

import logging
import pathlib
import sys
import traceback

from dials.util.options import ArgumentParser

import iotbx.phil

import xia2.Driver.timing
import xia2.Handlers.Streams
from xia2.Handlers.Files import cleanup
from xia2.Modules.SSX.xia2_ssx import full_phil_str, run_xia2_ssx

phil_scope = iotbx.phil.parse(full_phil_str)

xia2_logger = logging.getLogger(__name__)


def run(args=sys.argv[1:]):
    """
    Parse the command line input, setup logging and run the ssx processing script.
    """
    parser = ArgumentParser(
        usage="xia2.ssx template=images_####.cbf unit_cell=x space_group=y",
        read_experiments=False,
        read_reflections=False,
        phil=phil_scope,
        check_format=False,
        epilog=__doc__,
    )
    params, _ = parser.parse_args(args=args, show_diff_phil=False)

    xia2.Handlers.Streams.setup_logging(
        logfile="xia2.ssx.log", debugfile="xia2.ssx.debug.log"
    )
    # remove the xia2 handler from the dials logger.
    dials_logger = logging.getLogger("dials")
    dials_logger.handlers.clear()

    diff_phil = parser.diff_phil.as_str()
    if diff_phil:
        xia2_logger.info("The following parameters have been modified:\n%s", diff_phil)

    cwd = pathlib.Path.cwd()
    try:
        with cleanup(cwd):
            run_xia2_ssx(cwd, params)
    except ValueError as e:
        xia2_logger.info(f"Error: {e}")
        sys.exit(0)
    except FileNotFoundError as e:
        xia2_logger.info(f"Unable to find file: {e}")
        sys.exit(0)
    except Exception as e:
        with (cwd / "xia2-error.txt").open(mode="w") as fh:
            traceback.print_exc(file=fh)
        xia2_logger.error("Error: %s", str(e))
        xia2_logger.info(traceback.format_exc())
        xia2_logger.warning(
            "Please send the contents of xia2.ssx.log and xia2-error.txt to xia2.support@gmail.com"
        )
        sys.exit(1)
