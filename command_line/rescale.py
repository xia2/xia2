from __future__ import absolute_import, division, print_function

import os
import sys
import time
import traceback

from libtbx import Auto

from xia2.Applications.xia2_main import check_environment, write_citations
from xia2.Handlers.Citations import Citations
from xia2.Handlers.Environment import Environment
from xia2.Handlers.Files import cleanup
from xia2.Handlers.Phil import PhilIndex
from xia2.Handlers.Streams import Chatter
from xia2.XIA2Version import Version


def run():
    if os.path.exists("xia2-working.phil"):
        sys.argv.append("xia2-working.phil")
    try:
        check_environment()
    except Exception as e:
        with open("xia2.error", "w") as fh:
            traceback.print_exc(file=fh)
        Chatter.write('Status: error "%s"' % str(e))

    # print the version
    Chatter.write(Version)
    Citations.cite("xia2")

    start_time = time.time()

    assert os.path.exists("xia2.json")
    from xia2.Schema.XProject import XProject

    xinfo = XProject.from_json(filename="xia2.json")

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

        Chatter.write(xinfo.get_output())
        crystal.serialize()

    duration = time.time() - start_time

    # write out the time taken in a human readable way
    Chatter.write(
        "Processing took %s" % time.strftime("%Hh %Mm %Ss", time.gmtime(duration))
    )

    # delete all of the temporary mtz files...
    cleanup()

    write_citations()

    xinfo.as_json(filename="xia2.json")

    Environment.cleanup()


if __name__ == "__main__":
    run()
