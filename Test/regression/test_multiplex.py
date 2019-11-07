from __future__ import absolute_import, division, print_function

import pytest

from dxtbx.serialize import load

expected_data_files = [
    "multiplex.expt",
    "multiplex.refl",
    "scaled.mtz",
    "scaled_unmerged.mtz",
    "xia2.multiplex.html",
]


def test_proteinase_k(regression_test, ccp4, dials_data, tmpdir):
    data_dir = dials_data("multi_crystal_proteinase_k")
    expts = sorted(f.strpath for f in data_dir.listdir("experiments*.json"))
    refls = sorted(f.strpath for f in data_dir.listdir("reflections*.pickle"))
    with tmpdir.as_cwd():
        from xia2.command_line.multiplex import run

        run(expts + refls)
    for f in expected_data_files:
        assert tmpdir.join(f).check(file=1), "expected file %s missing" % f
    multiplex_expts = load.experiment_list(
        tmpdir.join("multiplex.expt").strpath, check_format=False
    )
    for expt in multiplex_expts:
        assert expt.crystal.get_space_group().type().lookup_symbol() == "P 41 21 2"


@pytest.mark.parametrize(
    "laue_group,space_group", [("P422", None), (None, "P422"), (None, "P43212")]
)
def test_proteinase_k_dose(
    laue_group, space_group, regression_test, ccp4, dials_data, tmpdir
):
    data_dir = dials_data("multi_crystal_proteinase_k")
    expts = sorted(f.strpath for f in data_dir.listdir("experiments*.json"))
    refls = sorted(f.strpath for f in data_dir.listdir("reflections*.pickle"))
    command_line_args = (
        [
            "dose=1,20",
            "symmetry.laue_group=%s" % laue_group,
            "symmetry.space_group=%s" % space_group,
        ]
        + expts
        + refls
    )
    with tmpdir.as_cwd():
        from xia2.command_line.multiplex import run

        run(command_line_args)
    for f in expected_data_files:
        assert tmpdir.join(f).check(file=1), "expected file %s missing" % f
    multiplex_expts = load.experiment_list(
        tmpdir.join("multiplex.expt").strpath, check_format=False
    )
    for expt in multiplex_expts:
        if space_group is None:
            assert expt.crystal.get_space_group().type().lookup_symbol() == "P 41 21 2"
        else:
            assert (
                expt.crystal.get_space_group().type().lookup_symbol().replace(" ", "")
                == space_group
            )


def test_proteinase_k_laue_group_space_group_raises_error(
    regression_test, ccp4, dials_data, tmpdir
):
    data_dir = dials_data("multi_crystal_proteinase_k")
    expts = sorted(f.strpath for f in data_dir.listdir("experiments*.json"))
    refls = sorted(f.strpath for f in data_dir.listdir("reflections*.pickle"))
    command_line_args = (
        ["symmetry.laue_group=P422", "symmetry.space_group=P41212"] + expts + refls
    )
    with tmpdir.as_cwd():
        from xia2.command_line.multiplex import run

        with pytest.raises(SystemExit):
            run(command_line_args)
