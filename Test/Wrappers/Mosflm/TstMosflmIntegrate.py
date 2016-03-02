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


def exercise_mosflm_integrate():
  if not have_dials_regression:
    print "Skipping exercise_mosflm_integrate(): dials_regression not configured"
    return


  xia2_demo_data = os.path.join(dials_regression, "xia2_demo_data")
  template = os.path.join(xia2_demo_data, "insulin_1_%03i.img")

  from Wrappers.Mosflm.MosflmIndex import MosflmIndex
  from Wrappers.Mosflm.MosflmRefineCell import MosflmRefineCell
  from Wrappers.Mosflm.MosflmIntegrate import MosflmIntegrate

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
  #output = ''.join(refiner.get_all_output())
  #print output

  integrater = MosflmIntegrate()
  integrater.set_image_range((1,45))
  integrater.set_input_mat_file("xiaindex.mat")
  #integrater.set_output_mat_file("xiarefine.mat")
  integrater.set_directory(directory)
  integrater.set_template(templ)
  integrater.set_beam_centre(
    tuple(float(x) for x in refiner.get_refined_beam_centre()))
  integrater.set_distance(refiner.get_refined_distance())
  integrater.set_mosaic(refiner.get_refined_mosaic())
  integrater.set_space_group_number(197)
  integrater.set_unit_cell(refiner.get_refined_unit_cell())
  integrater.run()
  hklout = integrater.get_hklout()
  assert os.path.exists(hklout)
  from iotbx.reflection_file_reader import any_reflection_file
  miller_arrays = any_reflection_file(hklout).as_miller_arrays(
    merge_equivalents=False)
  for ma in miller_arrays:
    assert ma.size() == 81011, ma.size()
  assert len(miller_arrays) == 13, len(miller_arrays)
  assert not integrater.get_bgsig_too_large()
  assert not integrater.get_getprof_error()
  assert integrater.get_batches_out() == (1, 45)
  assert integrater.get_mosaic_spreads() == [
    0.43, 0.42, 0.42, 0.41, 0.41, 0.41, 0.42, 0.42, 0.42, 0.42, 0.42, 0.42,
    0.41, 0.41, 0.41, 0.41, 0.41, 0.41, 0.41, 0.41, 0.4, 0.4, 0.4, 0.4, 0.4,
    0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4,
    0.4, 0.39, 0.39, 0.39, 0.39, 0.39]
  assert integrater.get_nref() == 81011
  assert len(integrater.get_postref_result()) == 45
  assert integrater.get_postref_result()[1] == {
    'ovrl': 0.0, 'full': 507.0, 'dist': 158.6, 'ccx': -0.01, 'yscale': 1.0,
    'sdrat': 7.5, 'tilt': 25.0, 'rsym': 0.027, 'bad': 0.0, 'i/sigi': 18.1,
    'i/sigi_out': 1.6, 'twist': 13.0, 'resid': 0.021, 'wresid': 1.1,
    'part': 1309.0, 'nsym': 18.0, 'neg': 158.0, 'ccy': -0.01, 'ccom': -0.01,
    'toff': 0.0, 'roff': 0.0}
  assert integrater.get_residuals() == [
    1.1, 0.9, 1.0, 1.0, 0.8, 0.9, 1.0, 0.8, 0.9, 0.9, 0.9, 0.9, 1.0, 1.0, 1.0,
    0.9, 0.9, 0.9, 0.9, 0.8, 1.0, 0.9, 0.8, 0.9, 1.0, 0.8, 1.0, 0.9, 0.8, 0.8,
    0.9, 0.9, 0.9, 0.9, 0.9, 1.0, 0.8, 0.9, 1.0, 0.7, 0.8, 0.9, 0.8, 0.9, 1.0]
  assert integrater.get_spot_status() \
         == 'ooooooooooooooooooooooooooooooooooooooooooooo'


  #print
  #output = ''.join(refiner.get_all_output())
  #print output



def run():
  exercise_mosflm_integrate()
  print "OK"


if __name__ == '__main__':
  run()

