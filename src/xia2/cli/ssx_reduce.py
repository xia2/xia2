from __future__ import annotations

import logging
import sys
from pathlib import Path

from dials.util import log
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

logger = logging.getLogger("dials")


def run(args=sys.argv[1:]):

    parser = ArgumentParser(
        usage="xia2.ssx_reduce directory=/path/to/integrated/directory/",
        read_experiments=False,
        read_reflections=False,
        phil=phil_scope,
        check_format=False,
        epilog="",
    )
    params, options = parser.parse_args(args=args, show_diff_phil=False)
    log.config(verbosity=options.verbose, logfile="xia2.ssx_reduce.log")
    diff_phil = parser.diff_phil.as_str()
    if diff_phil:
        logger.info("The following parameters have been modified:\n%s", diff_phil)

    directories = [Path(i).resolve() for i in params.directory]

    reducer = SimpleDataReduction(Path.cwd(), directories, 0)
    reducer.run(
        batch_size=params.batch_size,
        nproc=params.nproc,
        anomalous=params.anomalous,
        space_group=str(params.space_group),
        cluster_threshold=params.clustering.threshold,
        d_min=params.d_min,
    )
