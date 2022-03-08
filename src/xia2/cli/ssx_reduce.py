from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

from dials.util.options import ArgumentParser
from iotbx import phil

from xia2.Modules.SSX.data_reduction import SimpleDataReduction

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
clustering {
  threshold=1000
    .type = float
}
anomalous = False
  .type = bool
d_min = None
  .type = float
"""

phil_scope = phil.parse(phil_str)

xia2_logger = logging.getLogger(__name__)

import xia2.Handlers.Streams


def run(args=sys.argv[1:]):

    start_time = time.time()

    parser = ArgumentParser(
        usage="xia2.ssx_reduce directory=/path/to/integrated/directory/",
        read_experiments=False,
        read_reflections=False,
        phil=phil_scope,
        check_format=False,
        epilog="",
    )
    params, options = parser.parse_args(args=args, show_diff_phil=False)
    xia2.Handlers.Streams.setup_logging(logfile="xia2.ssx_reduce.log")
    # remove the xia2 handler from the dials logger.
    dials_logger = logging.getLogger("dials")
    dials_logger.handlers.clear()

    diff_phil = parser.diff_phil.as_str()
    if diff_phil:
        xia2_logger.info("The following parameters have been modified:\n%s", diff_phil)

    directories = [Path(i).resolve() for i in params.directory]

    reducer = SimpleDataReduction(Path.cwd(), directories, 0)
    reducer.run(
        batch_size=params.batch_size,
        nproc=params.nproc,
        anomalous=params.anomalous,
        space_group=params.space_group,
        cluster_threshold=params.clustering.threshold,
        d_min=params.d_min,
    )

    duration = time.time() - start_time
    # write out the time taken in a human readable way
    xia2_logger.info(
        "Processing took %s", time.strftime("%Hh %Mm %Ss", time.gmtime(duration))
    )
