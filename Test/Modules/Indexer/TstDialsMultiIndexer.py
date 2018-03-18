from __future__ import absolute_import, division

import os
import sys

import libtbx.load_env
from libtbx.test_utils import approx_equal, open_tmp_directory

try:
  dials_regression = libtbx.env.dist_path('dials_regression')
  have_dials_regression = True
except KeyError:
  have_dials_regression = False

def exercise_dials_multi_indexer(nproc=None):
  template = "/Volumes/touro/data/i19/4sweep/56_Reza-H2-normalhem_100K_3.75mmAl/56-RezaH2-hem_%02i_#####.cbf"

  cwd = os.path.abspath(os.curdir)
  tmp_dir = os.path.abspath(open_tmp_directory())
  os.chdir(tmp_dir)

  cryst = None
  wav = None
  samp = None

  from xia2.Handlers.Phil import PhilIndex
  PhilIndex.params.xia2.settings.trust_beam_centre = True

  from xia2.Modules.Indexer.DialsIndexer import DialsIndexer

  from xia2.Modules.Indexer.DialsIndexer import DialsIndexer
  indexer = DialsIndexer()
  indexer.set_working_directory(tmp_dir)
  for i in range(4):
    from dxtbx.datablock import DataBlockTemplateImporter
    importer = DataBlockTemplateImporter([template % (i + 1)])
    datablocks = importer.datablocks
    imageset = datablocks[0].extract_imagesets()[0]
    indexer.add_indexer_imageset(imageset)

    from xia2.Schema.XCrystal import XCrystal
    from xia2.Schema.XWavelength import XWavelength
    from xia2.Schema.XSweep import XSweep
    from xia2.Schema.XSample import XSample

    if cryst is None or wav is None:
      cryst = XCrystal("CRYST1", None)
      wav = XWavelength("WAVE1", cryst, imageset.get_beam().get_wavelength())
      samp = XSample("X1", cryst)

    directory, image = os.path.split(imageset.get_path(1))
    sweep = XSweep('SWEEP1', wav, samp, directory=directory, image=image)
    indexer.add_indexer_sweep(sweep)

  indexer.index()

  assert approx_equal(indexer.get_indexer_cell(),
                      (9.088, 12.415, 17.420, 90.000, 90.000, 90.000), eps=1e-2)

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
