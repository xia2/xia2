import os
import sys
if not os.environ.has_key('XIA2CORE_ROOT'):
  raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.environ.has_key('XIA2_ROOT'):
  raise RuntimeError, 'XIA2_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'],
                    'Python') in sys.path:
  sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                               'Python'))

if not os.environ['XIA2_ROOT'] in sys.path:
  sys.path.append(os.environ['XIA2_ROOT'])

import libtbx.load_env
from libtbx import easy_run
from libtbx.test_utils import show_diff
from libtbx.test_utils import open_tmp_directory
try:
  dials_regression = libtbx.env.dist_path('dials_regression')
  have_dials_regression = True
except KeyError, e:
  have_dials_regression = False


def work():
  if not have_dials_regression:
    raise RuntimeError, 'dials_regression not available'

  xia2_demo_data = os.path.join(dials_regression, "xia2_demo_data")
  template = os.path.join(xia2_demo_data, "insulin_1_%03i.img")

  cwd = os.path.abspath(os.curdir)
  tmp_dir1 = os.path.abspath(open_tmp_directory())
  os.chdir(tmp_dir1)

  from Wrappers.CCP4.Mosflm import Mosflm
  m1 = Mosflm()
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

  return

if __name__ == '__main__':
  work()
