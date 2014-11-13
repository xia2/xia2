
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


def exercise_labelit_index():
  if not have_dials_regression:
    print "Skipping exercise_labelit_index(): dials_regression not configured"
    return

  
  xia2_demo_data = os.path.join(dials_regression, "xia2_demo_data")
  template = os.path.join(xia2_demo_data, "insulin_1_%03i.img")

  from Wrappers.Labelit.LabelitIndex import LabelitIndex

  # exercise basic indexing from one image
  cwd = os.path.abspath(os.curdir)
  tmp_dir = open_tmp_directory()
  os.chdir(tmp_dir)

  indexer = LabelitIndex()
  indexer.add_image(template %1)
  indexer.run()
  assert indexer.get_mosflm_beam_centre() == (94.24, 94.52)
  assert indexer.get_mosflm_detector_distance() == 159.8
  solutions = indexer.get_solutions()
  assert len(solutions) == 22
  assert solutions[22] == {
    'cell': [78.47, 78.47, 78.47, 90.0, 90.0, 90.0],
    'lattice': 'cI',
    'rmsd': 0.154,
    'volume': 483239,
    'metric': 0.5812,
    'smiley': ':) ',
    'number': 22,
    'mosaic': 0.075,
    'nspots': 273
  }
  output = ''.join(indexer.get_all_output())
  #print output

  # now exercise indexing off more than one image and test more settings
  os.chdir(cwd)
  tmp_dir = open_tmp_directory()
  os.chdir(tmp_dir)

  indexer = LabelitIndex()
  indexer.add_image(template %1)
  indexer.add_image(template %22)
  indexer.add_image(template %45)
  indexer.set_distance(160)
  indexer.set_beam_centre((94.24, 94.52))
  indexer.set_wavelength(0.98)
  indexer.set_refine_beam(False)
  indexer.run()
  assert indexer.get_mosflm_beam_centre() == (94.35, 94.49)
  assert indexer.get_mosflm_detector_distance() == 159.75
  solutions = indexer.get_solutions()
  assert len(solutions) == 22
  assert solutions[22] == {
    'cell': [78.61, 78.61, 78.61, 90.0, 90.0, 90.0],
    'lattice': 'cI',
    'rmsd': 0.073,
    'volume': 485784,
    'metric': 0.0942,
    'smiley': ':) ',
    'number': 22,
    'mosaic': 0.025,
    'nspots': 823
  }
  output = ''.join(indexer.get_all_output())
  #print output
 
  
def run():
  exercise_labelit_index()
  print "OK"


if __name__ == '__main__':
  run()

