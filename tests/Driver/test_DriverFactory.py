import pytest

import xia2.Driver.DriverFactory as DF


def test_instantiate_driver():
    assert DF.DriverFactory.Driver()


def test_instantiate_nonexistent_driver_fails():
    with pytest.raises((RuntimeError, AssertionError)):
        DF.DriverFactory.Driver("nosuchtype")
