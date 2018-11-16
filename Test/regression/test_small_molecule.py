from __future__ import absolute_import, division, print_function

import procrunner
import pytest
import xia2.Test.regression

expected_data_files = [
    'AUTOMATIC_DEFAULT_scaled.mtz',
    'AUTOMATIC_DEFAULT_scaled.sca',
    'AUTOMATIC_DEFAULT_scaled_unmerged.mtz',
    'AUTOMATIC_DEFAULT_scaled_unmerged.sca',
]


@pytest.mark.regression
def test_dials(regression_data, run_in_tmpdir, ccp4):
  command_line = [
      'xia2', 'pipeline=dials', 'nproc=2',
      'small_molecule=True', 'read_all_image_headers=False', 'trust_beam_centre=True',
      regression_data('small_molecule_example').strpath,
  ]
  result = procrunner.run(command_line)
  success, issues = xia2.Test.regression.check_result(
      'small_molecule.dials', result, run_in_tmpdir, ccp4, expected_data_files=expected_data_files
  )
  assert success, issues

@pytest.mark.regression
def test_dials_full(regression_data, run_in_tmpdir, ccp4):
    command_line = [
        'xia2', 'pipeline=dials-full', 'nproc=2',
        'small_molecule=True', 'read_all_image_headers=False', 'trust_beam_centre=True',
        regression_data('small_molecule_example').strpath,
    ]
    result = procrunner.run(command_line)
    success, issues = xia2.Test.regression.check_result(
        'small_molecule.dials_full', result, run_in_tmpdir, ccp4, expected_data_files=[
    'AUTOMATIC_DEFAULT_scaled.mtz', 'AUTOMATIC_DEFAULT_scaled_unmerged.mtz']
    )
    assert success, issues


@pytest.mark.regression
def test_xds(regression_data, run_in_tmpdir, ccp4, xds):
  command_line = [
      'xia2', 'pipeline=3dii', 'nproc=2',
      'small_molecule=True', 'read_all_image_headers=False', 'trust_beam_centre=True',
      regression_data('small_molecule_example').strpath,
  ]
  result = procrunner.run(command_line)
  success, issues = xia2.Test.regression.check_result(
      'small_molecule.xds', result, run_in_tmpdir, ccp4, expected_data_files=expected_data_files
  )
  assert success, issues


@pytest.mark.regression
def test_xds_ccp4a(regression_data, run_in_tmpdir, ccp4, xds):
  command_line = [
      'xia2', 'pipeline=3dii', 'nproc=2',
      'small_molecule=True', 'read_all_image_headers=False', 'trust_beam_centre=True',
      'scaler=ccp4a',
      regression_data('small_molecule_example').strpath,
  ]
  result = procrunner.run(command_line)
  success, issues = xia2.Test.regression.check_result(
      'small_molecule.ccp4a', result, run_in_tmpdir, ccp4, expected_data_files=expected_data_files
  )
  assert success, issues
