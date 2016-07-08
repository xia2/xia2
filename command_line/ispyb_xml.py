import libtbx.load_env

def ispyb_xml(xml_out):
  from xia2.Interfaces.ISPyB.ISPyBXmlHandler import ISPyBXmlHandler
  import os
  assert os.path.exists('xia2.json')
  from xia2.Schema.XProject import XProject
  xinfo = XProject.from_json(filename='xia2.json')
  crystals = xinfo.get_crystals()
  assert len(crystals) == 1
  crystal = next(crystals.itervalues())
  ISPyBXmlHandler.add_xcrystal(crystal)
  ISPyBXmlHandler.write_xml(xml_out)

if __name__ == '__main__':
  import sys
  ispyb_xml(sys.argv[1])
