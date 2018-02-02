from __future__ import absolute_import, division, print_function

import os
import sys

import mock
import pytest

def test_mosflm_indexer(dials_regression, tmpdir):
  template = os.path.join(dials_regression, "xia2_demo_data", "insulin_1_###.img")
  tmpdir.chdir()

  from xia2.Modules.Indexer.MosflmIndexer import MosflmIndexer
  indexer = MosflmIndexer()
  indexer.set_working_directory(tmpdir.strpath)
  from dxtbx.datablock import DataBlockTemplateImporter
  importer = DataBlockTemplateImporter([template])
  datablocks = importer.datablocks
  imageset = datablocks[0].extract_imagesets()[0]
  indexer.add_indexer_imageset(imageset)

  with mock.patch.object(sys, 'argv', []): # otherwise indexing fails when running pytest with '--runslow'
    indexer.index()

  assert indexer.get_indexer_cell() == pytest.approx((78.6657, 78.6657, 78.6657, 90.0, 90.0, 90.0), abs=1e-3)
  experiment = indexer.get_indexer_experiment_list()[0]
  sgi = experiment.crystal.get_space_group().info()
  assert sgi.type().number() == 197

  beam_centre = indexer.get_indexer_beam_centre()
  assert beam_centre == pytest.approx((94.34, 94.57), abs=1e-2)
  assert indexer.get_indexer_images() == [(1, 1), (22, 22), (45, 45)]
  print(indexer.get_indexer_experiment_list()[0].crystal)
  print(indexer.get_indexer_experiment_list()[0].detector)

  # test serialization of indexer
  json_str = indexer.as_json()
  print(json_str)
  indexer2 = MosflmIndexer.from_json(string=json_str)
  indexer2.index()

  assert indexer.get_indexer_cell() == pytest.approx(indexer2.get_indexer_cell(), abs=1e-6)
  assert indexer.get_indexer_beam_centre() == pytest.approx(indexer2.get_indexer_beam_centre(), abs=1e-6)
  assert indexer2.get_indexer_images() == [[1, 1], [22, 22], [45, 45]] # coming from json these are now lists

  indexer.eliminate()
  indexer2.eliminate()

  assert indexer.get_indexer_cell() == pytest.approx(indexer2.get_indexer_cell(), abs=1e-6)
  assert indexer.get_indexer_lattice() == 'hR'
  assert indexer2.get_indexer_lattice() == 'hR'
