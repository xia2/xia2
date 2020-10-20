import json
import os
import sys

import xia2.Handlers.Streams
import xia2.Interfaces.ISPyB
from xia2.Interfaces.ISPyB.ISPyBXmlHandler import ISPyBXmlHandler
from xia2.Schema.XProject import XProject


def ispyb_object():
    assert os.path.exists("xia2.json")
    assert os.path.exists("xia2.txt")
    command_line = ""
    for record in open("xia2.txt"):
        if record.startswith("Command line:"):
            command_line = record.replace("Command line:", "").strip()
    xinfo = XProject.from_json(filename="xia2.json")
    crystals = xinfo.get_crystals()
    assert len(crystals) == 1
    crystal = next(iter(crystals.values()))
    ispyb_hdl = ISPyBXmlHandler(xinfo)
    ispyb_hdl.add_xcrystal(crystal)
    return ispyb_hdl.json_object(command_line=command_line)


def zocalo_object():
    assert os.path.exists("xia2.json")
    xinfo = XProject.from_json(filename="xia2.json")
    crystals = xinfo.get_crystals()
    assert len(crystals) == 1
    return xia2.Interfaces.ISPyB.xia2_to_json_object(list(crystals.values()))


def ispyb_json(json_out):
    with open(json_out, "w") as fh:
        json.dump(ispyb_object(), fh, indent=2)


if __name__ == "__main__":
    xia2.Handlers.Streams.setup_logging()
    if len(sys.argv) >= 2:
        ispyb_json(sys.argv[1])
    else:
        ispyb_json("ispyb.json")
