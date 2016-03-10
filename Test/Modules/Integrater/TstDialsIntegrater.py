import os
import sys

import libtbx.load_env
from libtbx import easy_run
from libtbx.test_utils import approx_equal, open_tmp_directory, show_diff

try:
  dials_regression = libtbx.env.dist_path('dials_regression')
  have_dials_regression = True
except KeyError, e:
  have_dials_regression = False


def exercise_dials_integrater(nproc=None):
  if not have_dials_regression:
    print "Skipping exercise_dials_integrater(): dials_regression not configured"
    return

  if nproc is not None:
    from xia2.Handlers.Flags import Flags
    Flags.set_parallel(nproc)

  xia2_demo_data = os.path.join(dials_regression, "xia2_demo_data")
  template = os.path.join(xia2_demo_data, "insulin_1_###.img")

  cwd = os.path.abspath(os.curdir)
  tmp_dir = os.path.abspath(open_tmp_directory())
  os.chdir(tmp_dir)

  from xia2.Modules.Indexer.DialsIndexer import DialsIndexer
  from xia2.Modules.Integrater.DialsIntegrater import DialsIntegrater
  from dxtbx.datablock import DataBlockTemplateImporter
  indexer = DialsIndexer()
  indexer.set_working_directory(tmp_dir)
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

  from xia2.Modules.Refiner.DialsRefiner import DialsRefiner
  refiner = DialsRefiner()
  refiner.set_working_directory(tmp_dir)
  refiner.add_refiner_indexer(sweep.get_epoch(1), indexer)
  #refiner.refine()

  integrater = DialsIntegrater()
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
  assert abs(mtz_object.n_reflections() - 48117) < 100, mtz_object.n_reflections()
  assert mtz_object.column_labels() == [
    'H', 'K', 'L', 'M_ISYM', 'BATCH', 'IPR', 'SIGIPR', 'I', 'SIGI',
    'FRACTIONCALC', 'XDET', 'YDET', 'ROT', 'LP', 'DQE']

  assert integrater.get_integrater_wedge() == (1, 45)
  assert approx_equal(integrater.get_integrater_cell(),
                      (78.14, 78.14, 78.14, 90, 90, 90), eps=1e-1)

  # test serialization of integrater
  json_str = integrater.as_json()
  #print json_str
  integrater2 = DialsIntegrater.from_json(string=json_str)
  integrater2.set_integrater_sweep(sweep, reset=False)
  integrater2_intensities = integrater.get_integrater_intensities()
  assert integrater2_intensities == integrater_intensities

  integrater2.set_integrater_finish_done(False)
  integrater2_intensities = integrater2.get_integrater_intensities()
  assert os.path.exists(integrater2_intensities)
  reader = any_reflection_file(integrater2_intensities)
  assert reader.file_type() == "ccp4_mtz"
  mtz_object = reader.file_content()
  assert abs(mtz_object.n_reflections() - 48117) < 100, mtz_object.n_reflections()

  integrater2.set_integrater_done(False)
  integrater2_intensities = integrater2.get_integrater_intensities()
  assert os.path.exists(integrater2_intensities)
  reader = any_reflection_file(integrater2_intensities)
  assert reader.file_type() == "ccp4_mtz"
  mtz_object = reader.file_content()
  assert abs(mtz_object.n_reflections() - 48117) < 100, mtz_object.n_reflections()

  integrater2.set_integrater_prepare_done(False)
  integrater2_intensities = integrater2.get_integrater_intensities()
  assert os.path.exists(integrater2_intensities)
  reader = any_reflection_file(integrater2_intensities)
  assert reader.file_type() == "ccp4_mtz"
  mtz_object = reader.file_content()
  assert abs(mtz_object.n_reflections() - 48117) < 100, mtz_object.n_reflections()


def run(args):
  assert len(args) <= 1, args
  if len(args) == 1:
    nproc = int(args[0])
  else:
    nproc = None
  exercise_dials_integrater(nproc=nproc)
  print "OK"


if __name__ == '__main__':
  run(sys.argv[1:])
