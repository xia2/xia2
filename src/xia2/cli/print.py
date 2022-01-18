from __future__ import annotations

import logging
import os

import xia2.Handlers.Streams
from xia2.Applications.xia2_main import write_citations

logger = logging.getLogger("xia2.cli.print")


def run():
    assert os.path.exists("xia2.json")
    from xia2.Schema.XProject import XProject

    xinfo = XProject.from_json(filename="xia2.json")
    logger.info(xinfo.get_output())
    write_citations()


def run_with_log():
    xia2.Handlers.Streams.setup_logging(
        logfile="xia2.print.txt", debugfile="xia2.print-debug.txt"
    )
    run()
