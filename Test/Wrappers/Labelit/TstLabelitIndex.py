from __future__ import absolute_import, division

import os

import libtbx.load_env
from libtbx.test_utils import approx_equal, open_tmp_directory

try:
  dials_regression = libtbx.env.dist_path('dials_regression')
  have_dials_regression = True
except KeyError:
  have_dials_regression = False


def exercise_labelit_index():
  if not have_dials_regression:
    print "Skipping exercise_labelit_index(): dials_regression not configured"
    return


  xia2_demo_data = os.path.join(dials_regression, "xia2_demo_data")
  template = os.path.join(xia2_demo_data, "insulin_1_%03i.img")

  from xia2.Wrappers.Labelit.LabelitIndex import LabelitIndex

  # exercise basic indexing from two images
  cwd = os.path.abspath(os.curdir)
  tmp_dir = open_tmp_directory()
  os.chdir(tmp_dir)

  from xia2.DriverExceptions.NotAvailableError import NotAvailableError
  try:
    indexer = LabelitIndex()
  except NotAvailableError:
    print "Skipping exercise_labelit_index(): labelit not found"
    return
  indexer.set_beam_search_scope(4.0)
  indexer.add_image(template %1)
  indexer.add_image(template %45)
  indexer.run()
  output = ''.join(indexer.get_all_output())
  print output
  assert approx_equal(
    indexer.get_mosflm_beam_centre(), (94.35, 94.52), eps=1e-1)
  assert approx_equal(indexer.get_mosflm_detector_distance(), 159.8, eps=1e-1)
  solutions = indexer.get_solutions()
  assert len(solutions) == 22
  assert approx_equal(solutions[22]['cell'], [78.6, 78.6, 78.6, 90, 90, 90], eps=1e-1)
  assert solutions[22]['lattice'] == 'cI'
  assert solutions[22]['rmsd'] <= 0.12
  assert solutions[22]['metric'] <= 0.1243
  assert solutions[22]['smiley'] == ':) '
  assert solutions[22]['number'] == 22
  assert solutions[22]['mosaic'] <= 0.2
  assert abs(solutions[22]['nspots'] - 563) <= 30


  # now exercise indexing off multiple images and test more settings
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
  output = ''.join(indexer.get_all_output())
  print output
  assert approx_equal(indexer.get_mosflm_beam_centre(), (94.35, 94.49), eps=4e-2)
  assert approx_equal(indexer.get_mosflm_detector_distance(), 159.75, eps=1e-1)
  solutions = indexer.get_solutions()
  assert len(solutions) == 22
  assert approx_equal(solutions[22]['cell'], [78.61, 78.61, 78.61, 90, 90, 90], eps=5e-2)
  assert solutions[22]['lattice'] == 'cI'
  assert solutions[22]['rmsd'] <= 0.16
  assert solutions[22]['metric'] <= 0.18
  assert solutions[22]['smiley'] == ':) '
  assert solutions[22]['number'] == 22
  assert solutions[22]['mosaic'] <= 0.12
  assert abs(solutions[22]['nspots'] - 823) <= 41 # XXX quite a big difference!


def run():
  exercise_labelit_index()
  print "OK"


if __name__ == '__main__':
  run()

