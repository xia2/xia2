from __future__ import absolute_import, division, print_function

import os

from xia2.Applications.xia2_main import write_citations
import xia2.Handlers.Streams
from xia2.Handlers.Streams import Chatter


def run():
    assert os.path.exists("xia2.json")
    from xia2.Schema.XProject import XProject

    xinfo = XProject.from_json(filename="xia2.json")
    Chatter.write(xinfo.get_output())
    write_citations()


if __name__ == "__main__":
    xia2.Handlers.Streams.setup_logging(
        logfile="xia2.print.txt", debugfile="xia2.print-debug.txt"
    )
    run()
