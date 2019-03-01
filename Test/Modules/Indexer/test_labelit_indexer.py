from __future__ import absolute_import, division, print_function

import pytest

def test_labelit_indexer(regression_test, ccp4, dials_data, run_in_tmpdir):
  template = dials_data('insulin').join("insulin_1_###.img").strpath

  from xia2.Modules.Indexer.LabelitIndexer import LabelitIndexer
  from xia2.DriverExceptions.NotAvailableError import NotAvailableError
  try:
    ls = LabelitIndexer(indxr_print=True)
  except NotAvailableError:
    pytest.skip("labelit not found")
  ls.set_working_directory(run_in_tmpdir.strpath)
  from dxtbx.model.experiment_list import ExperimentListTemplateImporter
  importer = ExperimentListTemplateImporter([template])
  experiments = importer.experiments
  imageset = experiments.imagesets()[0]
  ls.add_indexer_imageset(imageset)
  ls.index()

  assert ls.get_indexer_cell() == pytest.approx((78.58, 78.58, 78.58, 90, 90, 90), abs=0.5)
  solution = ls.get_solution()
  assert solution['rmsd'] <= 0.2
  assert solution['metric'] <= 0.16
  assert solution['number'] == 22
  assert solution['lattice'] == 'cI'
  assert solution['mosaic'] <= 0.25
  assert solution['nspots'] == pytest.approx(860, abs=30)

  beam_centre = ls.get_indexer_beam_centre()
  assert beam_centre == pytest.approx((94.3416, 94.4994), abs=2e-1)
  assert ls.get_indexer_images() == [(1, 1), (22, 22), (45, 45)]
  print(ls.get_indexer_experiment_list()[0].crystal)
  print(ls.get_indexer_experiment_list()[0].detector)

  json_str = ls.as_json()
# print(json_str)
  ls1 = LabelitIndexer.from_json(string=json_str)
  ls1.index()

  print(ls.get_indexer_experiment_list()[0].crystal)
  assert ls.get_indexer_beam_centre() == ls1.get_indexer_beam_centre()
  assert ls1.get_indexer_images() == [[1, 1], [22, 22], [45, 45]] # in JSON tuples become lists
  assert ls.get_distance() == ls1.get_distance()

  ls.eliminate()
  ls1.eliminate()

  print(ls1.get_indexer_experiment_list()[0].crystal)
  assert ls.get_indexer_beam_centre() == ls1.get_indexer_beam_centre()
  assert ls.get_indexer_images() == [(1, 1), (22, 22), (45, 45)]
  assert ls1.get_indexer_images() == [[1, 1], [22, 22], [45, 45]] # in JSON tuples become lists
  assert ls.get_distance() == ls1.get_distance()

  print(ls1.get_indexer_cell())
  print(ls1.get_solution())
  assert ls.get_indexer_cell() == pytest.approx((111.11, 111.11, 68.08, 90.0, 90.0, 120.0), abs=5e-1)
  solution = ls1.get_solution()
  assert solution['rmsd'] >= 0.07, solution['rmsd']
  assert solution['metric'] == pytest.approx(0.1291, abs=1e-1)
  assert solution['lattice'] == 'hR', solution['lattice']
  assert solution['mosaic'] <= 0.3, solution['mosaic']
  assert solution['nspots'] == pytest.approx(856, abs=30)
