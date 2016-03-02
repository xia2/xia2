import os
import sys

import libtbx.load_env
from libtbx import easy_run
from libtbx.test_utils import show_diff
from libtbx.test_utils import open_tmp_directory
try:
  dials_regression = libtbx.env.dist_path('dials_regression')
  have_dials_regression = True
except KeyError, e:
  have_dials_regression = False

from xia2.Handlers.Streams import Debug, Stdout
Debug.join(Stdout)

def exercise_mosflm_index():
  if not have_dials_regression:
    print 'SKIP: dials_regression not configured'
    exit(0)

  xia2_demo_data = os.path.join(dials_regression, "xia2_demo_data")
  template = os.path.join(xia2_demo_data, "insulin_1_%03i.img")

  cwd = os.path.abspath(os.curdir)
  tmp_dir1 = os.path.abspath(open_tmp_directory())
  os.chdir(tmp_dir1)

  from xia2.Modules.Indexer.MosflmIndexer import MosflmIndexer
  m1 = MosflmIndexer()
  m1.set_working_directory(tmp_dir1)
  m1.setup_from_image(template % 1)
  m1.index()

  os.chdir(cwd)
  tmp_dir2 = os.path.abspath(open_tmp_directory())
  os.chdir(tmp_dir2)

  from Original import Mosflm
  m2 = Mosflm()
  m2.set_working_directory(tmp_dir2)
  m2.setup_from_image(template % 1)
  m2.index()

  assert m1.get_indexer_beam_centre() == m2.get_indexer_beam_centre()
  assert m1.get_indexer_distance() == m2.get_indexer_distance()
  assert m1.get_indexer_cell() == m2.get_indexer_cell()
  assert m1.get_indexer_lattice() == m2.get_indexer_lattice()
  assert m1.get_indexer_mosaic() == m2.get_indexer_mosaic()

  os.chdir(cwd)

  return


def exercise_mosflm_integrate(nproc):
  if not have_dials_regression:
    raise RuntimeError, 'dials_regression not available'

  xia2_demo_data = os.path.join(dials_regression, "xia2_demo_data")
  template = os.path.join(xia2_demo_data, "insulin_1_%03i.img")

  from xia2.Schema.XCrystal import XCrystal
  from xia2.Schema.XWavelength import XWavelength
  from xia2.Schema.XSweep import XSweep
  from xia2.Schema.XSample import XSample

  from xia2.Handlers.Flags import Flags
  Flags.set_parallel(nproc)

  cwd = os.path.abspath(os.curdir)
  tmp_dir1 = os.path.abspath(open_tmp_directory())
  os.chdir(tmp_dir1)

  from xia2.Modules.Integrater.MosflmIntegrater import MosflmIntegrater
  from xia2.Modules.Refiner.MosflmRefiner import MosflmRefiner
  from xia2.Modules.Indexer.MosflmIndexer import MosflmIndexer
  indexer = MosflmIndexer()
  indexer.set_working_directory(tmp_dir1)
  indexer.setup_from_image(template % 1)
  refiner = MosflmRefiner()
  refiner.add_refiner_indexer(1, indexer)
  m1 = MosflmIntegrater()
  m1.set_working_directory(tmp_dir1)
  m1.setup_from_image(template % 1)
  cryst = XCrystal("CRYST1", None)
  wav = XWavelength("WAVE1", cryst, m1.get_wavelength())
  samp = XSample("X1", cryst)
  directory, image = os.path.split(template %1)
  sweep = XSweep('SWEEP1', wav, samp, directory=directory, image=image)
  indexer.set_indexer_sweep(sweep)
  m1.set_integrater_sweep(sweep)
  m1.set_integrater_refiner(refiner)
  m1.set_frame_wedge(1, 45)
  m1.set_integrater_wedge(1, 45)
  m1.integrate()

  os.chdir(cwd)
  tmp_dir2 = os.path.abspath(open_tmp_directory())
  os.chdir(tmp_dir2)

  from Original import Mosflm
  m2 = Mosflm()
  m2.set_working_directory(tmp_dir2)
  m2.setup_from_image(template % 1)
  m2.set_integrater_indexer(m2)
  m2.set_integrater_sweep(sweep)
  m2.set_frame_wedge(1, 45)
  m2.set_integrater_wedge(1, 45)
  m2.integrate()

  from libtbx.test_utils import approx_equal
  assert approx_equal(m1.get_integrater_cell(), m2.get_integrater_cell(),
                      eps=0.02)

  assert approx_equal(indexer.get_indexer_distance(), m2.get_indexer_distance(),
                      eps=0.2)

  assert approx_equal(m1.get_integrater_cell(),
                      m2.get_integrater_cell(), eps=0.02)
  assert indexer.get_indexer_lattice() == m2.get_indexer_lattice()
  assert approx_equal(indexer.get_indexer_mosaic(), m2.get_indexer_mosaic(),
                      eps=0.01)

  m1_mtz = m1.get_integrater_intensities()
  m2_mtz = m2.get_integrater_intensities()

  from iotbx.reflection_file_reader import any_reflection_file
  mas_1 = any_reflection_file(m1_mtz).as_miller_arrays()
  mas_2 = any_reflection_file(m2_mtz).as_miller_arrays()

  assert len(mas_1) == len(mas_2)
  for ma1, ma2 in zip(mas_1, mas_2):
    assert ma1.size() == ma2.size()
    assert ma1.space_group() == ma2.space_group()
    assert ma1.unit_cell().parameters() == ma2.unit_cell().parameters()
    assert ma1.indices() == ma2.indices()
    assert ma1.data() == ma2.data()
    assert ma1.sigmas() == ma2.sigmas()

  return

def run():
  exercise_mosflm_index()
  exercise_mosflm_integrate(nproc=1)
  exercise_mosflm_integrate(nproc=2)
  print "OK"

if __name__ == '__main__':
  run()
