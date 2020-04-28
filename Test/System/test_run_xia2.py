# System testing: run xia2 and check for zero exit code

from __future__ import absolute_import, division, print_function

import procrunner


def test_start_xia2():
    result = procrunner.run(["xia2"])
    assert result["exitcode"] == 0
