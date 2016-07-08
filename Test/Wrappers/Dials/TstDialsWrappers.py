import os
import sys

import libtbx.load_env
from libtbx import easy_run
from libtbx.test_utils import approx_equal, open_tmp_directory, show_diff

try:
  dials_regression = libtbx.env.dist_path('dials_regression')
  have_dials_regression = True
except KeyError, e:
  have_dials_regression = False


def exercise_dials_wrappers(nproc=None):
  if not have_dials_regression:
    print "Skipping exercise_dials_wrappers(): dials_regression not configured"
    return

  if nproc is not None:
    from xia2.Handlers.Phil import PhilIndex
    PhilIndex.params.xia2.settings.multiprocessing.nproc = nproc

  from xia2.Wrappers.Dials.Import import Import
  from xia2.Wrappers.Dials.Spotfinder import Spotfinder
  from xia2.Wrappers.Dials.Index import Index
  from xia2.Wrappers.Dials.Integrate import Integrate
  from xia2.Wrappers.Dials.RefineBravaisSettings import RefineBravaisSettings
  from xia2.Wrappers.Dials.Refine import Refine
  from xia2.Wrappers.Dials.Reindex import Reindex
  from xia2.Wrappers.Dials.ExportMtz import ExportMtz

  xia2_demo_data = os.path.join(dials_regression, "xia2_demo_data")
  template = os.path.join(xia2_demo_data, "insulin_1_%03i.img")
  scan_ranges = [(1, 45)]
  image_range = (1, 45)

  cwd = os.path.abspath(os.curdir)
  tmp_dir = os.path.abspath(open_tmp_directory())
  os.chdir(tmp_dir)

  print "Begin importing"
  importer = Import()
  importer.setup_from_image(template %1)
  importer.set_image_range(image_range)
  importer.run()
  print ''.join(importer.get_all_output())
  print "Done importing"

  print "Begin spotfinding"
  spotfinder = Spotfinder()
  spotfinder.set_input_sweep_filename(importer.get_sweep_filename())
  spotfinder.set_scan_ranges(scan_ranges)
  spotfinder.run()
  print ''.join(spotfinder.get_all_output())
  print "Done spotfinding"

  print "Begin indexing"
  indexer = Index()
  indexer.add_spot_filename(spotfinder.get_spot_filename())
  indexer.add_sweep_filename(importer.get_sweep_filename())
  indexer.run('fft3d')
  print ''.join(indexer.get_all_output())
  print "Done indexing"

  print "Begin refining"
  rbs = RefineBravaisSettings()
  rbs.set_experiments_filename(indexer.get_experiments_filename())
  rbs.set_indexed_filename(indexer.get_indexed_filename())
  rbs.run()
  print ''.join(rbs.get_all_output())
  print "Done refining"
  bravais_setting_22 = rbs.get_bravais_summary()[22]
  assert bravais_setting_22['bravais'] == 'cI'
  assert bravais_setting_22['cb_op'] == 'b+c,a+c,a+b'
  assert approx_equal(bravais_setting_22['unit_cell'],
                      (78.14,78.14,78.14,90,90,90), eps=1e-1)
  bravais_setting_22_json = bravais_setting_22['experiments_file']
  assert os.path.exists(bravais_setting_22_json)

  print "Begin reindexing"
  reindexer = Reindex()
  reindexer.set_experiments_filename(indexer.get_experiments_filename())
  reindexer.set_indexed_filename(indexer.get_indexed_filename())
  reindexer.set_cb_op(bravais_setting_22['cb_op'])
  reindexer.run()
  assert os.path.exists(reindexer.get_reindexed_experiments_filename())
  assert os.path.exists(reindexer.get_reindexed_reflections_filename())
  print ''.join(reindexer.get_all_output())
  print "Done reindexing"

  print "Begin refining"
  refiner = Refine()
  refiner.set_experiments_filename(bravais_setting_22_json)
  refiner.set_indexed_filename(reindexer.get_reindexed_reflections_filename())
  refiner.set_scan_varying(True)
  refiner.run()
  assert os.path.exists(refiner.get_refined_experiments_filename())
  print ''.join(refiner.get_all_output())
  print "Done refining"

  print "Begin integrating"
  integrater = Integrate()
  integrater.set_experiments_filename(refiner.get_refined_experiments_filename())
  integrater.set_reflections_filename(reindexer.get_reindexed_reflections_filename())
  integrater.run()
  print ''.join(integrater.get_all_output())
  print "Done integrating"

  print "Begin exporting"
  exporter = ExportMtz()
  exporter.set_experiments_filename(integrater.get_integrated_experiments())
  exporter.set_reflections_filename(integrater.get_integrated_reflections())
  exporter.run()
  print ''.join(exporter.get_all_output())
  print "Done exporting"
  assert os.path.exists(exporter.get_mtz_filename())

  import shutil
  shutil.copy(indexer.get_experiments_filename(), "copy.json")
  shutil.copy(indexer.get_indexed_filename(), "copy.pickle")
  print "Begin combining"
  from xia2.Wrappers.Dials.CombineExperiments import CombineExperiments
  exporter = CombineExperiments()
  exporter.add_experiments(indexer.get_experiments_filename())
  exporter.add_experiments("copy.json")
  exporter.add_reflections(indexer.get_indexed_filename())
  exporter.add_reflections("copy.pickle")
  exporter.run()
  print ''.join(exporter.get_all_output())
  print "Done combining"
  assert os.path.exists(exporter.get_combined_experiments_filename())
  assert os.path.exists(exporter.get_combined_reflections_filename())



def run(args):
  assert len(args) <= 1, args
  if len(args) == 1:
    nproc = int(args[0])
  else:
    nproc = None
  exercise_dials_wrappers(nproc=nproc)
  print "OK"


if __name__ == '__main__':
  run(sys.argv[1:])
