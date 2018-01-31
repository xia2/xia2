# LIBTBX_SET_DISPATCHER_NAME xia2.integrate

from __future__ import absolute_import, division

import os
import sys
import traceback

# Needed to make xia2 imports work correctly
import libtbx.load_env
from xia2.Applications.xia2_main import check_environment, help
from xia2.Handlers.Streams import Chatter, Debug

def run():
  try:
    check_environment()
  except Exception as e:
    traceback.print_exc(file = open('xia2.error', 'w'))
    Chatter.write('Status: error "%s"' % str(e))

  if len(sys.argv) < 2 or '-help' in sys.argv:
    help()
    sys.exit()

  wd = os.getcwd()

  try:
    from xia2.command_line.xia2_main import xia2_main
    xia2_main(stop_after='integrate')
    Chatter.write('Status: normal termination')

  except Exception as e:
    traceback.print_exc(file = open(os.path.join(wd, 'xia2.error'), 'w'))
    Chatter.write('Status: error "%s"' % str(e))

if __name__ == '__main__':
  run()
