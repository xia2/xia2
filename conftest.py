#
# See https://github.com/dials/dials/wiki/pytest for documentation on how to
# write and run pytest tests, and an overview of the available features.
#

from __future__ import absolute_import, division, print_function

import argparse
import os
import re

import procrunner
import pytest
import six
from dials.conftest import run_in_tmpdir  # noqa; lgtm; exported symbol


def pytest_addoption(parser):
    """
    Option '--regression-full' needs to be used to run all regression tests,
    including the full-length xia2 runs.
    """

    class RFAction(argparse.Action):
        def __call__(self, parser, namespace, values, option_string):
            namespace.regression = True
            namespace.regression_full = True

    parser.addoption(
        "--regression-full",
        nargs=0,
        action=RFAction,
        help="run all regression tests, this will take a while. Implies --regression",
    )


def pytest_configure(config):
    if six.PY3:
        import dxtbx.tests.python3_test_filter as ptf

        exp = ptf.Python3TestFailureExpectationPlugin(config)
        config.pluginmanager.register(exp)


@pytest.fixture(scope="session")
def regression_test(request):
    if not request.config.getoption("--regression-full"):
        pytest.skip("Test requires --regression-full option to run.")


@pytest.fixture(scope="session")
def ccp4():
    """
    Return information about the CCP4 installation.
    Skip the test if CCP4 is not installed.
    """
    if not os.getenv("CCP4"):
        pytest.skip("CCP4 installation required for this test")

    try:
        result = procrunner.run(["refmac5", "-i"], print_stdout=False)
    except OSError:
        pytest.skip(
            "CCP4 installation required for this test - Could not find CCP4 executable"
        )
    if result["exitcode"] or result["timeout"]:
        pytest.skip(
            "CCP4 installation required for this test - Could not run CCP4 executable"
        )
    version = re.search(br"patch level *([0-9]+)\.([0-9]+)\.([0-9]+)", result["stdout"])
    if not version:
        pytest.skip(
            "CCP4 installation required for this test - Could not determine CCP4 version"
        )
    return {"path": os.getenv("CCP4"), "version": [int(v) for v in version.groups()]}


@pytest.fixture(scope="session")
def xds():
    """
    Return information about the XDS installation.
    Skip the test if XDS is not installed.
    """
    try:
        result = procrunner.run(["xds"], print_stdout=False)
    except OSError:
        pytest.skip("XDS installation required for this test")
    if result["exitcode"] or result["timeout"]:
        pytest.skip("XDS installation required for this test - Could not run XDS")
    if b"license expired" in result["stdout"]:
        pytest.skip("XDS installation required for this test - XDS license is expired")
    version = re.search(br"BUILT=([0-9]+)\)", result["stdout"])
    if not version:
        pytest.skip(
            "XDS installation required for this test - Could not determine XDS version"
        )
    return {"version": int(version.groups()[0])}
