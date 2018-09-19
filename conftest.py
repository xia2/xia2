#
# See https://github.com/dials/dials/wiki/pytest for documentation on how to
# write and run pytest tests, and an overview of the available features.
#

from __future__ import absolute_import, division, print_function

import os
import re

import procrunner
import py.path
import pytest
from dials.conftest import (dials_regression, xia2_regression,
                            xia2_regression_build, run_in_tmpdir)

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
  if not config.getoption("--runslow") and len(items) > 1 and not config.getoption("--regression"):
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

@pytest.fixture(scope="session")
def regression_data():
  '''Return the location of a regression data set as py.path object.
     Download the files if they are not on disk already.
     Skip the test if the data can not be downloaded.
  '''
  dls_dir = '/dls/science/groups/scisoft/DIALS/repositories/current/xia2_regression_data'
  read_only = False
  if os.getenv('REGRESSIONDATA'):
    target_dir = os.getenv('REGRESSIONDATA')
  elif os.path.exists(os.path.join(dls_dir, 'filelist.json')):
    target_dir = dls_dir
    read_only = True
  elif os.getenv('LIBTBX_BUILD'):
    target_dir = os.path.join(os.getenv('LIBTBX_BUILD'), 'xia2_regression')
  else:
    pytest.skip('Can not determine regression data location. Use environment variable REGRESSIONDATA')

  from xia2.Test.fetch_test_data import download_lock, fetch_test_data
  _cache = {}
  def data_fetcher(test_data):
    if test_data not in _cache:
      with download_lock(target_dir):
        _cache[test_data] = fetch_test_data(target_dir, pre_scan=True, file_group=test_data, read_only=read_only)
    if not _cache[test_data]:
      pytest.skip('Automated download of test data failed. Run xia2.fetch_test_data')
    return py.path.local(_cache[test_data])
  return data_fetcher
