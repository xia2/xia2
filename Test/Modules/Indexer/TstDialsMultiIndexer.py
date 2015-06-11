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
from libtbx.test_utils import approx_equal, open_tmp_directory, show_diff

try:
  dials_regression = libtbx.env.dist_path('dials_regression')
  have_dials_regression = True
except KeyError, e:
  have_dials_regression = False


def exercise_dials_multi_indexer(nproc=None):
  template = "/Volumes/touro/data/i19/4sweep/56_Reza-H2-normalhem_100K_3.75mmAl/56-RezaH2-hem_%02i_%05i.cbf"

  cwd = os.path.abspath(os.curdir)
  tmp_dir = os.path.abspath(open_tmp_directory())
  os.chdir(tmp_dir)

  cryst = None
  wav = None

  from Modules.Indexer.DialsMultiIndexer import DialsMultiIndexer
  multi_indexer = DialsMultiIndexer()
  multi_indexer.set_working_directory(tmp_dir)

  from Handlers.Phil import PhilIndex
  PhilIndex.params.xia2.settings.trust_beam_centre = True

  from Modules.Indexer.DialsIndexer import DialsIndexer
  from Schema.Interfaces.MultiIndexerSingle import multi_indexer_single_factory
  for i in range(4):
    indexer = multi_indexer_single_factory(DialsIndexer)
    indexer.set_working_directory(tmp_dir)
    indexer.setup_from_image(template %(i+1, 1))

    from Schema.XCrystal import XCrystal
    from Schema.XWavelength import XWavelength
    from Schema.XSweep import XSweep

    if cryst is None or wav is None:
      cryst = XCrystal("CRYST1", None)
      wav = XWavelength("WAVE1", cryst, indexer.get_wavelength())

    directory, image = os.path.split(indexer.get_image_name(1))
    sweep = XSweep('SWEEP1', wav, directory=directory, image=image)
    indexer.set_indexer_sweep(sweep)
    indexer.set_multi_indexer(multi_indexer)
    multi_indexer.add_indexer(indexer)

  indexer.index()

  multi_indexer.index()

  assert approx_equal(
    multi_indexer.get_indexer_cell(), (9.23, 12.60, 17.69, 90, 90, 90), eps=1e-2)
  assert multi_indexer.get_indexer_cell() == indexer.get_indexer_cell()


def run(args):
  assert len(args) <= 1, args
  if len(args) == 1:
    nproc = int(args[0])
  else:
    nproc = None
  exercise_dials_multi_indexer(nproc=nproc)
  print "OK"


if __name__ == '__main__':
  run(sys.argv[1:])
