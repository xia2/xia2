# LIBTBX_SET_DISPATCHER_NAME dev.xia2.strategy
# LIBTBX_SET_DISPATCHER_NAME xia2.strategy

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

    from xia2.Handlers.Phil import PhilIndex
    params = PhilIndex.get_python_object()
    strategy_params = params.strategy
    if not len(strategy_params):
      strategy_params = [PhilIndex.get_scope_by_name('strategy')[0].extract()]

    from dxtbx.model import MultiAxisGoniometer
    gonio = sweeps[0].get_imageset().get_goniometer()
    if (isinstance(gonio, MultiAxisGoniometer) and
        len(gonio.get_axes()) == 3 and gonio.get_scan_axis() == 2):
      from xia2.Wrappers.Dials.AlignCrystal import AlignCrystal
      align_crystal = AlignCrystal()
      align_crystal.set_experiments_filename(
        sweeps[0]._get_integrater().get_integrated_experiments())
      align_crystal.set_working_directory(wd)
      auto_logfiler(align_crystal)
      align_crystal.set_json_filename(
        '%i_align_crystal.json' %align_crystal.get_xpid())
      align_crystal.run()
      Chatter.write("".join(align_crystal.get_all_output()))

    for istrategy, strategy in enumerate(strategy_params):
      from xia2.Wrappers.EMBL import Best
      best = Best.BestStrategy()
      for isweep, sweep in enumerate(sweeps):
        integrater = sweep._get_integrater()
        from xia2.Wrappers.Dials.ExportBest import ExportBest
        export = ExportBest()
        export.set_experiments_filename(integrater.get_integrated_experiments())
        export.set_reflections_filename(integrater.get_integrated_reflections())
        export.set_working_directory(wd)
        auto_logfiler(export)
        prefix = '%i_best' %export.get_xpid()
        export.set_prefix(prefix)
        export.run()
        if isweep == 0:
          imageset = sweep.get_imageset()
          scan = imageset.get_scan()
          best.set_t_ref(scan.get_exposure_times()[0])
          best.set_mos_dat('%s.dat' %prefix)
          best.set_mos_par('%s.par' %prefix)
        best.add_mos_hkl('%s.hkl' %prefix)
      best.set_i2s(strategy.i_over_sigi)
      best.set_T_max(strategy.max_total_exposure)
      best.set_t_min(strategy.min_exposure)
      #best.set_trans_ref(25.0)
      best.set_S_max(strategy.max_rotation_speed)
      best.set_w_min(strategy.min_oscillation_width)
      best.set_M_min(strategy.multiplicity)
      best.set_C_min(strategy.completeness)
      best.set_anomalous(strategy.anomalous)

      best.set_detector('pilatus6m')
      best.set_working_directory(wd)
      auto_logfiler(best)
      xmlout = '%s/%i_best.xml' %(best.get_working_directory(), best.get_xpid())
      best.set_xmlout(xmlout)
      best.strategy()

      multiplicity = best.get_multiplicity()
      try:
        mutiplicity = '%.2f' %multiplicity
      except TypeError:
        pass
      Chatter.write('Strategy %i' %istrategy)
      Chatter.write('Start / end / width: %.2f/%.2f/%.2f' % (best.get_phi_start(), best.get_phi_end(), best.get_phi_width()))
      Chatter.write('Completeness / multiplicity / resolution: %.2f/%s/%.2f' % (best.get_completeness(), multiplicity, best.get_resolution()))
      Chatter.write('Transmission / exposure %.3f/%.3f' % (best.get_transmission(), best.get_exposure_time()))
      Chatter.write('XML: %s' %xmlout)

  except exceptions.Exception, e:
    traceback.print_exc(file = open(os.path.join(cwd, 'xia2.error'), 'w'))
    Chatter.write('Status: error "%s"' % str(e))
  os.chdir(cwd)

if __name__ == '__main__':
  run()

