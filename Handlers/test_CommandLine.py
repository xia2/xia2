from __future__ import absolute_import, division, print_function

import pytest

from dials.util import Sorry


@pytest.mark.parametrize("name", ("foo_001", "_foo_001", "foo", "_foo_", "_1foo"))
def test_validate_project_crystal_name(name, ccp4, tmpdir):
    with tmpdir.as_cwd():
        # import creates droppings as side-effect
        from xia2.Handlers.CommandLine import validate_project_crystal_name

        validate_project_crystal_name("crystal", name)


@pytest.mark.parametrize("name", ("foo.001", "1foo", "foo&", "*foo"))
def test_fail_on_invalid_project_crystal_name(name, ccp4, tmpdir):
    with tmpdir.as_cwd(), pytest.raises(Sorry):
        # import creates droppings as side-effect
        from xia2.Handlers.CommandLine import validate_project_crystal_name

        validate_project_crystal_name("crystal", name)
