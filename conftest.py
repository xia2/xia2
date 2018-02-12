#
# See https://github.com/dials/dials/wiki/pytest for documentation on how to
# write and run pytest tests, and an overview of the available features.
#

from __future__ import absolute_import, division, print_function

import os

import pytest
from dials.conftest import (dials_regression, xia2_regression,
                            xia2_regression_build)

def pytest_addoption(parser):
  '''Add a '--runslow' option to py.test.'''
  parser.addoption("--runslow", action="store_true",
                   default=False, help="run slow tests")

def pytest_collection_modifyitems(config, items):
  '''Tests marked as slow will not be run unless slow tests are enabled with
     the '--runslow' parameter or the test is selected specifically. The
     latter allows running slow tests via the libtbx compatibility layer.'''
  if not config.getoption("--runslow") and len(items) > 1:
    skip_slow = pytest.mark.skip(reason="need --runslow option to run")
    for item in items:
      if "slow" in item.keywords:
        item.add_marker(skip_slow)

@pytest.fixture
def ccp4():
  '''Return the absolute path to the CCP4 installation.
     Skip the test if CCP4 is not installed.'''
  try:
    return os.environ['CCP4']
  except KeyError:
    pytest.skip("CCP4 installation required for this test")
