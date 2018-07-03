from __future__ import absolute_import, division, print_function

import os

import procrunner
import pytest
import xia2.Test.regression

@pytest.fixture(scope="session")
def data_dir(xia2_regression_build):
  data_dir = os.path.join(xia2_regression_build, "test_data", "small_molecule_example")
  if not os.path.exists(data_dir):
    pytest.skip('small molecule data not found. Please run xia2_regression.fetch_test_data first')
  return data_dir

expected_data_files = [
    'AUTOMATIC_DEFAULT_scaled.mtz',
    'AUTOMATIC_DEFAULT_scaled.sca',
    'AUTOMATIC_DEFAULT_scaled_unmerged.mtz',
    'AUTOMATIC_DEFAULT_scaled_unmerged.sca',
]


@pytest.mark.regression
def test_dials(data_dir, tmpdir, ccp4):
  command_line = [
      'xia2', 'pipeline=dials', 'nproc=2',
      'small_molecule=True', 'read_all_image_headers=False', 'trust_beam_centre=True',
      data_dir,
  ]
  with tmpdir.as_cwd():
    result = procrunner.run(command_line)
  success, issues = xia2.Test.regression.check_result(
      'small_molecule.dials', result, tmpdir, ccp4, expected_data_files=expected_data_files
  )
  assert success, issues


@pytest.mark.regression
def test_xds(data_dir, tmpdir, ccp4, xds):
  command_line = [
      'xia2', 'pipeline=3dii', 'nproc=2',
      'small_molecule=True', 'read_all_image_headers=False', 'trust_beam_centre=True',
      data_dir,
  ]
  with tmpdir.as_cwd():
    result = procrunner.run(command_line)
  success, issues = xia2.Test.regression.check_result(
      'small_molecule.xds', result, tmpdir, ccp4, expected_data_files=expected_data_files
  )
  assert success, issues


@pytest.mark.regression
def test_xds_ccp4a(data_dir, tmpdir, ccp4, xds):
  command_line = [
      'xia2', 'pipeline=3dii', 'nproc=2',
      'small_molecule=True', 'read_all_image_headers=False', 'trust_beam_centre=True',
      'scaler=ccp4a',
      data_dir,
  ]
  with tmpdir.as_cwd():
    result = procrunner.run(command_line)
  success, issues = xia2.Test.regression.check_result(
      'small_molecule.ccp4a', result, tmpdir, ccp4, expected_data_files=expected_data_files
  )
  assert success, issues
