import logging
import os
import sys
import traceback

from xia2.Applications.xia2_main import check_environment, help
import xia2.Handlers.Streams

logger = logging.getLogger("xia2.command_line.integrate")


def run():
    try:
        check_environment()
    except Exception as e:
        with open("xia2-error.txt", "w") as fh:
            traceback.print_exc(file=fh)
        logger.error('Status: error "%s"', str(e))
        sys.exit(1)

    if len(sys.argv) < 2 or "-help" in sys.argv:
        help()
        sys.exit()

    wd = os.getcwd()

    try:
        from xia2.command_line.xia2_main import xia2_main

        xia2_main(stop_after="integrate")
        logger.info("Status: normal termination")

    except Exception as e:
        with open(os.path.join(wd, "xia2-error.txt"), "w") as fh:
            traceback.print_exc(file=fh)
        logger.error('Status: error "%s"', str(e))
        sys.exit(1)


if __name__ == "__main__":
    xia2.Handlers.Streams.setup_logging(
        logfile="xia2.integrate.txt", debugfile="xia2.integrate-debug.txt"
    )
    run()
