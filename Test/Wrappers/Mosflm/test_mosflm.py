from __future__ import absolute_import, division, print_function

import os
import sys

import mock
import pytest
from libtbx.test_utils import approx_equal
from xia2.Experts.FindImages import image2template_directory
from xia2.Wrappers.Mosflm.MosflmIndex import MosflmIndex
from xia2.Wrappers.Mosflm.MosflmRefineCell import MosflmRefineCell

def get_template_and_directory(dials_regression):
  xia2_demo_data = os.path.join(dials_regression, "xia2_demo_data")
  template = os.path.join(xia2_demo_data, "insulin_1_%03i.img")
  with mock.patch.object(sys, 'argv', []):
    return image2template_directory(template %1)

two_images_indexing = {
  'beam_centre': (94.33, 94.58),
  'mosaicity': 0.4
}

@pytest.mark.slow
def test_index_two_images_with_mosflm(ccp4, dials_regression, tmpdir):
  tmpdir.chdir()
  templ, directory = get_template_and_directory(dials_regression)

  # exercise basic indexing from two images
  indexer = MosflmIndex()
  indexer.set_images((1,45))
  indexer.set_directory(directory)
  indexer.set_template(templ)
  indexer.run()
  print(''.join(indexer.get_all_output()))
  assert approx_equal(indexer.get_refined_beam_centre(),
                      two_images_indexing['beam_centre'])
  assert approx_equal(indexer.get_refined_unit_cell(),
                      (78.655, 78.655, 78.655, 90.0, 90.0, 90.0), 1e-3)
  assert approx_equal(indexer.get_refined_distance(), 160.0)
  assert approx_equal(indexer.get_resolution_estimate(), 2.12)
  assert approx_equal(indexer.get_separation(), [0.57, 0.57])
  assert approx_equal(indexer.get_raster(), [17, 17, 10, 5, 5])
  assert approx_equal(indexer.get_mosaic_spreads(), [two_images_indexing['mosaicity']]*2)
  assert indexer.get_lattice() == 'cI'

@pytest.mark.slow
def test_indexing_multiple_images_with_mosflm(ccp4, dials_regression, tmpdir):
  tmpdir.chdir()
  templ, directory = get_template_and_directory(dials_regression)

  # now exercise indexing off multiple images and test more settings
  indexer = MosflmIndex()
  indexer.set_images((5,15,25,35,45))
  indexer.set_directory(directory)
  indexer.set_template(templ)
  indexer.set_unit_cell((78,78,78,90,90,90))
  indexer.set_distance(159)
  indexer.set_space_group_number(197)
  indexer.run()
  print(''.join(indexer.get_all_output()))
  assert approx_equal(indexer.get_refined_beam_centre(), (94.33, 94.57))
  assert approx_equal(indexer.get_refined_unit_cell(),
                      (78.2082, 78.2082, 78.2082, 90.0, 90.0, 90.0))
  assert approx_equal(indexer.get_refined_distance(), 159.0)
  assert approx_equal(indexer.get_resolution_estimate(), 2.12)
  assert approx_equal(indexer.get_separation(), [0.48, 0.57])
  assert approx_equal(indexer.get_raster(), [15, 17, 9, 5, 5])
  assert approx_equal(
    indexer.get_mosaic_spreads(), [0.5, 0.35, 0.45, 0.65, 0.4], eps=1e-1)
  assert indexer.get_lattice() == 'cI'

@pytest.mark.slow
def test_mosflm_refine_cell(ccp4, dials_regression, tmpdir):
  tmpdir.chdir()
  templ, directory = get_template_and_directory(dials_regression)

  matrix = ''' -0.00728371 -0.00173706 -0.00994261
  0.01008485 -0.00175152 -0.00708190
 -0.00041078 -0.01220000  0.00243238
       0.000       0.000       0.000
  -0.5851825  -0.1395579  -0.7988023
   0.8102298  -0.1407195  -0.5689691
  -0.0330029  -0.9801641   0.1954206
     78.6541     78.6541     78.6542     90.0000     90.0000     90.0000
       0.000       0.000       0.000
SYMM I23       \n'''
  tmpdir.join('xiaindex.mat').write(matrix)

  refiner = MosflmRefineCell()
  refiner.set_images(((1,3), (21,23), (43,45)))
  refiner.set_input_mat_file("xiaindex.mat")
  refiner.set_output_mat_file("xiarefine.mat")
  refiner.set_directory(directory)
  refiner.set_template(templ)
  refiner.set_beam_centre(two_images_indexing['beam_centre'])
  refiner.set_mosaic(two_images_indexing['mosaicity'])
  refiner.run()
  output = ''.join(refiner.get_all_output())
  print(output)

  background_residual = refiner.get_background_residual()
  rms_values = refiner.get_rms_values()

  ref_residual = {
    1: {1: 0.1, 2: 0.1, 3: 0.1, 43: 0.1, 44: 0.2, 45: 0.1, 21: 0.1, 22: 0.1, 23: 0.1},
    2: {1: 0.1, 2: 0.1, 3: 0.1, 43: 0.1, 44: 0.2, 45: 0.1, 21: 0.1, 22: 0.1, 23: 0.1},
    3: {1: 0.1, 2: 0.1, 3: 0.1, 43: 0.1, 44: 0.2, 45: 0.1, 21: 0.1, 22: 0.1, 23: 0.1}
  }

  for cycle in background_residual:
    for frame in background_residual[cycle]:
      assert background_residual[cycle][frame] == \
             pytest.approx(ref_residual[cycle][frame], abs=0.1)

  ref_values = {
    1: [0.027, 0.029, 0.027, 0.025, 0.027, 0.025, 0.024, 0.022, 0.025],
    2: [0.02, 0.021, 0.023, 0.021, 0.02, 0.017, 0.018, 0.019, 0.022],
    3: [0.02, 0.021, 0.025, 0.022, 0.021, 0.019, 0.018, 0.019, 0.021]
  }

  for cycle in rms_values:
    for frame, value in enumerate(rms_values[cycle]):
      assert value == \
             pytest.approx(ref_values[cycle][frame], abs=0.05)
