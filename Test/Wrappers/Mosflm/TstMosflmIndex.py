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
from libtbx.test_utils import approx_equal, open_tmp_directory, show_diff

try:
  dials_regression = libtbx.env.dist_path('dials_regression')
  have_dials_regression = True
except KeyError, e:
  have_dials_regression = False


def exercise_mosflm_index():
  if not have_dials_regression:
    print "Skipping exercise_mosflm_index(): dials_regression not configured"
    return


  xia2_demo_data = os.path.join(dials_regression, "xia2_demo_data")
  template = os.path.join(xia2_demo_data, "insulin_1_%03i.img")

  from Wrappers.Mosflm.MosflmIndex import MosflmIndex

  # exercise basic indexing from two images
  cwd = os.path.abspath(os.curdir)
  tmp_dir = open_tmp_directory()
  os.chdir(tmp_dir)

  indexer = MosflmIndex()
  indexer.set_images((1,45))

  from Experts.FindImages import image2template_directory
  templ, directory = image2template_directory(template %1)

  indexer.set_directory(directory)
  indexer.set_template(templ)
  indexer.run()
  output = ''.join(indexer.get_all_output())
  print output
  assert approx_equal(indexer.get_refined_beam_centre(), (94.33, 94.58))
  assert approx_equal(indexer.get_refined_unit_cell(),
                      (78.655, 78.655, 78.655, 90.0, 90.0, 90.0), 1e-3)
  assert approx_equal(indexer.get_refined_distance(), 160.0)
  assert approx_equal(indexer.get_resolution_estimate(), 2.12)
  assert approx_equal(indexer.get_separation(), [0.57, 0.57])
  assert approx_equal(indexer.get_raster(), [17, 17, 10, 5, 5])
  assert approx_equal(indexer.get_mosaic_spreads(), [0.4, 0.4])
  assert indexer.get_lattice() == 'cI'

  # now exercise indexing off multiple images and test more settings
  os.chdir(cwd)
  tmp_dir = open_tmp_directory()
  os.chdir(tmp_dir)

  indexer = MosflmIndex()
  indexer.set_images((5,15,25,35,45))
  indexer.set_directory(directory)
  indexer.set_template(templ)
  indexer.set_unit_cell((78,78,78,90,90,90))
  indexer.set_distance(159)
  indexer.set_space_group_number(197)
  indexer.run()
  output = ''.join(indexer.get_all_output())
  print output
  assert approx_equal(indexer.get_refined_beam_centre(), (94.33, 94.57))
  assert approx_equal(indexer.get_refined_unit_cell(),
                      (78.2082, 78.2082, 78.2082, 90.0, 90.0, 90.0))
  assert approx_equal(indexer.get_refined_distance(), 159.0)
  assert approx_equal(indexer.get_resolution_estimate(), 2.12)
  assert approx_equal(indexer.get_separation(), [0.48, 0.57])
  assert approx_equal(indexer.get_raster(), [15, 17, 9, 5, 5])
  assert approx_equal(
    indexer.get_mosaic_spreads(), [0.5, 0.35, 0.45, 0.65, 0.4])
  assert indexer.get_lattice() == 'cI'

def run():
  exercise_mosflm_index()
  print "OK"


if __name__ == '__main__':
  run()

