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
  #dials_regression = libtbx.env.dist_path('dials_regression')
  xia2_regression = libtbx.env.under_build("xia2_regression")
  have_xia2_regression = True
except KeyError, e:
  have_xia2_regression = False


def exercise_dials_refiner(nproc=None):
  if not have_xia2_regression:
    print "Skipping exercise_dials_refiner(): xia2_regression not configured"
    return

  if nproc is not None:
    from Handlers.Flags import Flags
    Flags.set_parallel(nproc)

  xia2_demo_data = os.path.join(xia2_regression, "test_data", "mad_example")
  template = os.path.join(xia2_demo_data, "12287_1_E%i_%03i.img")

  cwd = os.path.abspath(os.curdir)
  tmp_dir = os.path.abspath(open_tmp_directory())
  os.chdir(tmp_dir)

  from Modules.Indexer.DialsIndexer import DialsIndexer
  from Modules.Refiner.DialsRefiner import DialsRefiner
  from Modules.Integrater.DialsIntegrater import DialsIntegrater
  indexer1 = DialsIndexer()
  indexer1.set_working_directory(tmp_dir)
  indexer1.setup_from_image(template %(1,1))

  from Schema.XCrystal import XCrystal
  from Schema.XWavelength import XWavelength
  from Schema.XSweep import XSweep
  from Schema.XSample import XSample
  cryst = XCrystal("CRYST1", None)
  wav1 = XWavelength("WAVE1", cryst, indexer1.get_wavelength())
  samp1 = XSample("X1", cryst)
  directory, image = os.path.split(template %(1,1))
  sweep1 = XSweep('SWEEP1', wav1, samp1, directory=directory, image=image)
  indexer1.set_indexer_sweep(sweep1)

  indexer2 = DialsIndexer()
  indexer2.set_working_directory(tmp_dir)
  indexer2.setup_from_image(template %(2,1))
  wav2 = XWavelength("WAVE2", cryst, indexer2.get_wavelength())
  samp2 = XSample("X2", cryst)
  directory, image = os.path.split(template %(2,1))
  sweep2 = XSweep('SWEEP2', wav2, samp2, directory=directory, image=image)
  indexer2.set_indexer_sweep(sweep2)

  refiner = DialsRefiner()
  refiner.set_working_directory(tmp_dir)
  refiner.add_refiner_indexer(indexer1)
  refiner.add_refiner_indexer(indexer2)

  refined_experiment_list = refiner.get_refined_experiment_list()

  assert refined_experiment_list is not None
  assert len(refined_experiment_list.detectors()) == 1
  refined_detector = refined_experiment_list[0].detector

  # test serialization of refiner
  json_str = refiner.as_json()
  #print json_str
  refiner2 = DialsRefiner.from_json(string=json_str)
  refined_expts_2 = refiner2.get_refined_experiment_list()
  assert refined_expts_2[0].detector == refined_detector

  refiner2.set_refiner_finish_done(False)
  refined_expts_2 = refiner2.get_refined_experiment_list()
  assert refined_expts_2[0].detector == refined_detector

  refiner2.set_refiner_done(False)
  refined_expts_2 = refiner2.get_refined_experiment_list()
  assert refined_expts_2[0].detector == refined_detector

  refiner2.set_refiner_prepare_done(False)
  refined_expts_2 = refiner2.get_refined_experiment_list()
  assert refined_expts_2[0].detector == refined_detector

  assert (indexer1.get_indexer_experiment_list()[0].detector !=
          indexer2.get_indexer_experiment_list()[0].detector)
  assert (indexer1.get_indexer_experiment_list()[0].beam !=
          indexer2.get_indexer_experiment_list()[0].beam)

  indexer1.set_indexer_experiment_list(refined_experiment_list[0:1])
  indexer2.set_indexer_experiment_list(refined_experiment_list[1:2])

  assert (indexer1.get_indexer_experiment_list()[0].detector ==
          indexer2.get_indexer_experiment_list()[0].detector)
  assert (indexer1.get_indexer_experiment_list()[0].goniometer ==
          indexer2.get_indexer_experiment_list()[0].goniometer)

  #integrater1 = DialsIntegrater()
  #integrater1.set_working_directory(tmp_dir)
  #integrater1.setup_from_image(template %(1,1))
  #integrater1.set_integrater_indexer(indexer1)
  #integrater1.set_integrater_sweep(sweep1)
  #integrater1.integrate()

  #integrater2 = DialsIntegrater()
  #integrater2.set_working_directory(tmp_dir)
  #integrater2.setup_from_image(template %(1,1))
  #integrater2.set_integrater_indexer(indexer1)
  #integrater2.set_integrater_sweep(sweep1)
  #integrater2.integrate()


def run(args):
  assert len(args) <= 1, args
  if len(args) == 1:
    nproc = int(args[0])
  else:
    nproc = None
  exercise_dials_refiner(nproc=nproc)
  print "OK"


if __name__ == '__main__':
  run(sys.argv[1:])

