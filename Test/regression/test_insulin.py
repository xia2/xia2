from __future__ import absolute_import, division, print_function

import procrunner
import pytest
import xia2.Test.regression

expected_data_files = [
    'AUTOMATIC_DEFAULT_NATIVE_SWEEP1_INTEGRATE.mtz',
    'AUTOMATIC_DEFAULT_free.mtz',
    'AUTOMATIC_DEFAULT_scaled.sca',
    'AUTOMATIC_DEFAULT_scaled_unmerged.mtz',
    'AUTOMATIC_DEFAULT_scaled_unmerged.sca',
]


@pytest.mark.regression
def test_2d(regression_data, run_in_tmpdir, ccp4):
  command_line = [
      'xia2', 'pipeline=2di', 'nproc=1',
      'trust_beam_centre=True',
      regression_data('insulin').strpath,
  ]
  result = procrunner.run(command_line)
  success, issues = xia2.Test.regression.check_result(
      'insulin.2d', result, run_in_tmpdir, ccp4, expected_data_files=expected_data_files
  )
  assert success, issues
