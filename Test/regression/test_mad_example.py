from __future__ import absolute_import, division, print_function

import os

import procrunner
import pytest
import xia2.Test.regression

expected_data_files = [
    'AUTOMATIC_DEFAULT_free.mtz',
    'AUTOMATIC_DEFAULT_scaled_WAVE2.sca',
    'AUTOMATIC_DEFAULT_scaled_unmerged_WAVE1.sca',
    'AUTOMATIC_DEFAULT_scaled_unmerged_WAVE2.sca',
    'AUTOMATIC_DEFAULT_scaled_WAVE1.sca',
    'AUTOMATIC_DEFAULT_scaled_unmerged_WAVE1.mtz',
    'AUTOMATIC_DEFAULT_scaled_unmerged_WAVE2.mtz',
]

@pytest.fixture(scope="session")
def data_dir(xia2_regression_build):
  data_dir = os.path.join(xia2_regression_build, "test_data", "mad_example")
  if not os.path.exists(data_dir):
    pytest.skip('MAD example data not found. Please run xia2_regression.fetch_test_data first')
  return data_dir

@pytest.mark.regression
def test_dials(data_dir, tmpdir, ccp4):
  command_line = [
      'xia2', 'pipeline=dials', 'nproc=1', 'njob=2', 'mode=parallel',
      'trust_beam_centre=True',
      data_dir,
  ]
  with tmpdir.as_cwd():
    result = procrunner.run(command_line)
  success, issues = xia2.Test.regression.check_result(
      'mad_example.dials', result, tmpdir, ccp4, expected_data_files=expected_data_files
  )
  assert success, issues


@pytest.mark.regression
def test_xds(data_dir, tmpdir, ccp4, xds):
  command_line = [
      'xia2', 'pipeline=3di', 'nproc=1', 'njob=2', 'mode=parallel',
      'trust_beam_centre=True',
      data_dir,
  ]
  with tmpdir.as_cwd():
    result = procrunner.run(command_line)
  success, issues = xia2.Test.regression.check_result(
      'mad_example.xds', result, tmpdir, ccp4, xds, expected_data_files=expected_data_files,
  )
  assert success, issues


@pytest.mark.regression
def test_xds_ccp4a(data_dir, tmpdir, ccp4, xds):
  command_line = [
      'xia2', 'pipeline=3di', 'nproc=1', 'njob=2', 'mode=parallel',
      'trust_beam_centre=True', 'scaler=ccp4a',
      data_dir,
  ]
  with tmpdir.as_cwd():
    result = procrunner.run(command_line)
  success, issues = xia2.Test.regression.check_result(
      'mad_example.ccp4a', result, tmpdir, ccp4, xds, expected_data_files=expected_data_files,
  )
  assert success, issues
