# System testing: run xia2 and check for zero exit code


import procrunner


def test_start_xia2():
    result = procrunner.run(["xia2"])
    assert result["exitcode"] == 0
