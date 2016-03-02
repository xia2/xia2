import os
import sys

if not os.environ.has_key('XIA2_ROOT'):
  raise RuntimeError, 'XIA2_ROOT not defined'

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


def exercise_mosflm_refine_cell():
  if not have_dials_regression:
    print "Skipping exercise_mosflm_refine_cell(): dials_regression not configured"
    return


  xia2_demo_data = os.path.join(dials_regression, "xia2_demo_data")
  template = os.path.join(xia2_demo_data, "insulin_1_%03i.img")

  from Wrappers.Mosflm.MosflmIndex import MosflmIndex
  from Wrappers.Mosflm.MosflmRefineCell import MosflmRefineCell

  # exercise basic indexing from two images
  cwd = os.path.abspath(os.curdir)
  tmp_dir = open_tmp_directory()
  os.chdir(tmp_dir)

  from Experts.FindImages import image2template_directory
  templ, directory = image2template_directory(template %1)

  indexer = MosflmIndex()
  indexer.set_images((1,45))
  indexer.set_directory(directory)
  indexer.set_template(templ)
  indexer.run()

  refiner = MosflmRefineCell()
  refiner.set_images(((1,3),(21,23), (43,45)))
  refiner.set_input_mat_file("xiaindex.mat")
  refiner.set_output_mat_file("xiarefine.mat")
  refiner.set_directory(directory)
  refiner.set_template(templ)
  refiner.set_beam_centre(indexer.get_refined_beam_centre())
  refiner.set_mosaic(
    sum(indexer.get_mosaic_spreads())/len(indexer.get_mosaic_spreads()))
  refiner.run()
  output = ''.join(refiner.get_all_output())
  print output

  background_residual = refiner.get_background_residual()
  rms_values = refiner.get_rms_values()

  ref_residual = {
    1: {1: 0.1, 2: 0.1, 3: 0.1, 43: 0.1, 44: 0.2, 45: 0.1, 21: 0.1, 22: 0.1, 23: 0.1},
    2: {1: 0.1, 2: 0.1, 3: 0.1, 43: 0.1, 44: 0.2, 45: 0.1, 21: 0.1, 22: 0.1, 23: 0.1},
    3: {1: 0.1, 2: 0.1, 3: 0.1, 43: 0.1, 44: 0.2, 45: 0.1, 21: 0.1, 22: 0.1, 23: 0.1}
  }

  for cycle in background_residual:
    for frame in background_residual[cycle]:
      assert abs(background_residual[cycle][frame] -
                 ref_residual[cycle][frame]) <= 0.1, (cycle, frame)

  ref_values = {
    1: [0.027, 0.029, 0.027, 0.025, 0.027, 0.025, 0.024, 0.022, 0.025],
    2: [0.02, 0.021, 0.023, 0.021, 0.02, 0.017, 0.018, 0.019, 0.022],
    3: [0.02, 0.021, 0.025, 0.022, 0.021, 0.019, 0.018, 0.019, 0.021]
  }

  for cycle in rms_values:
    for frame in range(len(rms_values[cycle])):
      assert abs(rms_values[cycle][frame] - ref_values[cycle][frame]) <= 0.05


def run():
  exercise_mosflm_refine_cell()
  print "OK"


if __name__ == '__main__':
  run()
