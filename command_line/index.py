from __future__ import absolute_import, division, print_function

import os
import sys
import traceback

from xia2.Applications.xia2_main import check_environment, help
import xia2.Handlers.Streams
from xia2.Handlers.Streams import Chatter


def run():
    try:
        check_environment()
    except Exception as e:
        with open("xia2-error.txt", "w") as fh:
            traceback.print_exc(file=fh)
        Chatter.write('Status: error "%s"' % str(e))

    if len(sys.argv) < 2 or "-help" in sys.argv:
        help()
        sys.exit()

    wd = os.getcwd()

    try:
        # xia2_index()
        from xia2.command_line.xia2_main import xia2_main

        xia2_main(stop_after="index")
        Chatter.write("Status: normal termination")

    except Exception as e:
        with open(os.path.join(wd, "xia2-error.txt"), "w") as fh:
            traceback.print_exc(file=fh)
        Chatter.write('Status: error "%s"' % str(e))


if __name__ == "__main__":
    xia2.Handlers.Streams.setup_logging(
        logfile="xia2.index.txt", debugfile="xia2.index-debug.txt"
    )
    run()
