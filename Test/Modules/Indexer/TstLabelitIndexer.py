
import os
import sys
if not os.environ.has_key('XIA2CORE_ROOT'):
  raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.environ.has_key('XIA2_ROOT'):
  raise RuntimeError, 'XIA2_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'],
                    'Python') in sys.path:
  sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                               'Python'))

if not os.environ['XIA2_ROOT'] in sys.path:
  sys.path.append(os.environ['XIA2_ROOT'])

import libtbx.load_env
from libtbx import easy_run
from libtbx.test_utils import show_diff
from libtbx.test_utils import open_tmp_directory
try:
  dials_regression = libtbx.env.dist_path('dials_regression')
  have_dials_regression = True
except KeyError, e:
  have_dials_regression = False


def exercise_labelit_indexer():
  if not have_dials_regression:
    print "Skipping exercise_labelit_index(): dials_regression not configured"
    return

  xia2_demo_data = os.path.join(dials_regression, "xia2_demo_data")
  template = os.path.join(xia2_demo_data, "insulin_1_%03i.img")

  cwd = os.path.abspath(os.curdir)
  tmp_dir = os.path.abspath(open_tmp_directory())
  os.chdir(tmp_dir)

  from Modules.Indexer.LabelitIndexer import LabelitIndexer
  ls = LabelitIndexer(indxr_print=True)
  ls.set_working_directory(tmp_dir)
  ls.setup_from_image(template %1)
  ls.index()
  assert ls.get_solution() == {
    'volume': 485230,
    'rmsd': 0.076,
    'metric': 0.1566,
    'smiley': ':) ',
    'number': 22,
    'cell': [78.58, 78.58, 78.58, 90.0, 90.0, 90.0],
    'lattice': 'cI',
    'mosaic': 0.025,
    'nspots': 860}
  beam_centre = ls.get_indexer_beam_centre()
  assert beam_centre == (94.3416, 94.4994)
  assert ls.get_indexer_images() == [(1, 1), (22, 22), (45, 45)]
  print ls.get_indexer_experiment_list()[0].crystal
  print ls.get_indexer_experiment_list()[0].detector


def run():
  exercise_labelit_indexer()
  print "OK"


if __name__ == '__main__':
  run()
