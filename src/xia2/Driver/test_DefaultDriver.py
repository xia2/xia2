import pytest
import xia2.Driver.DefaultDriver


def test_defaultdriver_fails_on_start():
    d = xia2.Driver.DefaultDriver.DefaultDriver()
    with pytest.raises(NotImplementedError):
        d.start()
