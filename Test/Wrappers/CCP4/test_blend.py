from __future__ import absolute_import, division, print_function

import glob
import os

import pytest
from libtbx.test_utils import approx_equal

def cmd_exists(cmd):
  import subprocess
  return subprocess.call('type ' + cmd, shell=True,
    stdout=subprocess.PIPE, stderr=subprocess.PIPE) == 0

def test_blend_wrapper(xia2_regression_build, tmpdir):
  if not cmd_exists('blend'):
    pytest.skip('blend not available')

  tmp_dir = tmpdir.strpath
  os.chdir(tmp_dir)

  blend_tutorial_dir = os.path.join(xia2_regression_build, 'blend_tutorial')
  tar_gz = os.path.join(blend_tutorial_dir, 'data02.tgz')
  import tarfile
  tar = tarfile.open(tar_gz, "r:gz")
  for tarinfo in tar:
    if tarinfo.isreg():
      # extract the file
      print("Extracting", tarinfo.name)
      tar.extract(tarinfo, path=tmp_dir)
  tar.close()

  g = sorted(glob.glob(os.path.join(tmp_dir, 'data', 'lysozyme', 'dataset_*.mtz')))

  from xia2.Wrappers.CCP4.Blend import Blend

  b = Blend()
  for f in g:
    b.add_hklin(f)
  b.analysis()

  #print("".join(b.get_all_output()))
  analysis = b.get_analysis()
  summary = b.get_summary()
  clusters = b.get_clusters()
  linkage_matrix = b.get_linkage_matrix()

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
  if 'furthest_datasets' in clusters[1]:
    del clusters[1]['furthest_datasets']
    del clusters[27]['furthest_datasets']
  assert clusters[1] == {
    'lcv': 0.05, 'alcv': 0.06, 'n_datasets': 2,
    'dataset_ids': [13, 14], 'height': 0.001
  }
  assert clusters[27] == {
    'lcv': 13.98, 'alcv': 15.44, 'n_datasets': 28,
    'dataset_ids': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17,
                    18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28],
    'height': 17.335
  }

  import numpy
  assert approx_equal(list(linkage_matrix.flat), list(numpy.array(
    [[  1.2000e+01,   1.3000e+01,   1.0000e-03,   2.0000e+00],
     [  1.0000e+00,   1.1000e+01,   6.0000e-03,   2.0000e+00],
     [  2.2000e+01,   2.6000e+01,   7.0000e-03,   2.0000e+00],
     [  0.0000e+00,   4.0000e+00,   9.0000e-03,   2.0000e+00],
     [  3.0000e+01,   2.5000e+01,   1.3000e-02,   3.0000e+00],
     [  3.1000e+01,   6.0000e+00,   1.6000e-02,   3.0000e+00],
     [  2.9000e+01,   2.0000e+00,   2.2000e-02,   3.0000e+00],
     [  1.6000e+01,   1.9000e+01,   2.4000e-02,   2.0000e+00],
     [  2.8000e+01,   2.1000e+01,   2.4000e-02,   3.0000e+00],
     [  5.0000e+00,   9.0000e+00,   2.6000e-02,   2.0000e+00],
     [  1.4000e+01,   1.7000e+01,   3.1000e-02,   2.0000e+00],
     [  3.2000e+01,   2.7000e+01,   3.2000e-02,   4.0000e+00],
     [  3.3000e+01,   1.0000e+01,   3.6000e-02,   4.0000e+00],
     [  3.7000e+01,   7.0000e+00,   6.9000e-02,   3.0000e+00],
     [  1.5000e+01,   2.4000e+01,   7.5000e-02,   2.0000e+00],
     [  3.4000e+01,   3.0000e+00,   8.4000e-02,   4.0000e+00],
     [  3.5000e+01,   3.6000e+01,   9.3000e-02,   5.0000e+00],
     [  4.0000e+01,   8.0000e+00,   1.5700e-01,   5.0000e+00],
     [  4.2000e+01,   2.3000e+01,   1.7500e-01,   3.0000e+00],
     [  3.8000e+01,   3.9000e+01,   2.0200e-01,   6.0000e+00],
     [  4.3000e+01,   4.5000e+01,   2.8100e-01,   9.0000e+00],
     [  4.6000e+01,   4.7000e+01,   4.7600e-01,   9.0000e+00],
     [  4.1000e+01,   4.8000e+01,   7.2000e-01,   1.2000e+01],
     [  4.4000e+01,   4.9000e+01,   9.9300e-01,   1.4000e+01],
     [  1.8000e+01,   2.0000e+01,   4.3150e+00,   2.0000e+00],
     [  5.0000e+01,   5.1000e+01,   7.5490e+00,   2.6000e+01],
     [  5.2000e+01,   5.3000e+01,   1.7335e+01,   2.8000e+01]]).flat))

  assert os.path.exists(b.get_dendrogram_file())
