from __future__ import absolute_import, division
import libtbx.load_env

def ispyb_json(json_out):
  from xia2.Interfaces.ISPyB.ISPyBXmlHandler import ISPyBXmlHandler
  import os
  assert os.path.exists('xia2.json')
  assert os.path.exists('xia2.txt')
  command_line = ''
  for record in open('xia2.txt'):
    if record.startswith('Command line:'):
      command_line = record.replace('Command line:', '').strip()
  from xia2.Schema.XProject import XProject
  xinfo = XProject.from_json(filename='xia2.json')
  crystals = xinfo.get_crystals()
  assert len(crystals) == 1
  crystal = next(crystals.itervalues())
  ISPyBXmlHandler.add_xcrystal(crystal)
  import json
  json.dump(ISPyBXmlHandler.json_object(command_line=command_line),
            open(json_out, 'w'))

if __name__ == '__main__':
  import sys
  if len(sys.argv) >= 2:
    ispyb_json(sys.argv[1])
  else:
    ispyb_json('ispyb.json')
