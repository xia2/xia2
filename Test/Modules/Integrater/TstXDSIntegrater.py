from __future__ import absolute_import, division

import os
import sys

import libtbx.load_env
from libtbx.test_utils import approx_equal, open_tmp_directory

try:
  dials_regression = libtbx.env.dist_path('dials_regression')
  have_dials_regression = True
except KeyError, e:
  have_dials_regression = False


def exercise_xds_integrater(nproc=None):
  if not have_dials_regression:
    print "Skipping exercise_xds_integrater(): dials_regression not configured"
    return

  if nproc is not None:
    from xia2.Handlers.Phil import PhilIndex
    PhilIndex.params.xia2.settings.multiprocessing.nproc = nproc

  xia2_demo_data = os.path.join(dials_regression, "xia2_demo_data")
  template = os.path.join(xia2_demo_data, "insulin_1_###.img")

  cwd = os.path.abspath(os.curdir)
  tmp_dir = os.path.abspath(open_tmp_directory())
  os.chdir(tmp_dir)

  from xia2.Modules.Indexer.XDSIndexer import XDSIndexer
  from xia2.Modules.Integrater.XDSIntegrater import XDSIntegrater
  indexer = XDSIndexer()
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
  wav = XWavelength("WAVE1", cryst, indexer.get_wavelength())
  samp = XSample("X1", cryst)
  directory, image = os.path.split(imageset.get_path(1))
  sweep = XSweep('SWEEP1', wav, samp, directory=directory, image=image)
  indexer.set_indexer_sweep(sweep)

  from xia2.Modules.Refiner.XDSRefiner import XDSRefiner
  refiner = XDSRefiner()
  refiner.set_working_directory(tmp_dir)
  refiner.add_refiner_indexer(sweep.get_epoch(1), indexer)
  #refiner.refine()

  integrater = XDSIntegrater()
  integrater.set_working_directory(tmp_dir)
  integrater.setup_from_image(imageset.get_path(1))
  integrater.set_integrater_refiner(refiner)
  #integrater.set_integrater_indexer(indexer)
  integrater.set_integrater_sweep(sweep)
  integrater.integrate()

  integrater_intensities = integrater.get_integrater_intensities()
  assert os.path.exists(integrater_intensities)
  from iotbx.reflection_file_reader import any_reflection_file
  reader = any_reflection_file(integrater_intensities)
  assert reader.file_type() == "ccp4_mtz"
  mtz_object = reader.file_content()
  assert approx_equal(mtz_object.n_reflections(), 50000, eps=400)
  assert mtz_object.column_labels() == [
    'H', 'K', 'L', 'M_ISYM', 'BATCH', 'I', 'SIGI', 'FRACTIONCALC',
    'XDET', 'YDET', 'ROT', 'LP', 'FLAG']

  corrected_intensities = integrater.get_integrater_corrected_intensities()
  assert os.path.exists(corrected_intensities)
  from iotbx.reflection_file_reader import any_reflection_file
  reader = any_reflection_file(corrected_intensities)
  assert reader.file_type() == "xds_ascii"
  ma = reader.as_miller_arrays(merge_equivalents=False)[0]
  assert approx_equal(ma.size(), 50000, eps=400)

  #assert integrater.get_integrater_reindex_operator() == 'x,z,-y'
  assert integrater.get_integrater_wedge() == (1, 45)
  assert approx_equal(integrater.get_integrater_cell(),
                      [78.066, 78.066, 78.066, 90, 90, 90], eps=3e-2)
  assert approx_equal(integrater.get_integrater_mosaic_min_mean_max(),
                      (0.180, 0.180, 0.180), eps=2e-3)

  # test serialization of integrater
  json_str = integrater.as_json()
  #print json_str
  integrater2 = XDSIntegrater.from_json(string=json_str)
  integrater2.set_integrater_sweep(sweep, reset=False)
  integrater2_intensities = integrater.get_integrater_intensities()
  assert integrater2_intensities == integrater_intensities

  integrater2.set_integrater_finish_done(False)
  integrater2_intensities = integrater2.get_integrater_intensities()
  assert os.path.exists(integrater2_intensities)
  reader = any_reflection_file(integrater2_intensities)
  assert reader.file_type() == "ccp4_mtz"
  mtz_object = reader.file_content()
  assert approx_equal(mtz_object.n_reflections(), 50000, eps=400)

  integrater2.set_integrater_done(False)
  integrater2_intensities = integrater2.get_integrater_intensities()
  assert os.path.exists(integrater2_intensities)
  reader = any_reflection_file(integrater2_intensities)
  assert reader.file_type() == "ccp4_mtz"
  mtz_object = reader.file_content()
  assert approx_equal(mtz_object.n_reflections(), 50000, eps=350)

  integrater2.set_integrater_prepare_done(False)
  integrater2_intensities = integrater2.get_integrater_intensities()
  assert os.path.exists(integrater2_intensities)
  reader = any_reflection_file(integrater2_intensities)
  assert reader.file_type() == "ccp4_mtz"
  mtz_object = reader.file_content()
  assert approx_equal(mtz_object.n_reflections(), 50000, eps=300)


def run(args):
  assert len(args) <= 1, args
  if len(args) == 1:
    nproc = int(args[0])
  else:
    nproc = None
  exercise_xds_integrater(nproc=nproc)
  print "OK"


if __name__ == '__main__':
  run(sys.argv[1:])
