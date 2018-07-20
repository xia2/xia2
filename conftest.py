#
# See https://github.com/dials/dials/wiki/pytest for documentation on how to
# write and run pytest tests, and an overview of the available features.
#

from __future__ import absolute_import, division, print_function

import os
import re

import procrunner
import pytest
from dials.conftest import (dials_regression, xia2_regression,
                            xia2_regression_build)

def pytest_addoption(parser):
  '''Add '--runslow' and '--regression' options to pytest.'''
  parser.addoption("--runslow", action="store_true", default=False,
                   help="run slow tests")
  parser.addoption("--regression", action="store_true", default=False,
                   help="run regression tests")
  parser.addoption("--regression-only", action="store_true", default=False,
                   help="run only regression tests")

def pytest_collection_modifyitems(config, items):
  '''Tests marked as slow will not be run unless slow tests are enabled with
     the '--runslow' parameter or the test is selected specifically. The
     latter allows running slow tests via the libtbx compatibility layer.
     Tests marked as regression are only run with --regression.
  '''
  if not config.getoption("--runslow") and len(items) > 1:
    skip_slow = pytest.mark.skip(reason="need --runslow option to run")
    for item in items:
      if "slow" in item.keywords:
        item.add_marker(skip_slow)
  if config.getoption("--regression-only"):
    skip_regression = pytest.mark.skip(reason="Test only runs without --regression-only")
    for item in items:
      if "regression" not in item.keywords:
        item.add_marker(skip_regression)
  elif not config.getoption("--regression"):
    skip_regression = pytest.mark.skip(reason="Test only runs with --regression")
    for item in items:
      if "regression" in item.keywords:
        item.add_marker(skip_regression)

@pytest.fixture(scope="session")
def ccp4():
  '''Return information about the CCP4 installation.
     Skip the test if CCP4 is not installed.'''
  if not os.getenv('CCP4'):
    pytest.skip("CCP4 installation required for this test")

  try:
    result = procrunner.run(['refmac5', '-i'], print_stdout=False)
  except OSError:
    pytest.skip("CCP4 installation required for this test - Could not find CCP4 executable")
  if result['exitcode'] or result['timeout']:
    pytest.skip("CCP4 installation required for this test - Could not run CCP4 executable")
  version = re.search('patch level *([0-9]+)\.([0-9]+)\.([0-9]+)', result['stdout'])
  if not version:
    pytest.skip("CCP4 installation required for this test - Could not determine CCP4 version")
  return {
      'path': os.getenv('CCP4'),
      'version': [int(v) for v in version.groups()],
  }

@pytest.fixture(scope="session")
def xds():
  '''Return information about the XDS installation.
     Skip the test if XDS is not installed.'''
  try:
    result = procrunner.run(['xds'], print_stdout=False)
  except OSError:
    pytest.skip("XDS installation required for this test")
  if result['exitcode'] or result['timeout']:
    pytest.skip("XDS installation required for this test - Could not run XDS")
  if 'license expired' in result['stdout']:
    pytest.skip("XDS installation required for this test - XDS license is expired")
  version = re.search('BUILT=([0-9]+)\)', result['stdout'])
  if not version:
    pytest.skip("XDS installation required for this test - Could not determine XDS version")
  return {
      'version': int(version.groups()[0])
  }
