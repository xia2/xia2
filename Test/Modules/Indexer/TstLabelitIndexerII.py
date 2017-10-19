from __future__ import absolute_import, division

import os

import libtbx.load_env
from libtbx.test_utils import approx_equal, open_tmp_directory

try:
  dials_regression = libtbx.env.dist_path('dials_regression')
  have_dials_regression = True
except KeyError:
  have_dials_regression = False


def exercise_labelit_indexerii():
  if not have_dials_regression:
    print "Skipping exercise_labelit_indexerii(): dials_regression not configured"
    return

  xia2_demo_data = os.path.join(dials_regression, "xia2_demo_data")
  template = os.path.join(xia2_demo_data, "insulin_1_###.img")

  cwd = os.path.abspath(os.curdir)
  tmp_dir = os.path.abspath(open_tmp_directory())
  os.chdir(tmp_dir)

  from xia2.Modules.Indexer.LabelitIndexerII import LabelitIndexerII

  from xia2.DriverExceptions.NotAvailableError import NotAvailableError
  try:
    ls = LabelitIndexerII(indxr_print=True)
  except NotAvailableError:
    print "Skipping exercise_labelit_indexerii(): labelit not found"
    return
  ls.set_working_directory(tmp_dir)
  from dxtbx.datablock import DataBlockTemplateImporter
  importer = DataBlockTemplateImporter([template])
  datablocks = importer.datablocks
  imageset = datablocks[0].extract_imagesets()[0]
  ls.add_indexer_imageset(imageset)
  ls.set_indexer_input_cell((78,78,78,90,90,90))
  ls.set_indexer_user_input_lattice(True)
  ls.set_indexer_input_lattice('cI')
  ls.index()

  assert approx_equal(ls.get_indexer_cell(), (78.52, 78.52, 78.52, 90, 90, 90),
                      eps=1e-1)
  solution = ls.get_solution()
  assert approx_equal(solution['rmsd'], 0.079, eps=1e-1)
  assert solution['metric'] <= 0.1762
  assert solution['number'] == 22
  assert solution['lattice'] == 'cI'
  assert solution['mosaic'] <= 0.2
  assert abs(solution['nspots'] - 5509) <= 50

  beam_centre = ls.get_indexer_beam_centre()
  assert approx_equal(beam_centre, (94.3286, 94.4662), eps=5e-1)
  assert ls.get_indexer_images() == [
    (1, 1), (3, 3), (5, 5), (7, 7), (9, 9), (11, 11), (13, 13), (15, 15),
    (17, 17), (19, 19), (21, 21), (23, 23), (25, 25), (27, 27), (29, 29),
    (31, 31), (33, 33), (35, 35), (37, 37), (39, 39)]
  print ls.get_indexer_experiment_list()[0].crystal
  print ls.get_indexer_experiment_list()[0].detector


def run():
  exercise_labelit_indexerii()
  print "OK"


if __name__ == '__main__':
  run()
