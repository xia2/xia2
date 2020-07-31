import logging
import os
import sys
import traceback

from dials.util import Sorry
from dials.util.version import dials_version
import xia2.Driver.timing
import xia2.Handlers.Streams
import xia2.XIA2Version
from xia2.Applications.xia2_main import (
    check_environment,
    get_command_line,
    help,
)
from xia2.command_line.xia2_main import get_ccp4_version
from xia2.Handlers.Citations import Citations

logger = logging.getLogger("xia2.command_line.setup")


def xia2_setup():
    """Actually process something..."""
    Citations.cite("xia2")

    # print versions of related software
    logger.info(dials_version())

    ccp4_version = get_ccp4_version()
    if ccp4_version:
        logger.info("CCP4 %s", ccp4_version)

    CommandLine = get_command_line()

    # check that something useful has been assigned for processing...
    xtals = CommandLine.get_xinfo().get_crystals()

    for name, xtal in xtals.items():
        if not xtal.get_all_image_names():
            logger.info("-----------------------------------" + "-" * len(name))
            logger.info("| No images assigned for crystal %s |", name)
            logger.info("-----------------------------------" + "-" * len(name))

    from xia2.Handlers.Phil import PhilIndex

    params = PhilIndex.get_python_object()
    xinfo = CommandLine.get_xinfo()
    logger.info(f"Project directory: {xinfo.path}")
    logger.info(f"xinfo written to: {params.xia2.settings.input.xinfo}")
    logger.info(f"Parameters: {PhilIndex.get_diff().as_str()}")


def run():
    if len(sys.argv) < 2 or "-help" in sys.argv or "--help" in sys.argv:
        help()
        sys.exit()

    if "-version" in sys.argv or "--version" in sys.argv:
        print(xia2.XIA2Version.Version)
        print(dials_version())
        ccp4_version = get_ccp4_version()
        if ccp4_version:
            print("CCP4 %s" % ccp4_version)
        sys.exit()

    xia2.Handlers.Streams.setup_logging(logfile="xia2.txt", debugfile="xia2-debug.txt")

    try:
        check_environment()
    except Exception as e:
        traceback.print_exc(file=open("xia2-error.txt", "w"))
        logger.debug(traceback.format_exc())
        logger.error("Error setting up xia2 environment: %s" % str(e))
        logger.warning(
            "Please send the contents of xia2.txt, xia2-error.txt and xia2-debug.txt to:"
        )
        logger.warning("xia2.support@gmail.com")
        sys.exit(1)

    wd = os.getcwd()

    try:
        xia2_setup()
    except Sorry as s:
        logger.error("Error: %s", str(s))
        sys.exit(1)
    except Exception as e:
        with open(os.path.join(wd, "xia2-error.txt"), "w") as fh:
            traceback.print_exc(file=fh)
        logger.debug(traceback.format_exc())
        logger.error("Error: %s", str(e))
        logger.warning(
            "Please send the contents of xia2.txt, xia2-error.txt and xia2-debug.txt to:"
        )
        logger.warning("xia2.support@gmail.com")
        sys.exit(1)


if __name__ == "__main__":
    run()
