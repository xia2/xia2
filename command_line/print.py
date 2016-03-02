import sys
import os
import math
import time
import exceptions
import traceback

# Needed to make xia2 imports work correctly
import libtbx.load_env
from xia2.Handlers.Streams import Chatter, Debug

from xia2.Handlers.Files import cleanup
from xia2.Handlers.Citations import Citations
from xia2.Handlers.Environment import Environment, df

from xia2.Applications.xia2 import get_command_line, write_citations, help

def run():
  assert os.path.exists('xia2.json')
  from xia2.Schema.XProject import XProject
  xinfo = XProject.from_json(filename='xia2.json')
  Chatter.write(xinfo.get_output())
  write_citations()

if __name__ == '__main__':
  run()
