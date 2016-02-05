# LIBTBX_SET_DISPATCHER_NAME xia2.rescale

import sys
import os
import math
import time
import exceptions
import traceback

# Needed to make xia2 imports work correctly
import libtbx.load_env
xia2_root_dir = libtbx.env.find_in_repositories("xia2", optional=False)
sys.path.insert(0, xia2_root_dir)
os.environ['XIA2_ROOT'] = xia2_root_dir
os.environ['XIA2CORE_ROOT'] = os.path.join(xia2_root_dir, "core")

from Handlers.Streams import Chatter, Debug
from Handlers.Phil import PhilIndex

from Handlers.Files import cleanup
from Handlers.Citations import Citations
from Handlers.Environment import Environment, df

from XIA2Version import Version

# XML Marked up output for e-HTPX
if not os.path.join(os.environ['XIA2_ROOT'], 'Interfaces') in sys.path:
  sys.path.append(os.path.join(os.environ['XIA2_ROOT'], 'Interfaces'))

from Applications.xia2 import check, check_cctbx_version, check_environment
from Applications.xia2 import get_command_line, write_citations, help


def run():
  if os.path.exists('xia2-working.phil'):
    sys.argv.append('xia2-working.phil')
  try:
    check_environment()
    check()
  except exceptions.Exception, e:
    traceback.print_exc(file = open('xia2.error', 'w'))
    Chatter.write('Status: error "%s"' % str(e))

  # print the version
  Chatter.write(Version)
  Citations.cite('xia2')

  start_time = time.time()

  assert os.path.exists('xia2.json')
  from Schema.XProject import XProject
  xinfo = XProject.from_json(filename='xia2.json')

  crystals = xinfo.get_crystals()
  for crystal_id, crystal in crystals.iteritems():
    #cwd = os.path.abspath(os.curdir)
    from libtbx import Auto
    scale_dir = PhilIndex.params.xia2.settings.scale.directory
    if scale_dir is Auto:
      scale_dir = 'scale'
      i = 0
      while os.path.exists(os.path.join(crystal.get_name(), scale_dir)):
        i += 1
        scale_dir = 'scale%i' %i
      PhilIndex.params.xia2.settings.scale.directory = scale_dir
    working_directory = Environment.generate_directory(
      [crystal.get_name(), scale_dir])
    #os.chdir(working_directory)

    crystals[crystal_id]._scaler = None # reset scaler

    scaler = crystal._get_scaler()
    Chatter.write(xinfo.get_output())
    crystal.serialize()

  duration = time.time() - start_time

  # write out the time taken in a human readable way
  Chatter.write('Processing took %s' % \
                time.strftime("%Hh %Mm %Ss", time.gmtime(duration)))

  # delete all of the temporary mtz files...
  cleanup()

  write_citations()

  xinfo.as_json(filename='xia2.json')

  Environment.cleanup()

  return

if __name__ == '__main__':
  run()
