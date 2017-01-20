from __future__ import absolute_import, division
import libtbx.load_env

def ispyb_xml(xml_out):
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
  ISPyBXmlHandler.write_xml(xml_out, command_line)

if __name__ == '__main__':
  import sys
  if len(sys.argv) >= 2:
    ispyb_xml(sys.argv[1])
  else:
    ispyb_xml('ispyb.xml')
