from __future__ import absolute_import, division, print_function

import pytest

from dxtbx.serialize import load
from xia2.Modules.Report import Report
from xia2.command_line.multiplex import run as run_multiplex


expected_data_files = [
    "multiplex.expt",
    "multiplex.refl",
    "scaled.mtz",
    "scaled_unmerged.mtz",
    "xia2.multiplex.html",
]


def test_proteinase_k(mocker, regression_test, dials_data, tmpdir):
    data_dir = dials_data("multi_crystal_proteinase_k")
    expts = sorted(f.strpath for f in data_dir.listdir("experiments*.json"))
    refls = sorted(f.strpath for f in data_dir.listdir("reflections*.pickle"))
    mocker.spy(Report, "pychef_plots")
    with tmpdir.as_cwd():
        run_multiplex(expts + refls + ["exclude_images=0:1:10"])
    # Verify that the *_vs_dose plots have been correctly plotted
    assert Report.pychef_plots.call_count == 1
    for k in (
        "rcp_vs_dose",
        "scp_vs_dose",
        "completeness_vs_dose",
        "rd_vs_batch_difference",
    ):
        assert Report.pychef_plots.return_value[k]["data"][0]["x"] == list(range(26))
    for f in expected_data_files:
        assert tmpdir.join(f).check(file=1), "expected file %s missing" % f
    multiplex_expts = load.experiment_list(
        tmpdir.join("multiplex.expt").strpath, check_format=False
    )
    for i, expt in enumerate(multiplex_expts):
        valid_image_ranges = expt.scan.get_valid_image_ranges(expt.identifier)
        if i == 0:
            assert valid_image_ranges == [(11, 25)]
        else:
            assert valid_image_ranges == [(1, 25)]
        assert expt.crystal.get_space_group().type().lookup_symbol() == "P 41 21 2"


def test_proteinase_k_filter_deltacchalf(regression_test, dials_data, tmpdir):
    data_dir = dials_data("multi_crystal_proteinase_k")
    expts = sorted(f.strpath for f in data_dir.listdir("experiments*.json"))
    refls = sorted(f.strpath for f in data_dir.listdir("reflections*.pickle"))
    with tmpdir.as_cwd():
        command_line_args = (
            expts
            + refls
            + [
                "filtering.method=deltacchalf",
                "filtering.deltacchalf.stdcutoff=1",
                "max_clusters=2",
            ]
        )
        run_multiplex(command_line_args)
    for f in expected_data_files:
        assert tmpdir.join(f).check(file=1), "expected file %s missing" % f
    multiplex_expts = load.experiment_list(
        tmpdir.join("multiplex.expt").strpath, check_format=False
    )
    assert len(multiplex_expts) == 7

    # Check that clusters 5 and 6 have been scaled
    for cluster in ("cluster_5", "cluster_6"):
        assert tmpdir.join(cluster).check(dir=1)
        assert tmpdir.join(cluster, "scaled.mtz").check(file=1)
        assert tmpdir.join(cluster, "scaled_unmerged.mtz").check(file=1)


@pytest.mark.parametrize(
    "laue_group,space_group,threshold",
    [("P422", None, None), (None, "P422", 3.5), (None, "P43212", None)],
)
def test_proteinase_k_dose(
    laue_group, space_group, threshold, regression_test, dials_data, tmpdir
):
    data_dir = dials_data("multi_crystal_proteinase_k")
    expts = sorted(f.strpath for f in data_dir.listdir("experiments*.json"))
    refls = sorted(f.strpath for f in data_dir.listdir("reflections*.pickle"))
    command_line_args = (
        [
            "dose=1,20",
            "symmetry.laue_group=%s" % laue_group,
            "symmetry.space_group=%s" % space_group,
            "max_clusters=2",
        ]
        + expts
        + refls
    )
    if threshold is not None:
        command_line_args.append("unit_cell_clustering.threshold=%s" % threshold)
    with tmpdir.as_cwd():
        run_multiplex(command_line_args)

    for f in expected_data_files:
        assert tmpdir.join(f).check(file=1), "expected file %s missing" % f

    multiplex_expts = load.experiment_list(
        tmpdir.join("multiplex.expt").strpath, check_format=False
    )
    if threshold is not None:
        # one experiment should have been rejected after unit cell clustering
        assert len(multiplex_expts) == 7
        expected_clusters = ("cluster_4", "cluster_5")
    else:
        assert len(multiplex_expts) == 8
        expected_clusters = ("cluster_5", "cluster_6")

    # Check that expected clusters have been scaled
    for cluster in expected_clusters:
        assert tmpdir.join(cluster).check(dir=1)
        assert tmpdir.join(cluster, "scaled.mtz").check(file=1)
        assert tmpdir.join(cluster, "scaled_unmerged.mtz").check(file=1)

    for expt in multiplex_expts:
        if space_group is None:
            assert expt.crystal.get_space_group().type().lookup_symbol() == "P 41 21 2"
        else:
            assert (
                expt.crystal.get_space_group().type().lookup_symbol().replace(" ", "")
                == space_group
            )


def test_proteinase_k_single_dataset_raises_error(regression_test, dials_data, tmpdir):
    data_dir = dials_data("multi_crystal_proteinase_k")
    expts = data_dir.join("experiments_1.json")
    refls = data_dir.join("reflections_1.pickle")
    with tmpdir.as_cwd():
        with pytest.raises(SystemExit) as e:
            run_multiplex([expts.strpath, refls.strpath])
        assert str(e.value) == "xia2.multiplex requires a minimum of two experiments"


def test_proteinase_k_laue_group_space_group_raises_error(
    regression_test, dials_data, tmpdir
):
    data_dir = dials_data("multi_crystal_proteinase_k")
    expts = sorted(f.strpath for f in data_dir.listdir("experiments*.json"))
    refls = sorted(f.strpath for f in data_dir.listdir("reflections*.pickle"))
    command_line_args = (
        ["symmetry.laue_group=P422", "symmetry.space_group=P41212"] + expts + refls
    )
    with tmpdir.as_cwd():
        with pytest.raises(SystemExit):
            run_multiplex(command_line_args)
