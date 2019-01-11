from __future__ import absolute_import, division, print_function

import pytest

def test_labelit_indexer_II(regression_test, ccp4, dials_data, run_in_tmpdir):
  template = dials_data('insulin').join("insulin_1_###.img").strpath

  from xia2.Modules.Indexer.LabelitIndexerII import LabelitIndexerII
  from xia2.DriverExceptions.NotAvailableError import NotAvailableError
  try:
    ls = LabelitIndexerII(indxr_print=True)
  except NotAvailableError:
    pytest.skip("labelit not found")
  ls.set_working_directory(run_in_tmpdir.strpath)
  from dxtbx.datablock import DataBlockTemplateImporter
  importer = DataBlockTemplateImporter([template])
  datablocks = importer.datablocks
  imageset = datablocks[0].extract_imagesets()[0]
  ls.add_indexer_imageset(imageset)
  ls.set_indexer_input_cell((78,78,78,90,90,90))
  ls.set_indexer_user_input_lattice(True)
  ls.set_indexer_input_lattice('cI')
  ls.index()

  assert ls.get_indexer_cell() == pytest.approx((78.52, 78.52, 78.52, 90, 90, 90), abs=1e-1)
  solution = ls.get_solution()
  assert solution['rmsd'] == pytest.approx(0.079, abs=1e-1)
  assert solution['metric'] <= 0.1762
  assert solution['number'] == 22
  assert solution['lattice'] == 'cI'
  assert solution['mosaic'] <= 0.2
  assert solution['nspots'] == pytest.approx(5509, abs=50)

  beam_centre = ls.get_indexer_beam_centre()
  assert beam_centre == pytest.approx((94.3286, 94.4662), abs=5e-1)
  assert ls.get_indexer_images() == [
    (1, 1), (3, 3), (5, 5), (7, 7), (9, 9), (11, 11), (13, 13), (15, 15),
    (17, 17), (19, 19), (21, 21), (23, 23), (25, 25), (27, 27), (29, 29),
    (31, 31), (33, 33), (35, 35), (37, 37), (39, 39)]
  print(ls.get_indexer_experiment_list()[0].crystal)
  print(ls.get_indexer_experiment_list()[0].detector)
