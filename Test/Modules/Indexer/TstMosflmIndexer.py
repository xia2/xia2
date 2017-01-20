from __future__ import absolute_import, division

import os

import libtbx.load_env
from libtbx.test_utils import approx_equal, open_tmp_directory

try:
  dials_regression = libtbx.env.dist_path('dials_regression')
  have_dials_regression = True
except KeyError, e:
  have_dials_regression = False

from xia2.Handlers.Streams import Debug, Stdout
Debug.join(Stdout)

def exercise_mosflm_indexer():
  if not have_dials_regression:
    print "Skipping exercise_mosflm_indexer(): dials_regression not configured"
    return

  xia2_demo_data = os.path.join(dials_regression, "xia2_demo_data")
  template = os.path.join(xia2_demo_data, "insulin_1_###.img")

  cwd = os.path.abspath(os.curdir)
  tmp_dir = os.path.abspath(open_tmp_directory())
  os.chdir(tmp_dir)

  from xia2.Modules.Indexer.MosflmIndexer import MosflmIndexer
  indexer = MosflmIndexer()
  indexer.set_working_directory(tmp_dir)
  from dxtbx.datablock import DataBlockTemplateImporter
  importer = DataBlockTemplateImporter([template])
  datablocks = importer.datablocks
  imageset = datablocks[0].extract_imagesets()[0]
  indexer.add_indexer_imageset(imageset)

  indexer.index()

  assert approx_equal(indexer.get_indexer_cell(),
                      (78.6657, 78.6657, 78.6657, 90.0, 90.0, 90.0), eps=1e-3)
  experiment = indexer.get_indexer_experiment_list()[0]
  sgi = experiment.crystal.get_space_group().info()
  assert sgi.type().number() == 197

  beam_centre = indexer.get_indexer_beam_centre()
  assert approx_equal(beam_centre, (94.34, 94.57), eps=1e-2)
  assert indexer.get_indexer_images() == [(1, 1), (22, 22), (45, 45)]
  print indexer.get_indexer_experiment_list()[0].crystal
  print indexer.get_indexer_experiment_list()[0].detector

  # test serialization of indexer
  json_str = indexer.as_json()
  print json_str
  indexer2 = MosflmIndexer.from_json(string=json_str)
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


def run():
  exercise_mosflm_indexer()
  print "OK"


if __name__ == '__main__':
  run()
