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

from Handlers.Files import cleanup
from Handlers.Citations import Citations
from Handlers.Environment import Environment, df
from lib.bits import auto_logfiler

from XIA2Version import Version

# XML Marked up output for e-HTPX
if not os.path.join(os.environ['XIA2_ROOT'], 'Interfaces') in sys.path:
  sys.path.append(os.path.join(os.environ['XIA2_ROOT'], 'Interfaces'))

from Applications.xia2setup import write_xinfo
from Applications.xia2 import check, check_cctbx_version, check_environment
from Applications.xia2 import get_command_line, write_citations, help
from xia2.lib.tabulate import tabulate

from scitbx.array_family import flex


def get_unit_cell_errors(stop_after=None):
  '''Actually process something...'''

  assert os.path.exists('xia2.json')
  from Schema.XProject import XProject
  xinfo = XProject.from_json(filename='xia2.json')

  from Wrappers.Dials.CombineExperiments import CombineExperiments
  from Wrappers.Dials.Reindex import Reindex
  from lib.bits import auto_logfiler

  crystals = xinfo.get_crystals()
  for crystal_id, crystal in crystals.iteritems():
    cwd = os.path.abspath(os.curdir)
    working_directory = Environment.generate_directory(
      [crystal.get_name(), 'analysis'])
    os.chdir(working_directory)

    scaler = crystal._get_scaler()

    epoch_to_batches = {}
    epoch_to_integrated_intensities = {}
    epoch_to_sweep_name = {}

    #epoch_to_si = {}
    # Aimless only
    epochs = scaler._sweep_handler.get_epochs()

    reference_vectors = None
    reindexed_reflections = []

    dials_combine = CombineExperiments()

    dials_combine.set_experimental_model(
      same_beam=True,
      same_detector=True, # This may require some more work for the general case
      same_goniometer=False)

    for epoch in epochs:
        si = scaler._sweep_handler.get_sweep_information(epoch)
#        epoch_to_batches[epoch] = si.get_batches()
#        epoch_to_integrated_intensities[epoch] = si.get_reflections()
#        epoch_to_sweep_name[epoch] = si.get_sweep_name()

# check CCP4ScalerA.py
#~line 347 to get the integrater
        intgr = si.get_integrater()
#        hklin = si.get_reflections()
        refiner = intgr.get_integrater_refiner()
#        print intgr
#        print hklin
#        print refiner

# go to DialsIntegrator.py
# ~234
# experiments filename, index filename
# (poss DialsIndexer)
#        _intgr_experiments_filename = refiner.get_refiner_payload("experiments.json")
#        print _intgr_experiments_filename
        if reference_vectors is None:
          reference_vectors = refiner.get_refiner_payload("experiments.json")

#        ## copy the data across
#        from dxtbx.serialize import load
#        experiments = load.experiment_list(_intgr_experiments_filename)
#        experiment = experiments[0]
        _reflections_filename = refiner.get_refiner_payload("reflections.pickle")
        print _reflections_filename

        dials_reindex = Reindex()
        dials_reindex.set_working_directory(working_directory)
        dials_reindex.set_cb_op("auto")
        dials_reindex.set_experiments_filename(reference_vectors)
        dials_reindex.set_indexed_filename(_reflections_filename)
        auto_logfiler(dials_reindex)
        dials_reindex.run()

        dials_combine.add_experiments(reference_vectors)
        dials_combine.add_reflections(dials_reindex.get_reindexed_reflections_filename())
#       Citations.cite('blend')


# TstDialsRefiner.py
# ..?
# ~72

# add multiple exps together
#  
    auto_logfiler(dials_combine)
    dials_combine.run()

    from Wrappers.Dials.Refine import Refine
    dials_refine = Refine()
    dials_refine.set_experiments_filename(dials_combine.get_combined_experiments_filename())
    dials_refine.set_indexed_filename(dials_combine.get_combined_reflections_filename())
    auto_logfiler(dials_refine)
    dials_refine.run()

    print
    with open('dials.refine.debug.log') as reflog:
      dials_log = reflog.readlines()
      model_start = dials_log.index("Final refined crystal model:\n")
      if model_start > 0:
        print "".join(dials_log[model_start:model_start+13])
      errors_start = dials_log.index("Refined cell parameters and estimated standard deviations:\n")
      if errors_start > 0:
        print "".join(dials_log[errors_start:errors_start+7])
  return

def run():
  if os.path.exists('xia2-working.phil'):
    sys.argv.append('xia2-working.phil')
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
    get_unit_cell_errors()
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
    sys.exit(1)

if __name__ == '__main__':
  run()
