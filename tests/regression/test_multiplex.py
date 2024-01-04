from __future__ import annotations

import json
import os
import pathlib

import pytest
import pytest_mock

import iotbx.mtz
from dials.array_family import flex
from dials.command_line.slice_sequence import slice_experiments, slice_reflections
from dials.util.multi_dataset_handling import (
    assign_unique_identifiers,
    parse_multiple_datasets,
)
from dxtbx.model import ExperimentList
from dxtbx.serialize import load

from xia2.cli.multiplex import run as run_multiplex
from xia2.Modules.MultiCrystal.data_manager import DataManager
from xia2.Modules.Report import Report

expected_data_files = [
    "scaled.expt",
    "scaled.refl",
    "scaled.mtz",
    "scaled_unmerged.mtz",
    "scaled.sca",
    "scaled_unmerged.sca",
    "xia2.multiplex.html",
    "xia2.multiplex.json",
]


@pytest.fixture()
def proteinase_k(dials_data):
    data_dir = dials_data("multi_crystal_proteinase_k", pathlib=True)
    expts = sorted(os.fspath(f) for f in data_dir.glob("experiments*.json"))
    refls = sorted(os.fspath(f) for f in data_dir.glob("reflections*.pickle"))
    yield expts, refls


def test_proteinase_k(mocker, proteinase_k, run_in_tmp_path):
    expts, refls = proteinase_k
    mocker.spy(Report, "pychef_plots")
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
        assert os.path.isfile(f), f"expected file {f} missing"
    multiplex_expts = load.experiment_list("scaled.expt", check_format=False)
    for i, expt in enumerate(multiplex_expts):
        valid_image_ranges = expt.scan.get_valid_image_ranges(expt.identifier)
        if i == 0:
            assert valid_image_ranges == [(11, 25)]
        else:
            assert valid_image_ranges == [(1, 25)]
    with open("xia2.multiplex.json") as fh:
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
    expected_keys = {
        "resolution_graphs",
        "batch_graphs",
        "xtriage",
        "merging_stats",
        "merging_stats_anom",
        "misc_graphs",
    }
    assert not expected_keys - set(d["datasets"]["All data"])
    assert list(d["datasets"]["All data"]["xtriage"].keys()) == [
        "success",
        "warnings",
        "danger",
    ]


def test_proteinase_k_anomalous(proteinase_k, run_in_tmp_path):
    expts, refls = proteinase_k
    run_multiplex(expts + refls + ["anomalous=True"])
    with open("xia2.multiplex.json") as fh:
        d = json.load(fh)
    assert "dano_All_data" in d["datasets"]["All data"]["resolution_graphs"]

    mtz_scaled = iotbx.mtz.object("scaled.mtz").as_miller_arrays()
    labels = [ma.info().labels for ma in mtz_scaled]
    assert ["F(+)", "SIGF(+)", "F(-)", "SIGF(-)"] in labels
    assert ["I(+)", "SIGI(+)", "I(-)", "SIGI(-)"] in labels


@pytest.mark.parametrize(
    "d_min",
    [None, 2.0],
)
def test_proteinase_k_filter_deltacchalf(d_min, proteinase_k, run_in_tmp_path):
    expts, refls = proteinase_k
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
        "filtered.sca",
        "filtered_unmerged.sca",
    ]:
        assert os.path.isfile(f), "expected file %s missing" % f
    assert len(load.experiment_list("scaled.expt", check_format=False)) == 8
    assert len(load.experiment_list("filtered.expt", check_format=False)) < 8

    # assert that the reflection files are different - the filtered reflections
    # should have fewer reflections as one data set has been removed
    mtz_scaled = iotbx.mtz.object("scaled_unmerged.mtz")
    mtz_filtered = iotbx.mtz.object("filtered_unmerged.mtz")
    if d_min:
        # assert that the input d_min has carried through to the output files
        for mtz in (mtz_scaled, mtz_filtered):
            assert mtz.as_miller_arrays()[0].d_min() == pytest.approx(d_min, abs=1e-4)

    assert mtz_filtered.n_reflections() != mtz_scaled.n_reflections()

    with open("xia2.multiplex.json") as fh:
        d = json.load(fh)
    assert list(d["datasets"].keys()) == ["All data", "cluster 6", "Filtered"]
    # assert that the recorded merging statistics are different
    assert (
        d["datasets"]["All data"]["resolution_graphs"]["cc_one_half_All_data"]["data"][
            0
        ]["y"]
        != d["datasets"]["Filtered"]["resolution_graphs"]["cc_one_half_Filtered"][
            "data"
        ][0]["y"]
    )

    # Check that cluster 6 has been scaled
    cluster = pathlib.Path("cluster_6")
    assert cluster.is_dir()
    assert (cluster / "scaled.mtz").is_file()
    assert (cluster / "scaled_unmerged.mtz").is_file()


@pytest.mark.parametrize(
    "laue_group,space_group,threshold",
    [("P422", None, None), (None, "P422", 3.5), (None, "P43212", None)],
)
def test_proteinase_k_dose(
    laue_group, space_group, threshold, proteinase_k, run_in_tmp_path
):
    expts, refls = proteinase_k
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
    run_multiplex(command_line_args)

    for f in expected_data_files:
        assert os.path.isfile, f"expected file {f} missing"

    multiplex_expts = load.experiment_list("scaled.expt", check_format=False)
    if threshold is not None:
        # one experiment should have been rejected after unit cell clustering
        assert len(multiplex_expts) == 7
        expected_clusters = ("cluster_4", "cluster_5")
    else:
        assert len(multiplex_expts) == 8
        expected_clusters = ("cluster_5", "cluster_6")

    # Check that expected clusters have been scaled
    for cluster in expected_clusters:
        cluster = pathlib.Path(cluster)
        assert cluster.is_dir()
        assert (cluster / "scaled.mtz").is_file()
        assert (cluster / "scaled_unmerged.mtz").is_file()

    for expt in multiplex_expts:
        if space_group is None:
            assert expt.crystal.get_space_group().type().lookup_symbol() == "P 41 21 2"
        else:
            assert (
                expt.crystal.get_space_group().type().lookup_symbol().replace(" ", "")
                == space_group
            )


@pytest.mark.parametrize(
    "parameters",
    (
        ["min_completeness=0.6", "cluster_method=cos_angle"],
        ["min_completeness=0.6", "cluster_method=correlation"],
    ),
)
def test_proteinase_k_min_completeness(parameters, proteinase_k, run_in_tmp_path):
    expts, refls = proteinase_k
    command_line_args = parameters + expts + refls
    run_multiplex(command_line_args)

    for f in expected_data_files:
        assert pathlib.Path(f).is_file(), "expected file %s missing" % f

    multiplex_expts = load.experiment_list("scaled.expt", check_format=False)
    assert len(multiplex_expts) == 8
    clusters = list(pathlib.Path().glob("cluster_[0-9]*"))
    assert len(clusters)
    for cluster in clusters:
        assert (cluster / "scaled.mtz").is_file()
        assert (cluster / "scaled_unmerged.mtz").is_file()


def test_proteinase_k_single_dataset_raises_error(proteinase_k, run_in_tmp_path):
    expts, refls = proteinase_k
    with pytest.raises(SystemExit) as e:
        run_multiplex([expts[0], refls[1]])
    assert str(e.value) == "xia2.multiplex requires a minimum of two experiments"


def test_proteinase_k_laue_group_space_group_raises_error(
    proteinase_k, run_in_tmp_path
):
    expts, refls = proteinase_k
    command_line_args = (
        ["symmetry.laue_group=P422", "symmetry.space_group=P41212"] + expts + refls
    )
    with pytest.raises(SystemExit):
        run_multiplex(command_line_args)


@pytest.fixture
def protk_experiments_and_reflections(dials_data):
    data_dir = dials_data("multi_crystal_proteinase_k", pathlib=True)

    # Load experiments
    experiments = ExperimentList()
    for expt_file in sorted(data_dir.glob("experiments*.json")):
        experiments.extend(load.experiment_list(expt_file, check_format=False))

    # Load reflection tables
    reflections = [
        flex.reflection_table.from_file(refl_file)
        for refl_file in sorted(data_dir.glob("reflections*.pickle"))
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
    data_manager = DataManager(experiments, reflections)

    # Filter dose and verify the resulting filtered image ranges
    data_manager.filter_dose(1, 20)
    assert len(data_manager.experiments) == 8
    for expt in data_manager.experiments:
        assert expt.scan.get_image_range() == (1, 20)


def test_prot_k_multiwave_single(run_in_tmp_path, protk_experiments_and_reflections):
    experiments, reflections = protk_experiments_and_reflections
    experiments[0].beam.set_wavelength(1.0)
    experiments = experiments[:2]
    reflections = reflections.select_on_experiment_identifiers(
        experiments.identifiers()
    )
    # just use first two
    experiments.as_file(run_in_tmp_path / "tmp.expt")
    reflections.as_file(run_in_tmp_path / "tmp.refl")
    run_multiplex(["tmp.expt", "tmp.refl", "wavelength_tolerance=0.1"])

    for f in expected_data_files:
        assert (run_in_tmp_path / f).is_file(), f"expected file {f} missing"


def test_prot_k_multiwave_double(run_in_tmp_path, protk_experiments_and_reflections):
    experiments, reflections = protk_experiments_and_reflections
    for i in range(0, 4):
        experiments[i].beam.set_wavelength(1.0)
    experiments.as_file(run_in_tmp_path / "tmp.expt")
    reflections.as_file(run_in_tmp_path / "tmp.refl")
    run_multiplex(
        [
            "tmp.expt",
            "tmp.refl",
            "wavelength_tolerance=0.001",
            "min_completeness=0.6",
            "filtering.method=deltacchalf",
            "resolution.d_min=2.6",
        ]
    )

    expected_multi_data_files = [
        "scaled.expt",
        "scaled.refl",
        "scaled_unmerged_WAVE1.mtz",
        "scaled_unmerged_WAVE2.mtz",
        "scaled_unmerged_WAVE1.sca",
        "scaled_unmerged_WAVE2.sca",
        "scaled_WAVE1.mtz",
        "scaled_WAVE2.mtz",
        "scaled_WAVE1.sca",
        "scaled_WAVE2.sca",
        "xia2.multiplex.html",
        "xia2.multiplex.json",
    ]

    expected_filtered = [
        "filtered.expt",
        "filtered.refl",
        "filtered_unmerged_WAVE1.mtz",
        "filtered_unmerged_WAVE2.mtz",
        "filtered_unmerged_WAVE1.sca",
        "filtered_unmerged_WAVE2.sca",
        "filtered_WAVE1.mtz",
        "filtered_WAVE2.mtz",
        "filtered_WAVE1.sca",
        "filtered_WAVE2.sca",
    ]

    for f in expected_multi_data_files + ["scaled.mtz"]:
        assert (run_in_tmp_path / f).is_file(), f"expected file {f} missing"
    for f in expected_multi_data_files[:-2]:
        assert (
            run_in_tmp_path / "cluster_6" / f
        ).is_file(), f"expected file {f} missing"
    for f in expected_filtered:
        assert (run_in_tmp_path / f).is_file(), f"expected file {f} missing"


def test_data_manager_filter_dose_out_of_range(protk_experiments_and_reflections):
    experiments, reflections = protk_experiments_and_reflections

    # Truncate one of the experiments so that one of the expt image ranges
    # doesn't overlap with the requested dose range
    image_range = [expt.scan.get_image_range() for expt in experiments]
    image_range[3] = (1, 10)
    experiments = slice_experiments(experiments, image_range)
    reflections = slice_reflections(reflections, image_range)

    # Construct the DataManager
    data_manager = DataManager(experiments, reflections)

    # Filter on dose and verify that one experiment has been removed
    data_manager.filter_dose(12, 25)
    assert len(data_manager.experiments) == 7
    assert len(data_manager.experiments) < len(experiments)
    for expt in data_manager.experiments:
        assert expt.scan.get_image_range() == (12, 25)


def test_run_with_reference_pdb(run_in_tmp_path, dials_data):
    # Test that use case of providing a reference file to consistently reindex against
    # In this case there is no indexing ambiguity, so we're just testing it
    # completes as expected with the set space group from the pdb file.
    data_dir = dials_data("multi_crystal_proteinase_k", pathlib=True)
    expts = [
        os.fspath(data_dir / "experiments_1.json"),
        os.fspath(data_dir / "experiments_2.json"),
    ]
    refls = [
        os.fspath(data_dir / "reflections_1.pickle"),
        os.fspath(data_dir / "reflections_2.pickle"),
    ]
    command_line_args = [f"reference={os.fspath(data_dir/'2id8.pdb')}"] + expts + refls
    run_multiplex(command_line_args)

    assert (run_in_tmp_path / "dials.reindex.log").is_file()
    assert (run_in_tmp_path / "scaled.expt").is_file()
    multiplex_expts = load.experiment_list("scaled.expt", check_format=False)
    for expt in multiplex_expts:
        assert expt.crystal.get_space_group().type().lookup_symbol() == "P 43 21 2"

    # test EXIT if incompatible space group
    command_line_args = (
        [f"reference={os.fspath(data_dir/'2id8.pdb')}", "symmetry.space_group=P1"]
        + expts
        + refls
    )

    with pytest.raises(SystemExit):
        run_multiplex(command_line_args)


def test_clean_exit_on_stills_data(dials_data, run_in_tmp_path):
    ssx = dials_data("cunir_serial_processed", pathlib=True)
    with pytest.raises(SystemExit):
        run_multiplex(
            [
                f"{ssx / 'integrated.refl'}",
                f"{ssx / 'integrated.expt'}",
            ],
        )
