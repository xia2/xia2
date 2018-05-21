from __future__ import absolute_import, division, print_function

import os

import pytest

def test_indexing_with_labelit_on_two_images(xia2_regression_build, tmpdir):
  template = os.path.join(xia2_regression_build, "test_data", "insulin", "insulin_1_%03i.img")
  tmpdir.chdir()

  from xia2.DriverExceptions.NotAvailableError import NotAvailableError
  from xia2.Wrappers.Labelit.LabelitIndex import LabelitIndex
  try:
    indexer = LabelitIndex()
  except NotAvailableError:
    pytest.skip("labelit not found")

  indexer.set_beam_search_scope(4.0)
  for image in (1, 45):
    indexer.add_image(template % image)

  indexer.run()

  print(''.join(indexer.get_all_output()))
  assert indexer.get_mosflm_beam_centre() == pytest.approx((94.35, 94.52), abs=1e-1)
  assert indexer.get_mosflm_detector_distance() == pytest.approx(159.8, abs=1e-1)

  solutions = indexer.get_solutions()
  assert len(solutions) == 22
  assert solutions[22]['cell'] == pytest.approx([78.6, 78.6, 78.6, 90, 90, 90], abs=1e-1)
  assert solutions[22]['lattice'] == 'cI'
  assert solutions[22]['rmsd'] <= 0.12
  assert solutions[22]['metric'] <= 0.1243
  assert solutions[22]['smiley'] == ':) '
  assert solutions[22]['number'] == 22
  assert solutions[22]['mosaic'] <= 0.2
  assert solutions[22]['nspots'] == pytest.approx(563, abs=30)

def test_indexing_with_labelit_on_multiple_images(xia2_regression_build, tmpdir):
  template = os.path.join(xia2_regression_build, "test_data", "insulin", "insulin_1_%03i.img")
  tmpdir.chdir()

  from xia2.DriverExceptions.NotAvailableError import NotAvailableError
  from xia2.Wrappers.Labelit.LabelitIndex import LabelitIndex
  try:
    indexer = LabelitIndex()
  except NotAvailableError:
    pytest.skip("labelit not found")

  for image in (1, 22, 45):
    indexer.add_image(template % image)
  indexer.set_distance(160)
  indexer.set_beam_centre((94.24, 94.52))
  indexer.set_wavelength(0.98)
  indexer.set_refine_beam(False)

  indexer.run()

  print(''.join(indexer.get_all_output()))
  assert indexer.get_mosflm_beam_centre() == pytest.approx((94.35, 94.49), abs=4e-2)
  assert indexer.get_mosflm_detector_distance() == pytest.approx(159.75, abs=1e-1)

  solutions = indexer.get_solutions()
  assert len(solutions) == 22
  assert solutions[22]['cell'] == pytest.approx([78.61, 78.61, 78.61, 90, 90, 90], abs=5e-2)
  assert solutions[22]['lattice'] == 'cI'
  assert solutions[22]['rmsd'] <= 0.16
  assert solutions[22]['metric'] <= 0.18
  assert solutions[22]['smiley'] == ':) '
  assert solutions[22]['number'] == 22
  assert solutions[22]['mosaic'] <= 0.12
  assert solutions[22]['nspots'] == pytest.approx(823, abs=41) # XXX quite a big difference!
