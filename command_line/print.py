from __future__ import absolute_import, division

import os

# Needed to make xia2 imports work correctly
import libtbx.load_env
from xia2.Applications.xia2_main import write_citations
from xia2.Handlers.Streams import Chatter, Debug

def run():
  assert os.path.exists('xia2.json')
  from xia2.Schema.XProject import XProject
  xinfo = XProject.from_json(filename='xia2.json')
  Chatter.write(xinfo.get_output())
  write_citations()

if __name__ == '__main__':
  run()
