# LIBTBX_SET_DISPATCHER_NAME xia2.index

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

from xia2.XIA2Version import Version

from xia2.Applications.xia2 import check, check_cctbx_version, check_environment
from xia2.Applications.xia2 import get_command_line, write_citations, help


def run():
  try:
    check_environment()
    check()
  except exceptions.Exception, e:
    traceback.print_exc(file = open('xia2.error', 'w'))
    Chatter.write('Status: error "%s"' % str(e))

  if len(sys.argv) < 2 or '-help' in sys.argv:
    help()
    sys.exit()

  wd = os.getcwd()

  try:
    #xia2_index()
    from xia2_main import xia2_main
    xia2_main(stop_after='index')
    Chatter.write('Status: normal termination')
    from xia2.Handlers.Flags import Flags
    if Flags.get_egg():
      from xia2.lib.bits import message
      message('xia2 status normal termination')

  except exceptions.Exception, e:
    traceback.print_exc(file = open(os.path.join(wd, 'xia2.error'), 'w'))
    Chatter.write('Status: error "%s"' % str(e))
    from xia2.Handlers.Flags import Flags
    if Flags.get_egg():
      from xia2.lib.bits import message
      message('xia2 status error %s' % str(e))

if __name__ == '__main__':
  run()
