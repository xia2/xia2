# LIBTBX_SET_DISPATCHER_NAME dev.xia2.strategy

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

from xia2.Applications.xia2 import check_environment
from xia2.Applications.xia2 import get_command_line, write_citations, help
from xia2.lib.bits import auto_logfiler


def run():
  try:
    check_environment()
  except exceptions.Exception, e:
    traceback.print_exc(file = open('xia2.error', 'w'))
    Chatter.write('Status: error "%s"' % str(e))

  if len(sys.argv) < 2 or '-help' in sys.argv:
    help()
    sys.exit()

  cwd = os.getcwd()

  try:
    from xia2_main import xia2_main
    xia2_main(stop_after='integrate')
    Chatter.write('Status: normal termination')
    from xia2.Handlers.Flags import Flags
    if Flags.get_egg():
      from xia2.lib.bits import message
      message('xia2 status normal termination')

    wd = os.path.join(cwd, 'strategy')
    if not os.path.exists(wd):
      os.mkdir(wd)
    os.chdir(wd)

    CommandLine = get_command_line()
    xinfo = CommandLine.get_xinfo()
    crystals = xinfo.get_crystals()

    assert len(crystals) == 1
    crystal = crystals.values()[0]
    assert len(crystal.get_wavelength_names()) == 1
    wavelength = crystal.get_xwavelength(crystal.get_wavelength_names()[0])
    sweeps = wavelength.get_sweeps()
    for sweep in sweeps:
      integrater = sweep._get_integrater()
      from xia2.Wrappers.Dials.ExportBest import ExportBest
      export = ExportBest()
      export.set_experiments_filename(integrater.get_integrated_experiments())
      export.set_reflections_filename(integrater.get_integrated_reflections())
      export.set_working_directory(wd)
      auto_logfiler(export)
      export.run()
      from xia2.Wrappers.EMBL import Best
      best = Best.BestStrategy()
      best.set_mos_dat('best.dat')
      best.set_mos_par('best.par')
      best.add_mos_hkl('best.hkl')
      best.set_t_ref(0.2)
      best.set_detector('pilatus6m')
      best.set_working_directory(wd)
      auto_logfiler(best)
      best.strategy()

      multiplicity = best.get_multiplicity()
      try:
        mutiplicity = '%.2f' %multiplicity
      except TypeError:
        pass
      print 'Native'
      print 'Start / end / width: %.2f/%.2f/%.2f' % (best.get_phi_start(), best.get_phi_end(), best.get_phi_width())
      print 'Completeness / multiplicity / resolution: %.2f/%s/%.2f' % (best.get_completeness(), multiplicity, best.get_resolution())
      print 'Transmission / exposure %.3f/%.3f' % (best.get_transmission(), best.get_exposure_time())

      best.set_anomalous(True)
      auto_logfiler(best)
      best.strategy()

      multiplicity = best.get_multiplicity()
      try:
        mutiplicity = '%.2f' %multiplicity
      except TypeError:
        pass
      print 'Anomalous'
      print 'Start / end / width: %.2f/%.2f/%.2f' % (best.get_phi_start(), best.get_phi_end(), best.get_phi_width())
      print 'Completeness / multiplicity / resolution: %.2f/%s/%.2f' % (best.get_completeness(), multiplicity, best.get_resolution())
      print 'Transmission / exposure %.3f/%.3f' % (best.get_transmission(), best.get_exposure_time())

  except exceptions.Exception, e:
    traceback.print_exc(file = open(os.path.join(cwd, 'xia2.error'), 'w'))
    Chatter.write('Status: error "%s"' % str(e))
    from xia2.Handlers.Flags import Flags
    if Flags.get_egg():
      from xia2.lib.bits import message
      message('xia2 status error %s' % str(e))
  os.chdir(cwd)

if __name__ == '__main__':
  run()

