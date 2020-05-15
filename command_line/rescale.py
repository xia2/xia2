import logging
import os
import sys
import time
import traceback

from libtbx import Auto
import xia2.Handlers.Streams
from xia2.Applications.xia2_main import check_environment, write_citations
from xia2.Handlers.Citations import Citations
from xia2.Handlers.Files import cleanup
from xia2.Handlers.Phil import PhilIndex
from xia2.XIA2Version import Version

logger = logging.getLogger("xia2.command_line.rescale")


def run():
    if os.path.exists("xia2-working.phil"):
        sys.argv.append("xia2-working.phil")
    try:
        check_environment()
    except Exception as e:
        with open("xia2-error.txt", "w") as fh:
            traceback.print_exc(file=fh)
        logger.error('Status: error "%s"', str(e))

    # print the version
    logger.info(Version)
    Citations.cite("xia2")

    start_time = time.time()

    assert os.path.exists("xia2.json")
    from xia2.Schema.XProject import XProject

    xinfo = XProject.from_json(filename="xia2.json")

    with cleanup(xinfo.path):
        crystals = xinfo.get_crystals()
        for crystal_id, crystal in crystals.items():
            scale_dir = PhilIndex.params.xia2.settings.scale.directory
            if scale_dir is Auto:
                scale_dir = "scale"
                i = 0
                while os.path.exists(os.path.join(crystal.get_name(), scale_dir)):
                    i += 1
                    scale_dir = "scale%i" % i
                PhilIndex.params.xia2.settings.scale.directory = scale_dir

            # reset scaler
            crystals[crystal_id]._scaler = None
            crystal._get_scaler()

            logger.info(xinfo.get_output())
            crystal.serialize()

        duration = time.time() - start_time

        # write out the time taken in a human readable way
        logger.info(
            "Processing took %s", time.strftime("%Hh %Mm %Ss", time.gmtime(duration))
        )

        write_citations()

        xinfo.as_json(filename="xia2.json")


if __name__ == "__main__":
    xia2.Handlers.Streams.setup_logging(
        logfile="xia2.rescale.txt", debugfile="xia2.rescale-debug.txt"
    )
    run()
