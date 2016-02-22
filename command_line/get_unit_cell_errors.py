import exceptions
import json
import math
import os
import random
import sys
import traceback

# Needed to make xia2 imports work correctly
import libtbx.load_env
xia2_root_dir = libtbx.env.find_in_repositories("xia2", optional=False)
sys.path.insert(0, xia2_root_dir)
os.environ['XIA2_ROOT'] = xia2_root_dir
os.environ['XIA2CORE_ROOT'] = os.path.join(xia2_root_dir, "core")

from Handlers.Streams import Chatter, Debug

from Handlers.Citations import Citations
from Handlers.Environment import Environment
from lib.bits import auto_logfiler

# XML Marked up output for e-HTPX
if not os.path.join(os.environ['XIA2_ROOT'], 'Interfaces') in sys.path:
  sys.path.append(os.path.join(os.environ['XIA2_ROOT'], 'Interfaces'))

from Applications.xia2 import check, check_environment
from cctbx import miller
from cctbx.array_family import flex

from Modules.UnitCellErrors import _refinery

def load_sweeps_with_common_indexing():
  assert os.path.exists('xia2.json')
  from Schema.XProject import XProject
  xinfo = XProject.from_json(filename='xia2.json')

  import dials # required for gaussian_rs warning
  from Wrappers.Dials.Reindex import Reindex
  Citations.cite('dials')

  from dxtbx.model.experiment.experiment_list import ExperimentListFactory
  import cPickle as pickle
  crystals = xinfo.get_crystals()
  assert len(crystals) == 1
  crystal = next(crystals.itervalues())
  working_directory = Environment.generate_directory([crystal.get_name(), 'analysis'])
  os.chdir(working_directory)

  scaler = crystal._get_scaler()

  epoch_to_batches = {}
  epoch_to_integrated_intensities = {}
  epoch_to_sweep_name = {}

  # Aimless only
  epochs = scaler._sweep_handler.get_epochs()

  reference_cell = None
  reference_lattice = None
  reference_vectors = None
  reference_wavelength = None

  # Reindex each sweep to same setting
  all_miller_indices = flex.miller_index()
  all_two_thetas = flex.double()

  for epoch in epochs:
    si = scaler._sweep_handler.get_sweep_information(epoch)
    Chatter.smallbanner(si.get_sweep_name(), True)
    Debug.smallbanner(si.get_sweep_name(), True)

    intgr = si.get_integrater()
    experiments_filename = intgr.get_integrated_experiments()
    reflections_filename = intgr.get_integrated_reflections()
    refiner = intgr.get_integrater_refiner()
    Debug.write('experiment: %s' % experiments_filename)
    Debug.write('reflection: %s' % reflections_filename)

    # Use setting of first sweep as reference
    if reference_vectors is None:
      reference_vectors = experiments_filename

    # Assume that all sweeps have the same lattice system
    if reference_lattice is None:
      reference_lattice = refiner.get_refiner_lattice()
    else:
      assert reference_lattice == refiner.get_refiner_lattice()
    Debug.write("lattice: %s" % refiner.get_refiner_lattice())

    # Read .json file for sweep
    db = ExperimentListFactory.from_json_file(experiments_filename)

    # Assume that each file only contains a single experiment
    assert (len(db) == 1)
    db = db[0]

    # Get beam vector
    s0 = db.beam.get_unit_s0()

    # Use the unit cell of the first sweep as reference
    if reference_cell is None:
      reference_cell = db.crystal.get_unit_cell()
      Debug.write("Reference cell: %s" % str(reference_cell))

    dials_reindex = Reindex()
    dials_reindex.set_working_directory(working_directory)
    dials_reindex.set_cb_op("auto")
    dials_reindex.set_reference_filename(reference_vectors)
    dials_reindex.set_experiments_filename(experiments_filename)
    dials_reindex.set_indexed_filename(reflections_filename)
    auto_logfiler(dials_reindex)
    dials_reindex.run()

    # Assume that all data are collected at same wavelength
    if reference_wavelength is None:
      reference_wavelength = intgr.get_wavelength()
    else:
      assert abs(reference_wavelength - intgr.get_wavelength()) < 0.01
    Debug.write("wavelength: %f A" % intgr.get_wavelength())
    Debug.write("distance: %f mm" % intgr.get_distance())

    # Get integrated reflection data
    import dials
    with open(dials_reindex.get_reindexed_reflections_filename(), 'rb') as fh:
      reflections = pickle.load(fh)

    selection = reflections.get_flags(reflections.flags.used_in_refinement)
    Chatter.write("Found %d reflections used in refinement (out of %d entries)" % (selection.count(True), len(reflections['miller_index'])))
    reflections = reflections.select(selection)

    # Filter bad reflections
    selection = reflections['intensity.sum.variance'] <= 0
    if selection.count(True) > 0:
      reflections.del_selected(selection)
      print 'Removing %d reflections with negative variance' % \
        selection.count(True)

    if 'intensity.prf.variance' in reflections:
      selection = reflections['intensity.prf.variance'] <= 0
      if selection.count(True) > 0:
        reflections.del_selected(selection)
        print 'Removing %d profile reflections with negative variance' % \
          selection.count(True)

    # Find the observed 2theta angles
    miller_indices = flex.miller_index()
    two_thetas_obs = flex.double()
    for pixel, panel, hkl in zip(reflections['xyzobs.px.value'], reflections['panel'], reflections['miller_index']):
      assert hkl != (0, 0, 0)
      two_thetas_obs.append(db.detector[panel].get_two_theta_at_pixel(s0, pixel[0:2]))
      miller_indices.append(hkl)

    # Convert observed 2theta angles to degrees
    two_thetas_obs = two_thetas_obs * 180 / 3.14159265359
    Chatter.write("Remaining %d reflections are in 2theta range %.3f - %.3f deg" % (len(miller_indices), min(two_thetas_obs), max(two_thetas_obs)))

    all_miller_indices.extend(miller_indices)
    all_two_thetas.extend(two_thetas_obs)

  return all_miller_indices, all_two_thetas, reference_cell, reference_lattice, reference_wavelength


def get_unit_cell_errors(stop_after=None):
  '''Actually process something...'''
  wd = os.getcwd()

  all_miller_indices, all_two_thetas_obs, reference_cell, reference_lattice, reference_wavelength = load_sweeps_with_common_indexing()

  Chatter.banner('Unit cell sampling')
  Debug.banner('Unit cell sampling')
  span = miller.index_span(all_miller_indices)
  Chatter.write("Found %d reflections in 2theta range %.3f - %.3f deg" % (len(all_miller_indices), min(all_two_thetas_obs), max(all_two_thetas_obs)))
  Debug.write("Initial miller index range: %s - %s" % (str(span.min()), str(span.max())))

  # Exclude 1% of reflections to remove potential outliers
  # eg. indexed/integrated high angle noise
  two_theta_cutoff = sorted(all_two_thetas_obs)[-int(len(all_two_thetas_obs) * 0.01)-1]
  Chatter.write("Excluding outermost 1%% of reflections (2theta >= %.3f)" % two_theta_cutoff)
  two_thetas_select = all_two_thetas_obs < two_theta_cutoff
  all_two_thetas_obs = all_two_thetas_obs.select(two_thetas_select)
  all_miller_indices = all_miller_indices.select(two_thetas_select)

  Chatter.write("Kept %d reflections in 2theta range %.3f - %.3f deg" % (len(all_miller_indices), min(all_two_thetas_obs), max(all_two_thetas_obs)))
  span = miller.index_span(all_miller_indices)
  Chatter.write("Miller index range: %s - %s" % (str(span.min()), str(span.max())))

  unit_cell_info = { 'reflections':
                     { 'count': len(all_miller_indices),
                       'min_2theta': min(all_two_thetas_obs),
                       'max_2theta': max(all_two_thetas_obs),
                       'min_miller': list(span.min()),
                       'max_miller': list(span.max())
                     } }

  # prepare MonteCarlo sampling
  mc_runs = 50
  sample_size = min(len(all_miller_indices) // 2, 100)
  unit_cell_info['sampling'] = { 'method': 'montecarlo', 'runs': mc_runs, 'used_per_run': sample_size }
  unit_cell_info['reference'] = { 'cell': reference_cell.parameters(), 'cell_volume': reference_cell.volume(),
                                  'lattice': reference_lattice, 'wavelength': reference_wavelength }

  Chatter.write("\nRandomly sampling %d x %d reflections for Monte Carlo iterations" % (mc_runs, sample_size))
  Debug.write("Refinements start with reference unit cell:", reference_cell)

  MC = []
  MCconstrained = []
  used_index_range = flex.miller_index()
  used_two_theta_range_min = 1e300
  used_two_theta_range_max = 0
  used_reflections = set()

  for n in range(mc_runs): # MC sampling
    # Select sample_size reflections
    sample = flex.size_t(random.sample(range(len(all_miller_indices)), sample_size))
    used_reflections = used_reflections.union(set(sample))
    miller_indices = all_miller_indices.select(sample)
    two_thetas_obs = all_two_thetas_obs.select(sample)

    # Record
    span = miller.index_span(miller_indices)
    used_index_range.append(span.min())
    used_index_range.append(span.max())
    used_two_theta_range_min = min(used_two_theta_range_min, min(two_thetas_obs))
    used_two_theta_range_max = max(used_two_theta_range_max, max(two_thetas_obs))

    refined = _refinery(two_thetas_obs, miller_indices, reference_wavelength, reference_cell)
    MC.append(refined.unit_cell().parameters() + (refined.unit_cell().volume(),))
    Debug.write('Run %d refined to: %s', (n, str(refined.unit_cell())))
    if reference_lattice is not None and reference_lattice is not 'aP':
      refined = _refinery(two_thetas_obs, miller_indices, reference_wavelength, reference_cell, reference_lattice[0])
      MCconstrained.append(refined.unit_cell().parameters() + (refined.unit_cell().volume(),))
      Debug.write('Run %d (constrained %s) refined to: %s', (n, reference_lattice[0], str(refined.unit_cell())))

    if (n % 50) == 0:
      sys.stdout.write("\n%5s ." % (str(n) if n > 0 else ''))
    else:
      sys.stdout.write(".")
    sys.stdout.flush()

  assert used_two_theta_range_min < used_two_theta_range_max

  def stats_summary(l):
    mean = sum(l) / len(l)
    var = 0
    for y in l:
      var = var + ((y - mean) ** 2)
    popvar = var / (len(l)-1)
    popstddev = math.sqrt(popvar)
    stderr = popstddev / math.sqrt(len(l))
    return { 'mean': mean, 'variance': var, 'population_variance': popvar,
        'population_standard_deviation': popstddev, 'standard_error': stderr }

  print
  Chatter.write("")
  Chatter.write("Unit cell estimation based on %d Monte Carlo runs," % len(MC))
  span = miller.index_span(used_index_range)
  Chatter.write("drawn from miller indices between %s and %s" % (str(span.min()), str(span.max())))
  Chatter.write("with associated 2theta angles between %.3f and %.3f deg" % (used_two_theta_range_min, used_two_theta_range_max))
  unit_cell_info['sampling'].update({
      'used_reflections': len(used_reflections),
      'used_max_2theta': used_two_theta_range_max,
      'used_min_2theta': used_two_theta_range_min,
      'used_max_miller': span.max(),
      'used_min_miller': span.min() })
  unit_cell_info['solution_unconstrained'] = {}
  unit_cell_info['solution_constrained'] = { 'lattice': reference_lattice }
  if reference_lattice is None or reference_lattice == 'aP':
    Chatter.write("\n  Unconstrained estimate:", strip=False)
    for dimension, estimate in zip(['a', 'b', 'c', 'alpha', 'beta', 'gamma', 'volume'], zip(*MC)):
      est_stats = stats_summary(estimate)
      unit_cell_info['solution_unconstrained'][dimension] = est_stats
      unit_cell_info['solution_constrained'][dimension] = est_stats
      Chatter.write(" %6s =%10.5f (SD: %.5f, SE: %.5f)" % (dimension,
        est_stats['mean'],
        est_stats['population_standard_deviation'],
        est_stats['standard_error']), strip=False)
  else:
    Chatter.write("\n    Unconstrained estimate:                     |     Constrained estimate (%s):" % reference_lattice, strip=False)
    for dimension, estimate, constrained in zip(['a', 'b', 'c', 'alpha', 'beta', 'gamma', 'volume'], zip(*MC), zip(*MCconstrained)):
      est_stats = stats_summary(estimate)
      rest_stats = stats_summary(constrained)
      unit_cell_info['solution_unconstrained'][dimension] = est_stats
      unit_cell_info['solution_constrained'][dimension] = rest_stats
      Chatter.write(" %6s =%10.5f (SD: %.5f, SE: %.5f)  |  %6s =%10.5f (SD: %.5f, SE: %.5f)" %
        (dimension,
         est_stats['mean'],
         est_stats['population_standard_deviation'],
         est_stats['standard_error'],
         dimension,
         rest_stats['mean'],
         rest_stats['population_standard_deviation'],
         rest_stats['standard_error']), strip=False)

  with open(os.path.join(wd, 'xia2.get_unit_cell_errors.json'), 'w') as fh:
    json.dump(unit_cell_info, fh, indent = 2, sort_keys=True)


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
    print "Run after xia2 has successfully completed"
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
