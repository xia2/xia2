from __future__ import division

import os
import glob

import libtbx.load_env
from libtbx import easy_run
#from libtbx.test_utils import approx_equal
from libtbx.test_utils import open_tmp_directory

xia2_regression = libtbx.env.under_build('xia2_regression')

def cmd_exists(cmd):
  import subprocess
  return subprocess.call('type ' + cmd, shell=True,
    stdout=subprocess.PIPE, stderr=subprocess.PIPE) == 0

def exercise_blend_wrapper():
  if not cmd_exists('blend'):
    print "Skipping exercise_blend_wrapper(): blend not available"

  if xia2_regression is None:
    print "Skipping exercise_blend_wrapper(): xia2_regression not present."

  cwd = os.path.abspath(os.curdir)
  tmp_dir = os.path.abspath(open_tmp_directory())
  os.chdir(tmp_dir)

  blend_tutorial_dir = os.path.join(xia2_regression, 'blend_tutorial')
  tar_gz = os.path.join(blend_tutorial_dir, 'data02.tgz')
  import tarfile
  tar = tarfile.open(tar_gz, "r:gz")
  for tarinfo in tar:
    if tarinfo.isreg():
      # extract the file
      print "Extracting", tarinfo.name
      tar.extract(tarinfo, path=tmp_dir)
  tar.close()

  g = glob.glob(os.path.join(tmp_dir, 'data', 'lysozyme', 'dataset_*.mtz'))

  from xia2.Wrappers.CCP4.Blend import Blend

  b = Blend()
  for f in g:
    b.add_hklin(f)
  b.analysis()

  #print "".join(b.get_all_output())
  analysis = b.get_analysis()
  summary = b.get_summary()
  clusters = b.get_clusters()

  assert analysis.keys() == range(1, 29)
  assert analysis[1] == {
    'start_image': 1, 'radiation_damage_cutoff': 50, 'd_min': 1.739,
    'final_image': 50,
    'input_file': os.path.join(tmp_dir, 'data', 'lysozyme', 'dataset_001.mtz')
  }, analysis[1]

  assert summary.keys() == range(1, 29)
  assert summary[1] == {
    'volume': 238834.27, 'distance': 308.73, 'd_max': 24.854,
    'cell': (78.595, 78.595, 38.664, 90.0, 90.0, 90.0),
    'd_min': 1.692, 'mosaicity': 0.0, 'wavelength': 0.9173
  }

  assert clusters.keys() == range(1, 28)
  assert clusters[1] == {
    'lcv': 0.05, 'alcv': 0.06, 'n_datasets': 2,
    'dataset_ids': [13, 14], 'height': 0.001
  }
  assert clusters[27] == {
    'lcv': 13.98, 'alcv': 15.44, 'n_datasets': 28,
    'dataset_ids': [19, 21, 8, 6, 10, 4, 3, 2, 12, 9, 11, 7, 1, 5, 17, 20,
                    22, 13, 14, 24, 16, 25, 15, 18, 28, 26, 23, 27],
    'height': 17.335
  }


def run(args):
  exercise_blend_wrapper()

if __name__ == '__main__':
  import sys
  from libtbx.utils import show_times_at_exit
  show_times_at_exit()
  run(sys.argv[1:])
