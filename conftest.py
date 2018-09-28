#
# See https://github.com/dials/dials/wiki/pytest for documentation on how to
# write and run pytest tests, and an overview of the available features.
#

from __future__ import absolute_import, division, print_function

import os
import re

import procrunner
import pytest
from dials.conftest import run_in_tmpdir

def pytest_addoption(parser):
  '''Tests that use regression_data will not be run unless '--regression' is
     given as command line parameter.
  '''
  parser.addoption("--regression", action="store_true", default=False,
                   help="run regression tests")

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
def regression_data(request):
  '''Return the location of a regression data set as py.path object.
     Download the files if they are not on disk already.
     Skip the test if the data can not be downloaded.
  '''
  if not request.config.getoption("--regression"):
    pytest.skip("Test requires --regression option to run.")

  dls_dir = '/dls/science/groups/scisoft/DIALS/regression_data'
  read_only = False
  if os.getenv('REGRESSIONDATA'):
    target_dir = os.getenv('REGRESSIONDATA')
  elif os.path.exists(os.path.join(dls_dir, 'filelist.json')):
    target_dir = dls_dir
    read_only = True
  elif os.getenv('LIBTBX_BUILD'):
    target_dir = os.path.join(os.getenv('LIBTBX_BUILD'), 'regression_data')
  else:
    pytest.skip('Can not determine regression data location. Use environment variable REGRESSIONDATA')

  import dials.util.regression_data
  df = dials.util.regression_data.DataFetcher(target_dir, read_only=read_only)
  def skip_test_if_lookup_failed(result):
    if not result:
      if read_only:
        pytest.skip('Regression data is required to run this test. Run with --regression or run dials.fetch_test_data')
      else:
        pytest.skip('Automated download of test data failed. Run dials.fetch_test_data')
    return result
  setattr(df, 'result_filter', skip_test_if_lookup_failed)
  return df
