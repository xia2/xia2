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


def exercise_labelit_indexer():
  if not have_dials_regression:
    print "Skipping exercise_labelit_indexer(): dials_regression not configured"
    return

  xia2_demo_data = os.path.join(dials_regression, "xia2_demo_data")
  template = os.path.join(xia2_demo_data, "insulin_1_###.img")

  cwd = os.path.abspath(os.curdir)
  tmp_dir = os.path.abspath(open_tmp_directory())
  os.chdir(tmp_dir)

  from xia2.Modules.Indexer.LabelitIndexer import LabelitIndexer

  from xia2.DriverExceptions.NotAvailableError import NotAvailableError
  try:
    ls = LabelitIndexer(indxr_print=True)
  except NotAvailableError:
    print "Skipping exercise_labelit_indexer(): labelit not found"
    return
  ls.set_working_directory(tmp_dir)
  from dxtbx.datablock import DataBlockTemplateImporter
  importer = DataBlockTemplateImporter([template])
  datablocks = importer.datablocks
  imageset = datablocks[0].extract_imagesets()[0]
  ls.add_indexer_imageset(imageset)
  ls.index()

  assert approx_equal(ls.get_indexer_cell(), (78.58, 78.58, 78.58, 90, 90, 90))
  solution = ls.get_solution()
  assert approx_equal(solution['rmsd'], 0.076)
  assert approx_equal(solution['metric'], 0.1566, eps=1e-3)
  assert solution['number'] == 22
  assert solution['lattice'] == 'cI'
  assert solution['mosaic'] == 0.025
  assert abs(solution['nspots'] - 860) <= 1

  beam_centre = ls.get_indexer_beam_centre()
  assert approx_equal(beam_centre, (94.3416, 94.4994), eps=1e-2)
  assert ls.get_indexer_images() == [(1, 1), (22, 22), (45, 45)]
  print ls.get_indexer_experiment_list()[0].crystal
  print ls.get_indexer_experiment_list()[0].detector

  json_str = ls.as_json()
  #print ls.to_dict()
  print json_str
  ls1 = LabelitIndexer.from_json(string=json_str)
  ls1.index()

  print ls.get_indexer_experiment_list()[0].crystal
  assert ls.get_indexer_beam_centre() == ls1.get_indexer_beam_centre()
  assert approx_equal(ls.get_indexer_images(), ls1.get_indexer_images())
  assert ls.get_distance() == ls1.get_distance()

  ls.eliminate()
  ls1.eliminate()

  print ls1.get_indexer_experiment_list()[0].crystal
  assert ls.get_indexer_beam_centre() == ls1.get_indexer_beam_centre()
  assert approx_equal(ls.get_indexer_images(), ls1.get_indexer_images())
  assert ls.get_distance() == ls1.get_distance()

  print ls1.get_indexer_cell()
  print ls1.get_solution()
  assert approx_equal(ls.get_indexer_cell(),
                      (111.11, 111.11, 68.08, 90.0, 90.0, 120.0), 1e-1)
  solution = ls1.get_solution()
  assert solution['rmsd'] >= 0.07, solution['rmsd']
  assert approx_equal(solution['metric'], 0.1291, eps=1e-3)
  #assert solution['number'] == 8
  assert solution['lattice'] == 'hR', solution['lattice']
  assert solution['mosaic'] == 0.025, solution['mosaic']
  assert abs(solution['nspots'] - 856) <= 3

def run():
  exercise_labelit_indexer()
  print "OK"


if __name__ == '__main__':
  run()
