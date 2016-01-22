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


def exercise_dials_indexer(nproc=None):
  if not have_dials_regression:
    print "Skipping exercise_dials_indexer(): dials_regression not configured"
    return

  if nproc is not None:
    from Handlers.Flags import Flags
    Flags.set_parallel(nproc)

  xia2_demo_data = os.path.join(dials_regression, "xia2_demo_data")
  template = os.path.join(xia2_demo_data, "insulin_1_###.img")

  cwd = os.path.abspath(os.curdir)
  tmp_dir = os.path.abspath(open_tmp_directory())
  os.chdir(tmp_dir)

  from Modules.Indexer.DialsIndexer import DialsIndexer
  indexer = DialsIndexer()
  indexer.set_working_directory(tmp_dir)
  from dxtbx.datablock import DataBlockTemplateImporter
  importer = DataBlockTemplateImporter([template])
  datablocks = importer.datablocks
  imageset = datablocks[0].extract_imagesets()[0]
  indexer.add_indexer_imageset(imageset)

  from Schema.XCrystal import XCrystal
  from Schema.XWavelength import XWavelength
  from Schema.XSweep import XSweep
  from Schema.XSample import XSample
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
  assert indexer.get_indexer_images() == [(1,45)]
  print indexer.get_indexer_experiment_list()[0].crystal
  print indexer.get_indexer_experiment_list()[0].detector

  # test serialization of indexer
  json_str = indexer.as_json()
  #print json_str
  indexer2 = DialsIndexer.from_json(string=json_str)
  indexer2.index()

  assert approx_equal(indexer.get_indexer_cell(), indexer2.get_indexer_cell())
  assert approx_equal(
    indexer.get_indexer_beam_centre(), indexer2.get_indexer_beam_centre())
  assert approx_equal(
    indexer.get_indexer_images(), indexer2.get_indexer_images())

  indexer.eliminate()
  indexer2.eliminate()

  assert approx_equal(indexer.get_indexer_cell(), indexer2.get_indexer_cell())
  assert indexer.get_indexer_lattice() == 'hR'
  assert indexer2.get_indexer_lattice() == 'hR'


def run(args):
  assert len(args) <= 1, args
  if len(args) == 1:
    nproc = int(args[0])
  else:
    nproc = None
  exercise_dials_indexer(nproc=nproc)
  print "OK"


if __name__ == '__main__':
  run(sys.argv[1:])
