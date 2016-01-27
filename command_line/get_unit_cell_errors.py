import sys
import os
import math
import exceptions
import traceback
import re
# Needed to make xia2 imports work correctly
import libtbx.load_env
xia2_root_dir = libtbx.env.find_in_repositories("xia2", optional=False)
sys.path.insert(0, xia2_root_dir)
os.environ['XIA2_ROOT'] = xia2_root_dir
os.environ['XIA2CORE_ROOT'] = os.path.join(xia2_root_dir, "core")

from Handlers.Streams import Chatter, Debug

from Handlers.Files import cleanup
from Handlers.Citations import Citations
from Handlers.Environment import Environment
from lib.bits import auto_logfiler

# XML Marked up output for e-HTPX
if not os.path.join(os.environ['XIA2_ROOT'], 'Interfaces') in sys.path:
  sys.path.append(os.path.join(os.environ['XIA2_ROOT'], 'Interfaces'))

from Applications.xia2setup import write_xinfo
from Applications.xia2 import check, check_cctbx_version, check_environment
from Applications.xia2 import get_command_line, write_citations, help


def get_unit_cell_errors(stop_after=None):
  '''Actually process something...'''

  assert os.path.exists('xia2.json')
  from Schema.XProject import XProject
  xinfo = XProject.from_json(filename='xia2.json')

  from Wrappers.Dials.CombineExperiments import CombineExperiments
  from Wrappers.Dials.Reindex import Reindex
  from lib.bits import auto_logfiler
  Citations.cite('dials')

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

    # Aimless only
    epochs = scaler._sweep_handler.get_epochs()

    reference_vectors = None
    reindexed_reflections = []

    dials_combine = CombineExperiments()

    dials_combine.set_experimental_model(
      same_beam=True,
#     same_crystal=True,
      same_crystal=False,
      same_detector=False,
      same_goniometer=False)

    # Reindex each sweep to same setting
    Chatter.write('Reindexing experiments')

    for epoch in epochs:
        si = scaler._sweep_handler.get_sweep_information(epoch)
        intgr = si.get_integrater()
        refiner = intgr.get_integrater_refiner()
#        print intgr
#        print refiner

        if reference_vectors is None:
          reference_vectors = refiner.get_refiner_payload("experiments.json")
        _reflections_filename = refiner.get_refiner_payload("reflections.pickle")
        print _reflections_filename

        dials_reindex = Reindex()
        dials_reindex.set_working_directory(working_directory)
        dials_reindex.set_cb_op("auto")
        dials_reindex.set_experiments_filename(reference_vectors)
        dials_reindex.set_indexed_filename(_reflections_filename)
        auto_logfiler(dials_reindex)
        dials_reindex.run()

        dials_combine.add_experiments(refiner.get_refiner_payload("experiments.json"))
        dials_combine.add_reflections(dials_reindex.get_reindexed_reflections_filename())

    # joint refinement of n sweeps, but with separate A matrices,
    # to obtain n unit cell uncertainties
    auto_logfiler(dials_combine)
    Chatter.write("Combining experiments")
    dials_combine.run()

    from Wrappers.Dials.Refine import Refine
    dials_refine = Refine()
    dials_refine.set_experiments_filename(dials_combine.get_combined_experiments_filename())
    dials_refine.set_indexed_filename(dials_combine.get_combined_reflections_filename())
    dials_refine.set_use_all_reflections(True)
    auto_logfiler(dials_refine)
    Chatter.write("Running joint refinement")
    dials_refine.run()

    Chatter.write("")
    match_esd_header = re.compile('Crystal ([0-9]+) refined cell parameters and estimated standard deviations')
    match_esd = re.compile(' (a|b|c|alpha|beta|gamma): +([0-9]+\.[0-9]+) [^0-9]+([0-9]+\.[0-9]+)\)')

    match_nref_header = re.compile('RMSDs by experiment:')
    match_nref = re.compile('\| ([0-9]+) *\| ([0-9]+) *\|')

    esd = {}
    with open('dials.refine.debug.log') as reflog:
      dials_log = reflog.readlines()
      for n in range(len(dials_log)):
        result = match_esd_header.match(dials_log[n])
        if result:
          crystal_id = result.group(1)
          Chatter.write("ESD %s" % crystal_id)
          esd[crystal_id] = {}
          for i in range(6):
            result = match_esd.match(dials_log[n + i + 1])
            if result:
              Chatter.write("%s: %s (+/- %s)" % (result.group(1, 2, 3)))
              esd[crystal_id][result.group(1)] = (float(result.group(2)), float(result.group(3)))
          Chatter.write("")

        if match_nref_header.match(dials_log[n]):
          i = 5
          result = match_nref.match(dials_log[n + i])
          nref_total = 0
          while result:
            Chatter.write("Found %s reflections for experiment %s" % (result.group(2,1)))
#            esd[result.group(1)]['nref'] = int(result.group(2))
            nref_total = nref_total + int(result.group(2))
            i = i + 1
            result = match_nref.match(dials_log[n + i])
          Chatter.write("Total number of reflections: %d" % nref_total)
          Chatter.write("")

    Chatter.write("Weighted estimated standard deviations:")
    for value in ['a', 'b', 'c', 'alpha', 'beta', 'gamma']:
      [x, sd] = zip(*[e[value] for e in esd.itervalues()])
      if any([v == 0 for v in sd]):
        # If any values with 0 variance present, average all values with 0 variance
        est_value = sum([i for i, v in zip(x, sd) if v == 0])
        est_value = est_value / sum([v == 0 for v in sd])
        est_sigma = 0
      else:
        weights = [ 1 / (v * v) for v in sd ]
        est_value = sum([ i * w for i, w in zip(x, weights) ])
        est_value = est_value / sum(weights)
        est_sigma = math.sqrt(1 / sum(weights))

      print "%8s: %10.6f (+/- %f)" % (value, est_value, est_sigma)

#   Chatter.write(str(esd))
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
