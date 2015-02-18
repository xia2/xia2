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

from Handlers.Flags import Flags
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

from xia2.Applications.xia2_helpers import process_one_sweep


def xia2(stop_after=None):
  '''Actually process something...'''

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

  args = []

  from Handlers.Phil import PhilIndex
  params = PhilIndex.get_python_object()
  mp_params = params.xia2.settings.multiprocessing
  njob = mp_params.njob

  from libtbx import group_args

  # this actually gets the processing started...
  xinfo = CommandLine.get_xinfo()
  crystals = xinfo.get_crystals()

  if njob > 1:
    driver_type = mp_params.type
    for crystal_id in crystals.keys():
      for wavelength_id in crystals[crystal_id].get_wavelength_names():
        wavelength = crystals[crystal_id].get_xwavelength(wavelength_id)
        sweeps = wavelength.get_sweeps()
        for sweep in sweeps:
          sweep._get_indexer()
          sweep._get_refiner()
          sweep._get_integrater()
          args.append((
            group_args(
              driver_type=driver_type,
              stop_after=stop_after,
              failover=Flags.get_failover(),
              command_line_args=CommandLine.get_argv()[1:],
              nproc=mp_params.nproc,
              crystal_id=crystal_id,
              wavelength_id=wavelength_id,
              sweep_id=sweep.get_name(),
              ),))

    if mp_params.type == "qsub":
      method = "sge"
    else:
      method = "multiprocessing"
    nproc = mp_params.nproc
    qsub_command = mp_params.qsub_command
    if not qsub_command:
      qsub_command = 'qsub'
    qsub_command = '%s -V -cwd -pe smp %d' %(qsub_command, nproc)

    from libtbx import easy_mp
    results = easy_mp.parallel_map(
      process_one_sweep, args, processes=njob,
      #method=method,
      method="multiprocessing",
      qsub_command=qsub_command,
      preserve_order=True,
      preserve_exception_message=True)

    # Hack to update sweep with the serialized indexers/refiners/integraters
    i_sweep = 0
    for crystal_id in crystals.keys():
      for wavelength_id in crystals[crystal_id].get_wavelength_names():
        wavelength = crystals[crystal_id].get_xwavelength(wavelength_id)
        remove_sweeps = []
        sweeps = wavelength.get_sweeps()
        for sweep in sweeps:
          success, output = results[i_sweep]
          if output is not None:
            Chatter.write(output)
          if not success:
            print "Sweep failed: removing %s" %sweep.get_name()
            remove_sweeps.append(sweep)
          else:
            print "Loading sweep: %s" %sweep.get_name()
            sweep._indexer = None
            sweep._refiner = None
            sweep._integrater = None
            sweep._get_indexer()
            sweep._get_refiner()
            sweep._get_integrater()
          i_sweep += 1
        for sweep in remove_sweeps:
          wavelength.remove_sweep(sweep)

    # switch off parallel mode so that old-style parallelisation doesn't kick in
    mp_params.njob = 1
    mp_params.mode = "serial"

  else:
    for crystal_id in crystals.keys():
      for wavelength_id in crystals[crystal_id].get_wavelength_names():
        wavelength = crystals[crystal_id].get_xwavelength(wavelength_id)
        sweeps = wavelength.get_sweeps()
        for sweep in sweeps:
          try:
            if stop_after == 'index':
              sweep.get_indexer_cell()
            else:
              sweep.get_integrater_intensities()
            sweep.serialize()
          except Exception, e:
            if Flags.get_failover():
              Chatter.write('Processing sweep %s failed: %s' % \
                            (sweep.get_name(), str(e)))
              wavelength.remove_sweep(sweep)
            else:
              raise

  if stop_after not in ('index', 'integrate'):
    Chatter.write(xinfo.get_output())

  for crystal in crystals.values():
    crystal.serialize()

  duration = time.time() - start_time

  # write out the time taken in a human readable way
  Chatter.write('Processing took %s' % \
                time.strftime("%Hh %Mm %Ss", time.gmtime(duration)))

  # delete all of the temporary mtz files...
  cleanup()

  # maybe write out the headers
  if Flags.get_hdr_out():
    from Wrappers.XIA.Diffdump import HeaderCache
    HeaderCache.write(Flags.get_hdr_out())

  if stop_after not in ('index', 'integrate'):
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
    Chatter.write(
      'Please send the contents of xia2.txt, xia2.error and xia2-debug.txt to:')
    Chatter.write('xia2.support@gmail.com')
    from Handlers.Flags import Flags
    if Flags.get_egg():
      from lib.bits import message
      message('xia2 status error %s' % str(e))

if __name__ == '__main__':
  run()
