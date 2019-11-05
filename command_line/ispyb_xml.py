from __future__ import absolute_import, division, print_function

import os
import iotbx.phil
from xia2.Interfaces.ISPyB.ISPyBXmlHandler import ISPyBXmlHandler
from xia2.Schema.XProject import XProject


def ispyb_xml(xml_out):
    assert os.path.exists("xia2.json")
    assert os.path.exists("xia2.txt")
    assert os.path.exists("xia2-working.phil")
    command_line = ""
    for record in open("xia2.txt"):
        if record.startswith("Command line:"):
            command_line = record.replace("Command line:", "").strip()
    with open("xia2-working.phil", "rb") as f:
        working_phil = iotbx.phil.parse(f.read())
    xinfo = XProject.from_json(filename="xia2.json")
    crystals = xinfo.get_crystals()
    assert len(crystals) == 1
    crystal = next(iter(crystals.values()))
    ISPyBXmlHandler.add_xcrystal(crystal)
    ISPyBXmlHandler.write_xml(xml_out, command_line, working_phil=working_phil)


if __name__ == "__main__":
    import sys

    if len(sys.argv) >= 2:
        ispyb_xml(sys.argv[1])
    else:
        ispyb_xml("ispyb.xml")
