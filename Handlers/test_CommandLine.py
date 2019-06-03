from __future__ import absolute_import, division, print_function

import pytest

from xia2.Handlers.CommandLine import validate_project_crystal_name
from dials.util import Sorry


def test_validate_project_crystal_name():
    for value in ("foo_001", "_foo_001", "foo", "_foo_", "_1foo"):
        assert validate_project_crystal_name("crystal", value)
    for value in ("foo.001", "1foo", "foo&", "*foo"):
        with pytest.raises(Sorry):
            validate_project_crystal_name("crystal", value)
