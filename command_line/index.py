# LIBTBX_SET_DISPATCHER_NAME xia2.index
from __future__ import absolute_import, division

import sys
import os
import exceptions
import traceback

# Needed to make xia2 imports work correctly
import libtbx.load_env
from xia2.Handlers.Streams import Chatter, Debug

from xia2.Applications.xia2_main import check_environment, help


def run():
  try:
    check_environment()
  except exceptions.Exception, e:
    traceback.print_exc(file = open('xia2.error', 'w'))
    Chatter.write('Status: error "%s"' % str(e))

  if len(sys.argv) < 2 or '-help' in sys.argv:
    help()
    sys.exit()

  wd = os.getcwd()

  try:
    #xia2_index()
    from xia2.command_line.xia2_main import xia2_main
    xia2_main(stop_after='index')
    Chatter.write('Status: normal termination')

  except exceptions.Exception, e:
    traceback.print_exc(file = open(os.path.join(wd, 'xia2.error'), 'w'))
    Chatter.write('Status: error "%s"' % str(e))

if __name__ == '__main__':
  run()
