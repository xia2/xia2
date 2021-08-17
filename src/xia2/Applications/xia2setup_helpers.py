import logging
import os
import traceback

from xia2.Schema.Sweep import SweepFactory

# this must be defined in a separate file from xia2setup.py to be
# compatible with easy_mp.parallel_map with method="sge" when
# xia2setup.py is run as the __main__ program.
def get_sweep(args):
    assert len(args) == 1
    directory, template = os.path.split(args[0])

    try:
        sweeplist = SweepFactory(template, directory)

    except Exception as e:
        logger = logging.getLogger("xia2.Applications.xia2setup_helpers")
        logger.debug("Exception C: %s (%s)" % (str(e), args[0]))
        logger.debug(traceback.format_exc())
        return None

    return sweeplist
