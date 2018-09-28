from __future__ import absolute_import, division, print_function

import os
import sys

import mock
import pytest
from libtbx.test_utils import approx_equal

def exercise_dials_indexer(regression_data, tmp_dir, nproc=None):
  if nproc is not None:
    from xia2.Handlers.Phil import PhilIndex
    PhilIndex.params.xia2.settings.multiprocessing.nproc = nproc

  template = regression_data('insulin').join("insulin_1_###.img").strpath

  from xia2.Modules.Indexer.DialsIndexer import DialsIndexer
  indexer = DialsIndexer()
  indexer.set_working_directory(tmp_dir)
  from dxtbx.datablock import DataBlockTemplateImporter
  importer = DataBlockTemplateImporter([template])
  datablocks = importer.datablocks
  imageset = datablocks[0].extract_imagesets()[0]
  indexer.add_indexer_imageset(imageset)

  from xia2.Schema.XCrystal import XCrystal
  from xia2.Schema.XWavelength import XWavelength
  from xia2.Schema.XSweep import XSweep
  from xia2.Schema.XSample import XSample
  cryst = XCrystal("CRYST1", None)
  wav = XWavelength("WAVE1", cryst, imageset.get_beam().get_wavelength())
  samp = XSample("X1", cryst)
  directory, image = os.path.split(imageset.get_path(1))
  sweep = XSweep('SWEEP1', wav, samp, directory=directory, image=image)
  indexer.set_indexer_sweep(sweep)

  indexer.index()

  assert approx_equal(indexer.get_indexer_cell(),
                      (78.14, 78.14, 78.14, 90, 90, 90), eps=1e-1)
  solution = indexer.get_solution()
  assert approx_equal(solution['rmsd'], 0.041, eps=1e-2)
  assert approx_equal(solution['metric'], 0.027, eps=1e-2)
  assert solution['number'] == 22
  assert solution['lattice'] == 'cI'

  beam_centre = indexer.get_indexer_beam_centre()
  assert approx_equal(beam_centre, (94.4223, 94.5097), eps=1e-2)
  print(indexer.get_indexer_experiment_list()[0].crystal)
  print(indexer.get_indexer_experiment_list()[0].detector)

  # test serialization of indexer
  json_str = indexer.as_json()
  #print(json_str)
  indexer2 = DialsIndexer.from_json(string=json_str)
  indexer2.index()

  assert approx_equal(indexer.get_indexer_cell(), indexer2.get_indexer_cell())
  assert approx_equal(indexer.get_indexer_beam_centre(),
                      indexer2.get_indexer_beam_centre())

  indexer.eliminate()
  indexer2.eliminate()

  assert approx_equal(indexer.get_indexer_cell(), indexer2.get_indexer_cell())
  assert indexer.get_indexer_lattice() == 'hR'
  assert indexer2.get_indexer_lattice() == 'hR'

@pytest.mark.slow
def test_xds_indexer_serial(ccp4, regression_data, run_in_tmpdir):
  with mock.patch.object(sys, 'argv', []):
    exercise_dials_indexer(regression_data, run_in_tmpdir.strpath, nproc=1)
