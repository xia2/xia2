from __future__ import absolute_import, division, print_function

import sys

import xia2.Handlers.Streams
from xia2.Modules.DeltaCcHalf import run

if __name__ == "__main__":
    xia2.Handlers.Streams.setup_logging()
    run(sys.argv[1:])
