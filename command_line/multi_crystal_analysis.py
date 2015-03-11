# LIBTBX_SET_DISPATCHER_NAME xia2.multi_crystal_analysis

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
from lib.bits import auto_logfiler

from XIA2Version import Version

# XML Marked up output for e-HTPX
if not os.path.join(os.environ['XIA2_ROOT'], 'Interfaces') in sys.path:
  sys.path.append(os.path.join(os.environ['XIA2_ROOT'], 'Interfaces'))

from xia2.Applications.xia2setup import write_xinfo
from xia2.Applications.xia2 import check, check_cctbx_version, check_environment
from xia2.Applications.xia2 import get_command_line, write_citations, help

def multi_crystal_analysis(stop_after=None):
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

  for crystal_id, crystal in crystals.iteritems():
    scaler = crystal._get_scaler()
    scaler_working_directory = scaler.get_working_directory()
    json_file = os.path.join(scaler_working_directory, 'xia2.json')
    if (Flags.get_serialize_state() and
        os.path.isdir(scaler_working_directory) and
        os.path.isfile(json_file)):
      scaler = scaler.__class__.from_json(filename=json_file)
      scaler.set_working_directory(scaler_working_directory)
      scaler.set_scaler_xcrystal(crystal)
      crystal._scaler = scaler

  for crystal_id, crystal in crystals.iteritems():
    cwd = os.path.abspath(os.curdir)
    working_directory = Environment.generate_directory(
      [crystal.get_name(), 'analysis'])
    os.chdir(working_directory)

    from Wrappers.CCP4.Blend import Blend

    from lib.bits import auto_logfiler
    hand_blender = Blend()
    hand_blender.set_working_directory(working_directory)
    auto_logfiler(hand_blender)
    Citations.cite('blend')

    scaler = crystal._get_scaler()

    try:
      for epoch, si in scaler._sweep_information.iteritems():
        hand_blender.add_hklin(si['corrected_intensities'])
    except AttributeError, e:
      for epoch in scaler._sweep_handler.get_epochs():
        si = scaler._sweep_handler.get_sweep_information(epoch)
        hand_blender.add_hklin(si.get_reflections())
    finally:
      hand_blender.analysis()
      Chatter.write("Dendrogram saved to: %s" %hand_blender.get_dendrogram_file())
      analysis = hand_blender.get_analysis()
      summary = hand_blender.get_summary()
      clusters = hand_blender.get_clusters()

      linkage_matrix = hand_blender.get_linkage_matrix()
      #print linkage_matrix


  # XXX what about multiple wavelengths?
  with open('batches.phil', 'wb') as f:
    try:
      for epoch, si in scaler._sweep_information.iteritems():
        print >> f, "batch {"
        print >> f, "  id=%s" %si['sname']
        print >> f, "  range=%i,%i" %tuple(si['batches'])
        print >> f, "}"
    except AttributeError, e:
      for epoch in scaler._sweep_handler.get_epochs():
        si = scaler._sweep_handler.get_sweep_information(epoch)
        print >> f, "batch {"
        print >> f, "  id=%s" %si.get_sweep_name()
        print >> f, "  range=%i,%i" %tuple(si.get_batches())
        print >> f, "}"

  #from Modules import MultiCrystalAnalysis
  #MultiCrystalAnalysis.run(
    #[scaler.get_scaled_reflections(format="sca_unmerged").values()[0],
     #"unit_cell=%s %s %s %s %s %s" %tuple(scaler.get_scaler_cell()),
     #"batches.phil"])

  from Wrappers.XIA.MultiCrystalAnalysis import MultiCrystalAnalysis
  mca = MultiCrystalAnalysis()
  auto_logfiler(mca, extra="MultiCrystalAnalysis")
  mca.add_command_line_args(
    [scaler.get_scaled_reflections(format="sca_unmerged").values()[0],
     "unit_cell=%s %s %s %s %s %s" %tuple(scaler.get_scaler_cell()),
     "batches.phil"])
  mca.set_working_directory(working_directory)
  mca.run()

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
    multi_crystal_analysis()
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
