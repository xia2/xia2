import json
import pytest

from dxtbx.model import ExperimentList
from dxtbx.serialize import load
import iotbx.mtz
from dials.array_family import flex
from dials.command_line.slice_sequence import (
    slice_experiments,
    slice_reflections,
)
from dials.util.multi_dataset_handling import (
    assign_unique_identifiers,
    parse_multiple_datasets,
)
from xia2.Modules.Report import Report
from xia2.cli.multiplex import run as run_multiplex
from xia2.Modules.MultiCrystal import ScaleAndMerge

import pytest_mock


expected_data_files = [
    "scaled.expt",
    "scaled.refl",
    "scaled.mtz",
    "scaled_unmerged.mtz",
    "xia2.multiplex.html",
    "xia2.multiplex.json",
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
        if getattr(pytest_mock, "version", "").startswith("1."):
            assert Report.pychef_plots.return_value[k]["data"][0]["x"] == list(
                range(26)
            )
        else:
            assert Report.pychef_plots.spy_return[k]["data"][0]["x"] == list(range(26))
    for f in expected_data_files:
        assert tmpdir.join(f).check(file=1), "expected file %s missing" % f
    multiplex_expts = load.experiment_list(
        tmpdir.join("scaled.expt").strpath, check_format=False
    )
    for i, expt in enumerate(multiplex_expts):
        valid_image_ranges = expt.scan.get_valid_image_ranges(expt.identifier)
        if i == 0:
            assert valid_image_ranges == [(11, 25)]
        else:
            assert valid_image_ranges == [(1, 25)]
    with tmpdir.join("xia2.multiplex.json").open("r") as fh:
        d = json.load(fh)
        for hkl in ("100", "010", "001"):
            k = f"stereographic_projection_{hkl}"
            assert k in d
        assert d["stereographic_projection_001"]["data"][0]["hovertext"] == [
            "0",
            "1",
            "2",
            "3",
            "4",
            "5",
            "6",
            "7",
        ]
        for k in ("xtriage", "merging_stats", "merging_stats_anom"):
            assert k in d["datasets"]["All data"]
        assert list(d["datasets"]["All data"]["xtriage"].keys()) == [
            "success",
            "warnings",
            "danger",
        ]
    # Delete large temporary files to conserve disk space
    for f in tmpdir.listdir("*.refl"):
        f.remove()


@pytest.mark.parametrize(
    "d_min",
    [None, 2.0],
)
def test_proteinase_k_filter_deltacchalf(d_min, regression_test, dials_data, tmpdir):
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
                "max_clusters=1",
                "nproc=1",
                "resolution.d_min=%s" % d_min,
            ]
        )
        run_multiplex(command_line_args)
    for f in expected_data_files + [
        "filtered.expt",
        "filtered.refl",
        "filtered.mtz",
        "filtered_unmerged.mtz",
    ]:
        assert tmpdir.join(f).check(file=1), "expected file %s missing" % f
    assert len(load.experiment_list(tmpdir / "scaled.expt", check_format=False)) == 8
    assert len(load.experiment_list(tmpdir / "filtered.expt", check_format=False)) < 8

    # assert that the reflection files are different - the filtered reflections
    # should have fewer reflections as one data set has been removed
    mtz_scaled = iotbx.mtz.object(tmpdir.join("scaled_unmerged.mtz").strpath)
    mtz_filtered = iotbx.mtz.object(tmpdir.join("filtered_unmerged.mtz").strpath)
    if d_min:
        # assert that the input d_min has carried through to the output files
        for mtz in (mtz_scaled, mtz_filtered):
            assert mtz.as_miller_arrays()[0].d_min() == pytest.approx(d_min, abs=1e-4)

    assert mtz_filtered.n_reflections() != mtz_scaled.n_reflections()

    with tmpdir.join("xia2.multiplex.json").open("r") as fh:
        d = json.load(fh)
        assert list(d["datasets"].keys()) == ["All data", "cluster 6", "Filtered"]
        # assert that the recorded merging statistics are different
        assert (
            d["datasets"]["All data"]["resolution_graphs"]["cc_one_half_All_data"][
                "data"
            ][0]["y"]
            != d["datasets"]["Filtered"]["resolution_graphs"]["cc_one_half_Filtered"][
                "data"
            ][0]["y"]
        )

    # Check that cluster 6 has been scaled
    assert tmpdir.join("cluster_6").check(dir=1)
    assert tmpdir.join("cluster_6", "scaled.mtz").check(file=1)
    assert tmpdir.join("cluster_6", "scaled_unmerged.mtz").check(file=1)

    # Delete large temporary files to conserve disk space
    for f in tmpdir.listdir("*.refl"):
        f.remove()
    for f in tmpdir.join("cluster_6").listdir("*.refl"):
        f.remove()


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
        tmpdir.join("scaled.expt").strpath, check_format=False
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
    # Delete large temporary files to conserve disk space
    for f in tmpdir.listdir("*.refl"):
        f.remove()


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


@pytest.fixture
def protk_experiments_and_reflections(dials_data):
    data_dir = dials_data("multi_crystal_proteinase_k")

    # Load experiments
    experiments = ExperimentList()
    for expt_file in sorted(f.strpath for f in data_dir.listdir("experiments*.json")):
        experiments.extend(load.experiment_list(expt_file, check_format=False))

    # Load reflection tables
    reflections = [
        flex.reflection_table.from_file(refl_file)
        for refl_file in sorted(
            f.strpath for f in data_dir.listdir("reflections*.pickle")
        )
    ]

    # Setup experiment identifiers
    reflections = parse_multiple_datasets(reflections)
    experiments, reflections = assign_unique_identifiers(experiments, reflections)

    # Combine into single ExperimentList
    reflections_all = flex.reflection_table()
    for i, (expt, refl) in enumerate(zip(experiments, reflections)):
        reflections_all.extend(refl)
    reflections_all.assert_experiment_identifiers_are_consistent(experiments)
    return experiments, reflections_all


def test_data_manager_filter_dose(protk_experiments_and_reflections):
    # Construct the DataManager
    experiments, reflections = protk_experiments_and_reflections
    data_manager = ScaleAndMerge.DataManager(experiments, reflections)

    # Filter dose and verify the resulting filtered image ranges
    data_manager.filter_dose(1, 20)
    assert len(data_manager.experiments) == 8
    for expt in data_manager.experiments:
        assert expt.scan.get_image_range() == (1, 20)


def test_data_manager_filter_dose_out_of_range(protk_experiments_and_reflections):
    experiments, reflections = protk_experiments_and_reflections

    # Truncate one of the experiments so that one of the expt image ranges
    # doesn't overlap with the requested dose range
    image_range = [expt.scan.get_image_range() for expt in experiments]
    image_range[3] = (1, 10)
    experiments = slice_experiments(experiments, image_range)
    reflections = slice_reflections(reflections, image_range)

    # Construct the DataManager
    data_manager = ScaleAndMerge.DataManager(experiments, reflections)

    # Filter on dose and verify that one experiment has been removed
    data_manager.filter_dose(12, 25)
    assert len(data_manager.experiments) == 7
    assert len(data_manager.experiments) < len(experiments)
    for expt in data_manager.experiments:
        assert expt.scan.get_image_range() == (12, 25)
