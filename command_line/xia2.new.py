# LIBTBX_SET_DISPATCHER_NAME xia2.new

import sys
import os
import math
import time
import exceptions
import traceback

# Needed to make xia2 imports work correctly
import libtbx.load_env
xia2_root_dir = libtbx.env.find_in_repositories("xia2")
sys.path.insert(0, xia2_root_dir)
os.environ['XIA2_ROOT'] = xia2_root_dir
os.environ['XIA2CORE_ROOT'] = os.path.join(xia2_root_dir, "core")

from Handlers.Streams import Chatter, Debug

from Handlers.Files import cleanup
from Handlers.Citations import Citations
from Handlers.Environment import Environment, df

from XIA2Version import Version

# XML Marked up output for e-HTPX
if not os.path.join(os.environ['XIA2_ROOT'], 'Interfaces') in sys.path:
  sys.path.append(os.path.join(os.environ['XIA2_ROOT'], 'Interfaces'))

from xia2.Applications.xia2setup import write_xinfo
from xia2.Applications.xia2 import check, check_cctbx_version, check_environment
from xia2.Applications.xia2 import get_command_line, write_citations, help

def xia2():
  '''Actually process something...'''

  from Handlers.Flags import Flags
  Flags.set_serialize_state(True)

  # print the version
  Chatter.write(Version)
  Citations.cite('xia2')

  start_time = time.time()

  CommandLine = get_command_line()

  # check that something useful has been assigned for processing...
  xtals = CommandLine.get_xinfo().get_crystals()

  no_images = True

  for name in xtals.keys():
    xtal = xtals[name]

    if not xtal.get_all_image_names():

      Chatter.write('-----------------------------------' + \
                    '-' * len(name))
      Chatter.write('| No images assigned for crystal %s |' % name)
      Chatter.write('-----------------------------------' + '-' \
                    * len(name))
    else:
      no_images = False

  # this actually gets the processing started...
  xinfo = CommandLine.get_xinfo()
  crystals = xinfo.get_crystals()
  for crystal_id in crystals.keys():
    for wavelength_id in crystals[crystal_id].get_wavelength_names():
      wavelength = crystals[crystal_id].get_xwavelength(wavelength_id)
      sweeps = wavelength.get_sweeps()
      for sweep in sweeps:
        sweep.get_integrater_intensities()
        sweep.serialize()
  Chatter.write(xinfo.get_output())

  duration = time.time() - start_time

  # write out the time taken in a human readable way
  Chatter.write('Processing took %s' % \
                time.strftime("%Hh %Mm %Ss", time.gmtime(duration)))

  # delete all of the temporary mtz files...
  cleanup()

  # maybe write out the headers
  from Handlers.Flags import Flags
  if Flags.get_hdr_out():
    from Wrappers.XIA.Diffdump import HeaderCache
    HeaderCache.write(Flags.get_hdr_out())

  # and the summary file
  summary_records = CommandLine.get_xinfo().summarise()

  fout = open('xia2-summary.dat', 'w')
  for record in summary_records:
    fout.write('%s\n' % record)
  fout.close()

  write_citations()

  Environment.cleanup()

  return

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
    xia2()
    Chatter.write('Status: normal termination')
    from Handlers.Flags import Flags
    if Flags.get_egg():
      from lib.bits import message
      message('xia2 status normal termination')

  except exceptions.Exception, e:
    traceback.print_exc(file = open(os.path.join(wd, 'xia2.error'), 'w'))
    Chatter.write('Status: error "%s"' % str(e))
    from Handlers.Flags import Flags
    if Flags.get_egg():
      from lib.bits import message
      message('xia2 status error %s' % str(e))

if __name__ == '__main__':
  run()
