from __future__ import absolute_import, division, print_function

import procrunner
import pytest

expected_data_files = [
    "scaled.mtz",
    "scaled_unmerged.mtz",
    "xia2-multi-crystal-report.html",
]


def test_proteinase_k(regression_test, ccp4, dials_data, run_in_tmpdir):
    data_dir = dials_data("multi_crystal_proteinase_k")
    expts = sorted(f.strpath for f in data_dir.listdir("experiments*.json"))
    refls = sorted(f.strpath for f in data_dir.listdir("reflections*.pickle"))
    command_line = ["xia2.multiplex"] + expts + refls
    print(" ".join(command_line))
    result = procrunner.run(command_line)
    assert not result["exitcode"]
    for f in expected_data_files:
        assert run_in_tmpdir.join(f).check(file=1), "expected file %s missing" % f


@pytest.mark.parametrize("space_group", [None, "P422"])
def test_proteinase_k_dose(
    space_group, regression_test, ccp4, dials_data, run_in_tmpdir
):
    data_dir = dials_data("multi_crystal_proteinase_k")
    expts = sorted(f.strpath for f in data_dir.listdir("experiments*.json"))
    refls = sorted(f.strpath for f in data_dir.listdir("reflections*.pickle"))
    command_line = (
        ["xia2.multiplex", "dose=1,20", "symmetry.space_group=%s" % space_group]
        + expts
        + refls
    )
    print(" ".join(command_line))
    result = procrunner.run(command_line)
    assert not result["exitcode"]
    for f in expected_data_files:
        assert run_in_tmpdir.join(f).check(file=1), "expected file %s missing" % f
