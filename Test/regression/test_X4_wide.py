from __future__ import absolute_import, division, print_function

import os

import procrunner
import pytest
import xia2.Test.regression

@pytest.fixture(scope="session")
def data_dir(xia2_regression_build):
  data_dir = os.path.join(xia2_regression_build, "test_data", "X4_wide")
  if not os.path.exists(data_dir):
    pytest.skip('X4_wide data not found. Please run xia2_regression.fetch_test_data first')
  return data_dir

def split_xinfo(data_dir, tmpdir):
  split_xinfo_template = """/
BEGIN PROJECT AUTOMATIC
BEGIN CRYSTAL DEFAULT

BEGIN WAVELENGTH NATIVE
WAVELENGTH 0.979500
END WAVELENGTH NATIVE

BEGIN SWEEP SWEEP1
WAVELENGTH NATIVE
DIRECTORY {0}
IMAGE X4_wide_M1S4_2_0001.cbf
START_END 1 40
BEAM 219.84 212.65
END SWEEP SWEEP1

BEGIN SWEEP SWEEP2
WAVELENGTH NATIVE
DIRECTORY {0}
IMAGE X4_wide_M1S4_2_0001.cbf
START_END 45 90
BEAM 219.84 212.65
END SWEEP SWEEP2

END CRYSTAL DEFAULT
END PROJECT AUTOMATIC
"""
  xinfo_file = tmpdir / 'split.xinfo'
  xinfo_file.write(split_xinfo_template.format(data_dir.replace('\\', '\\\\')))
  return xinfo_file.strpath

@pytest.mark.regression
def test_dials(data_dir, tmpdir, ccp4):
  command_line = [
      'xia2', 'pipeline=dials', 'nproc=1',
      'trust_beam_centre=True', 'read_all_image_headers=False',
      'truncate=cctbx', data_dir,
  ]
  with tmpdir.as_cwd():
    result = procrunner.run(command_line)
  success, issues = xia2.Test.regression.check_result('X4_wide.dials', result, tmpdir, ccp4)
  assert success, issues

@pytest.mark.regression
def test_dials_split(data_dir, tmpdir, ccp4):
  command_line = [
      'xia2', 'pipeline=dials', 'nproc=1', 'njob=2', 'mode=parallel',
      'trust_beam_centre=True', 'xinfo=%s' % split_xinfo(data_dir, tmpdir),
  ]
  with tmpdir.as_cwd():
    result = procrunner.run(command_line)
  success, issues = xia2.Test.regression.check_result('X4_wide_split.dials', result, tmpdir, ccp4)
  assert success, issues

@pytest.mark.regression
def test_xds(data_dir, tmpdir, ccp4, xds):
  command_line = [
      'xia2', 'pipeline=3di', 'nproc=1', 'trust_beam_centre=True',
      'read_all_image_headers=False', data_dir,
  ]
  with tmpdir.as_cwd():
    result = procrunner.run(command_line)
  success, issues = xia2.Test.regression.check_result('X4_wide.xds', result, tmpdir, ccp4, xds)
  assert success, issues

@pytest.mark.regression
def test_xds_split(data_dir, tmpdir, ccp4, xds):
  command_line = [
      'xia2', 'pipeline=3di', 'nproc=1', 'njob=2', 'mode=parallel',
      'trust_beam_centre=True', 'xinfo=%s' % split_xinfo(data_dir, tmpdir),
  ]
  with tmpdir.as_cwd():
    result = procrunner.run(command_line)
  success, issues = xia2.Test.regression.check_result('X4_wide_split.xds', result, tmpdir, ccp4, xds)
  assert success, issues

@pytest.mark.regression
def test_xds_ccp4a(data_dir, tmpdir, ccp4, xds):
  command_line = [
      'xia2', 'pipeline=3di', 'nproc=1',
      'scaler=ccp4a', 'trust_beam_centre=True', data_dir,
  ]
  with tmpdir.as_cwd():
    result = procrunner.run(command_line)
  success, issues = xia2.Test.regression.check_result('X4_wide.ccp4a', result, tmpdir, ccp4, xds)
  assert success, issues

@pytest.mark.regression
def test_xds_ccp4a_split(data_dir, tmpdir, ccp4, xds):
  command_line = [
    'xia2', 'pipeline=3di', 'nproc=1', 'scaler=ccp4a', 'njob=2',
    'merging_statistics.source=aimless',
    'trust_beam_centre=True', 'mode=parallel', 'xinfo=%s' % split_xinfo(data_dir, tmpdir),
  ]
  with tmpdir.as_cwd():
    result = procrunner.run(command_line)
  success, issues = xia2.Test.regression.check_result('X4_wide_split.ccp4a', result, tmpdir, ccp4, xds)
  assert success, issues
