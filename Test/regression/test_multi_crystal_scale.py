from __future__ import absolute_import, division, print_function

import glob
import os
import procrunner
import pytest
import xia2.Test.regression

expected_data_files = [
  '4_scaled.mtz',
  '4_scaled_unmerged.mtz',
  '6_scaled.mtz',
  '6_scaled_unmerged.mtz',
  'multi-crystal-report.html'
]

@pytest.mark.regression
def test_proteinase_k(regression_data, run_in_tmpdir, ccp4):
  data_dir = regression_data('multi_crystal_proteinase_k')
  expts = sorted(glob.glob(data_dir.join('experiments*.json').strpath))
  refls = sorted(glob.glob(data_dir.join('reflections*.pickle').strpath))
  command_line = [
    'xia2.multi_crystal_scale',
  ] + expts + refls
  print(' '.join(command_line))
  result = procrunner.run(command_line, print_stdout=False, print_stderr=False)
  for f in expected_data_files:
    assert os.path.exists(f), f

def test_proteinase_k_dose(regression_data, run_in_tmpdir, ccp4):
  data_dir = regression_data('multi_crystal_proteinase_k')
  expts = sorted(glob.glob(data_dir.join('experiments*.json').strpath))
  refls = sorted(glob.glob(data_dir.join('reflections*.pickle').strpath))
  command_line = [
    'xia2.multi_crystal_scale', 'dose=1,20',
  ] + expts + refls
  print(' '.join(command_line))
  result = procrunner.run(command_line, print_stdout=False, print_stderr=False)
  for f in expected_data_files:
    assert os.path.exists(f), f
