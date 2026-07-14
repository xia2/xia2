from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess

import iotbx.mtz
import pytest
from dials.array_family import flex
from dials.command_line.slice_sequence import slice_experiments, slice_reflections
from dials.util.multi_dataset_handling import (
    assign_unique_identifiers,
    parse_multiple_datasets,
)
from dxtbx.model import ExperimentList
from dxtbx.serialize import load

from xia2.Modules.MultiCrystal.data_manager import DataManager

expected_data_files = [
    pathlib.Path("Processing") / "scaled.expt",
    pathlib.Path("Processing") / "scaled.refl",
    pathlib.Path("DataFiles") / "scaled.mtz",
    pathlib.Path("DataFiles") / "scaled_unmerged.mtz",
    pathlib.Path("DataFiles") / "scaled_unmerged.mmcif",
    pathlib.Path("DataFiles") / "scaled.sca",
    pathlib.Path("DataFiles") / "scaled_unmerged.sca",
    pathlib.Path("xia2.multiplex.html"),
    pathlib.Path("Processing") / "xia2.multiplex.json",
]


@pytest.fixture()
def proteinase_k(dials_data):
    data_dir = dials_data("multi_crystal_proteinase_k")
    expts = sorted(os.fspath(f) for f in data_dir.glob("experiments*.json"))
    refls = sorted(os.fspath(f) for f in data_dir.glob("reflections*.pickle"))
    yield expts, refls


def test_proteinase_k(proteinase_k, run_in_tmp_path):
    expts, refls = proteinase_k
    result = subprocess.run(
        [shutil.which("xia2.multiplex"), "exclude_images=0:1:10"] + expts + refls,
        cwd=run_in_tmp_path,
        capture_output=True,
    )
    assert not result.returncode

    for f in expected_data_files:
        assert (run_in_tmp_path / f).exists(), f"expected file {f} missing"
    multiplex_expts = load.experiment_list(
        run_in_tmp_path / "Processing" / "scaled.expt", check_format=False
    )
    for i, expt in enumerate(multiplex_expts):
        valid_image_ranges = expt.scan.get_valid_image_ranges(expt.identifier)
        if i == 0:
            assert valid_image_ranges == [(11, 25)]
        else:
            assert valid_image_ranges == [(1, 25)]
    with open(run_in_tmp_path / "Processing" / "xia2.multiplex.json") as fh:
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
    # Verify that the *_vs_dose plots have been correctly plotted
    dose_plots = d["datasets"]["All data"]["batch_graphs"]

    for k in (
        "rcp_vs_dose",
        "scp_vs_dose",
        "completeness_vs_dose",
        "rd_vs_batch_difference",
    ):
        assert dose_plots[k + "_All_data"]["data"][0]["x"] == list(range(26))


def test_proteinase_k_anomalous(proteinase_k, run_in_tmp_path):
    expts, refls = proteinase_k
    result = subprocess.run(
        [shutil.which("xia2.multiplex"), "anomalous=True"] + expts + refls,
        cwd=run_in_tmp_path,
        capture_output=True,
    )
    assert not result.returncode

    with open(run_in_tmp_path / "Processing" / "xia2.multiplex.json") as fh:
        d = json.load(fh)
    assert "dano_All_data" in d["datasets"]["All data"]["resolution_graphs"]

    mtz_scaled = iotbx.mtz.object("DataFiles/scaled.mtz").as_miller_arrays()
    labels = [ma.info().labels for ma in mtz_scaled]
    assert ["F(+)", "SIGF(+)", "F(-)", "SIGF(-)"] in labels
    assert ["I(+)", "SIGI(+)", "I(-)", "SIGI(-)"] in labels


def test_proteinase_k_filter_deltacchalf(proteinase_k, run_in_tmp_path):
    # Note we need to set a dmin, else the scaling lbfgs minimisation can give
    # slightly different numerical results across platforms as there is low
    # multiplicity, which ends up affecting the clustering.
    expts, refls = proteinase_k
    command_line_args = (
        expts
        + refls
        + [
            "filtering.method=deltacchalf",
            "filtering.deltacchalf.stdcutoff=1",
            "clustering.output_clusters=True",
            "clustering.max_output_clusters=1",
            "nproc=1",
            "resolution.d_min=2.0",
        ]
    )
    result = subprocess.run(
        [shutil.which("xia2.multiplex")] + command_line_args,
        cwd=run_in_tmp_path,
        capture_output=True,
    )
    assert not result.returncode

    for f in expected_data_files + [
        pathlib.Path("Processing") / "filtered.expt",
        pathlib.Path("Processing") / "filtered.refl",
        pathlib.Path("DataFiles") / "filtered.mtz",
        pathlib.Path("DataFiles") / "filtered_unmerged.mtz",
        pathlib.Path("DataFiles") / "filtered_unmerged.mmcif",
        pathlib.Path("DataFiles") / "filtered.sca",
        pathlib.Path("DataFiles") / "filtered_unmerged.sca",
    ]:
        assert os.path.isfile(run_in_tmp_path / f), "expected file %s missing" % f
    assert (
        len(
            load.experiment_list(
                run_in_tmp_path / "Processing" / "scaled.expt", check_format=False
            )
        )
        == 8
    )
    assert (
        len(
            load.experiment_list(
                run_in_tmp_path / "Processing" / "filtered.expt", check_format=False
            )
        )
        < 8
    )

    # assert that the reflection files are different - the filtered reflections
    # should have fewer reflections as one data set has been removed
    mtz_scaled = iotbx.mtz.object(
        str((run_in_tmp_path / "DataFiles" / "scaled_unmerged.mtz").resolve())
    )
    mtz_filtered = iotbx.mtz.object(
        str((run_in_tmp_path / "DataFiles" / "filtered_unmerged.mtz").resolve())
    )
    # assert that the input d_min has carried through to the output files
    for mtz in (mtz_scaled, mtz_filtered):
        assert mtz.as_miller_arrays()[0].d_min() == pytest.approx(2.0, abs=1e-4)

    assert mtz_filtered.n_reflections() != mtz_scaled.n_reflections()

    with open(run_in_tmp_path / "Processing" / "xia2.multiplex.json") as fh:
        d = json.load(fh)
    assert list(d["datasets"].keys()) == ["All data", "cos cluster 6", "Filtered"]
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
    cluster = "cos_cluster_6"
    cluster_dir = run_in_tmp_path / "Processing" / f"{cluster}"
    assert cluster_dir.is_dir()
    assert (run_in_tmp_path / "DataFiles" / f"{cluster}_scaled.mtz").is_file()
    assert (run_in_tmp_path / "DataFiles" / f"{cluster}_scaled_unmerged.mtz").is_file()
    assert (
        run_in_tmp_path / "DataFiles" / f"{cluster}_scaled_unmerged.mmcif"
    ).is_file()


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
            "space_group=%s" % space_group,
            "clustering.output_clusters=True",
            "clustering.max_output_clusters=2",
            "clustering.min_cluster_size=2",
        ]
        + expts
        + refls
    )
    if threshold is not None:
        command_line_args.append("unit_cell_clustering.threshold=%s" % threshold)

    result = subprocess.run(
        [shutil.which("xia2.multiplex")] + command_line_args,
        cwd=run_in_tmp_path,
        capture_output=True,
    )
    assert not result.returncode

    for f in expected_data_files:
        assert os.path.isfile, f"expected file {f} missing"

    multiplex_expts = load.experiment_list(
        run_in_tmp_path / "Processing" / "scaled.expt", check_format=False
    )
    if threshold is not None:
        # one experiment should have been rejected after unit cell clustering
        assert len(multiplex_expts) == 7
        # also means the cluster numbers change to avoid outputting a cluster identical to the full dataset
        expected_clusters = ("cos_cluster_4", "cos_cluster_5")
    else:
        assert len(multiplex_expts) == 8
        expected_clusters = ("cos_cluster_5", "cos_cluster_6")

    # Check that expected clusters have been scaled
    for cluster in expected_clusters:
        cluster_dir = pathlib.Path(f"Processing/{cluster}")
        assert cluster_dir.is_dir()
        assert (run_in_tmp_path / "DataFiles" / f"{cluster}_scaled.mtz").is_file()
        assert (
            run_in_tmp_path / "DataFiles" / f"{cluster}_scaled_unmerged.mtz"
        ).is_file()
        assert (
            run_in_tmp_path / "DataFiles" / f"{cluster}_scaled_unmerged.mmcif"
        ).is_file()

    for expt in multiplex_expts:
        if space_group is None:
            assert expt.crystal.get_space_group().type().lookup_symbol() == "P 41 21 2"
        else:
            assert (
                expt.crystal.get_space_group().type().lookup_symbol().replace(" ", "")
                == space_group
            )


def test_proteinase_k_coordinate_clusters(proteinase_k, run_in_tmp_path):
    expts, refls = proteinase_k
    parameters = [
        "clustering.output_clusters=True",
        "clustering.method=coordinate",
        "space_group=P422",
        "clustering.min_cluster_size=2",
    ]
    command_line_args = parameters + expts[:-1] + refls[:-1]
    result = subprocess.run(
        [shutil.which("xia2.multiplex")] + command_line_args,
        cwd=run_in_tmp_path,
        capture_output=True,
    )
    assert not result.returncode

    for f in expected_data_files:
        assert pathlib.Path(f).is_file(), "expected file %s missing" % f

    multiplex_expts = load.experiment_list(
        run_in_tmp_path / "Processing" / "scaled.expt", check_format=False
    )
    assert len(multiplex_expts) == 7
    assert (run_in_tmp_path / "DataFiles" / "coordinate_cluster_0_scaled.mtz").is_file()
    assert (
        run_in_tmp_path / "DataFiles" / "coordinate_cluster_0_scaled_unmerged.mtz"
    ).is_file()
    assert (
        run_in_tmp_path / "DataFiles" / "coordinate_cluster_0_scaled_unmerged.mmcif"
    ).is_file()


def test_proteinase_k_hierarchical_clusters(proteinase_k, run_in_tmp_path):
    parameters = [
        "clustering.output_clusters=True",
        "clustering.min_completeness=0.5",
        "clustering.hierarchical.method=correlation+cos_angle",
        "space_group=P422",
    ]
    expts, refls = proteinase_k
    command_line_args = parameters + expts[:-1] + refls[:-1]
    result = subprocess.run(
        [shutil.which("xia2.multiplex")] + command_line_args,
        cwd=run_in_tmp_path,
        capture_output=True,
    )
    assert not result.returncode

    for f in expected_data_files:
        assert pathlib.Path(f).is_file(), "expected file %s missing" % f

    multiplex_expts = load.experiment_list(
        run_in_tmp_path / "Processing" / "scaled.expt", check_format=False
    )
    assert len(multiplex_expts) == 7
    for ctype in ["cc", "cos"]:
        clusters = list(pathlib.Path("Processing").glob(ctype + "_cluster_[0-9]*"))
        assert len(clusters)
        for cluster in clusters:
            assert (
                run_in_tmp_path / "DataFiles" / f"{cluster.name}_scaled.mtz"
            ).is_file()
            assert (
                run_in_tmp_path / "DataFiles" / f"{cluster.name}_scaled_unmerged.mtz"
            ).is_file()
            assert (
                run_in_tmp_path / "DataFiles" / f"{cluster.name}_scaled_unmerged.mmcif"
            ).is_file()


def test_proteinase_k_hierarchical_clusters_distinct(proteinase_k, run_in_tmp_path):
    parameters = [
        "clustering.output_clusters=True",
        "clustering.min_completeness=0.2",
        "clustering.min_cluster_size=1",
        "clustering.hierarchical.method=correlation",
        "space_group=P422",
        "distinct_clusters=True",
    ]
    expts, refls = proteinase_k
    command_line_args = parameters + expts[:-1] + refls[:-1]
    result = subprocess.run(
        [shutil.which("xia2.multiplex")] + command_line_args,
        cwd=run_in_tmp_path,
        capture_output=True,
    )
    assert not result.returncode

    for f in expected_data_files:
        assert pathlib.Path(f).is_file(), "expected file %s missing" % f

    multiplex_expts = load.experiment_list(
        run_in_tmp_path / "Processing" / "scaled.expt", check_format=False
    )
    assert len(multiplex_expts) == 7
    clusters = list(pathlib.Path().glob("cc_cluster_[0-9]*"))
    # Has shown to be unstable if it finds clusters or not: just need to make sure code runs to completion
    if len(clusters):
        for cluster in clusters:
            assert (
                run_in_tmp_path / "DataFiles" / f"{cluster.name}_scaled.mtz"
            ).is_file()
            assert (
                run_in_tmp_path / "DataFiles" / f"{cluster.name}_scaled_unmerged.mtz"
            ).is_file()
            assert (
                run_in_tmp_path / "DataFiles" / f"{cluster.name}_scaled_unmerged.mmcif"
            ).is_file()


def test_proteinase_k_single_dataset_raises_error(proteinase_k, run_in_tmp_path):
    expts, refls = proteinase_k
    result = subprocess.run(
        [shutil.which("xia2.multiplex")] + [expts[0], refls[1]],
        cwd=run_in_tmp_path,
        capture_output=True,
    )
    assert result.returncode
    assert result.stderr.decode().splitlines() == [
        "xia2.multiplex requires a minimum of two experiments"
    ]


def test_proteinase_k_laue_group_space_group_raises_error(
    proteinase_k, run_in_tmp_path
):
    expts, refls = proteinase_k
    command_line_args = (
        ["symmetry.laue_group=P422", "space_group=P41212"] + expts + refls
    )
    result = subprocess.run(
        [shutil.which("xia2.multiplex")] + command_line_args,
        cwd=run_in_tmp_path,
        capture_output=True,
    )
    assert result.returncode


@pytest.fixture
def protk_experiments_and_reflections(dials_data):
    data_dir = dials_data("multi_crystal_proteinase_k")

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
    result = subprocess.run(
        [shutil.which("xia2.multiplex")]
        + ["tmp.expt", "tmp.refl", "wavelength_tolerance=0.1"],
        cwd=run_in_tmp_path,
        capture_output=True,
    )
    assert not result.returncode

    for f in expected_data_files:
        assert (run_in_tmp_path / f).is_file(), f"expected file {f} missing"


def test_prot_k_multiwave_double(run_in_tmp_path, protk_experiments_and_reflections):
    experiments, reflections = protk_experiments_and_reflections
    for i in range(0, 4):
        experiments[i].beam.set_wavelength(1.0)
    experiments = experiments[:-1]
    reflections = reflections.select_on_experiment_identifiers(
        experiments.identifiers()
    )
    experiments.as_file(run_in_tmp_path / "tmp.expt")
    reflections.as_file(run_in_tmp_path / "tmp.refl")
    cmdline_args = [
        "tmp.expt",
        "tmp.refl",
        "wavelength_tolerance=0.001",
        "clustering.output_clusters=True",
        "clustering.min_completeness=0.55",  # 6",
        "filtering.method=deltacchalf",
        "resolution.d_min=2.6",
    ]
    result = subprocess.run(
        [shutil.which("xia2.multiplex")] + cmdline_args,
        cwd=run_in_tmp_path,
        capture_output=True,
    )
    assert not result.returncode

    expected_multi_data_files = [
        pathlib.Path("Processing") / "scaled.expt",
        pathlib.Path("Processing") / "scaled.refl",
        pathlib.Path("DataFiles") / "scaled_unmerged_WAVE1.mtz",
        pathlib.Path("DataFiles") / "scaled_unmerged_WAVE2.mtz",
        pathlib.Path("DataFiles") / "scaled_unmerged_WAVE1.mmcif",
        pathlib.Path("DataFiles") / "scaled_unmerged_WAVE2.mmcif",
        pathlib.Path("DataFiles") / "scaled_unmerged_WAVE1.sca",
        pathlib.Path("DataFiles") / "scaled_unmerged_WAVE2.sca",
        pathlib.Path("DataFiles") / "scaled_WAVE1.mtz",
        pathlib.Path("DataFiles") / "scaled_WAVE2.mtz",
        pathlib.Path("DataFiles") / "scaled_WAVE1.sca",
        pathlib.Path("DataFiles") / "scaled_WAVE2.sca",
        pathlib.Path("xia2.multiplex.html"),
        pathlib.Path("Processing") / "xia2.multiplex.json",
    ]

    expected_filtered = [
        pathlib.Path("Processing") / "filtered.expt",
        pathlib.Path("Processing") / "filtered.refl",
        pathlib.Path("DataFiles") / "filtered_unmerged_WAVE1.mtz",
        pathlib.Path("DataFiles") / "filtered_unmerged_WAVE2.mtz",
        pathlib.Path("DataFiles") / "filtered_unmerged_WAVE1.mmcif",
        pathlib.Path("DataFiles") / "filtered_unmerged_WAVE2.mmcif",
        pathlib.Path("DataFiles") / "filtered_unmerged_WAVE1.sca",
        pathlib.Path("DataFiles") / "filtered_unmerged_WAVE2.sca",
        pathlib.Path("DataFiles") / "filtered_WAVE1.mtz",
        pathlib.Path("DataFiles") / "filtered_WAVE2.mtz",
        pathlib.Path("DataFiles") / "filtered_WAVE1.sca",
        pathlib.Path("DataFiles") / "filtered_WAVE2.sca",
    ]

    for f in expected_multi_data_files + [pathlib.Path("DataFiles") / "scaled.mtz"]:
        assert (run_in_tmp_path / f).is_file(), f"expected file {f} missing"
    for f in expected_multi_data_files[:2]:
        cluster_path = pathlib.Path("cos_cluster_5") / f"cos_cluster_5_{f.name}"
        assert (run_in_tmp_path / f.parent / cluster_path).is_file(), (
            f"expected file {f} missing"
        )
    for f in expected_multi_data_files[2:-2]:
        cluster_path = f"cos_cluster_5_{f.name}"
        assert (run_in_tmp_path / f.parent / cluster_path).is_file(), (
            f"expected file {f} missing"
        )
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
    data_dir = dials_data("multi_crystal_proteinase_k")
    expts = [
        os.fspath(data_dir / "experiments_1.json"),
        os.fspath(data_dir / "experiments_2.json"),
    ]
    refls = [
        os.fspath(data_dir / "reflections_1.pickle"),
        os.fspath(data_dir / "reflections_2.pickle"),
    ]
    command_line_args = (
        [f"reference={os.fspath(data_dir / '2id8.pdb')}"] + expts + refls
    )
    result = subprocess.run(
        [shutil.which("xia2.multiplex")] + command_line_args,
        cwd=run_in_tmp_path,
        capture_output=True,
    )
    assert not result.returncode

    candidate_reindex_logs = list(
        (run_in_tmp_path / "LogFiles").glob("*_dials.reindex.log")
    )

    assert len(candidate_reindex_logs) == 1
    assert (run_in_tmp_path / "Processing" / "scaled.expt").is_file()
    multiplex_expts = load.experiment_list(
        run_in_tmp_path / "Processing" / "scaled.expt", check_format=False
    )
    for expt in multiplex_expts:
        assert expt.crystal.get_space_group().type().lookup_symbol() == "P 43 21 2"

    # test EXIT if incompatible space group
    command_line_args = (
        [f"reference={os.fspath(data_dir / '2id8.pdb')}", "space_group=P1"]
        + expts
        + refls
    )

    result = subprocess.run(
        [shutil.which("xia2.multiplex")] + command_line_args,
        cwd=run_in_tmp_path,
        capture_output=True,
    )
    assert result.returncode


def test_clean_exit_on_stills_data(dials_data, run_in_tmp_path):
    ssx = dials_data("cunir_serial_processed")
    result = subprocess.run(
        [shutil.which("xia2.multiplex")]
        + [
            f"{ssx / 'integrated.refl'}",
            f"{ssx / 'integrated.expt'}",
        ],
        cwd=run_in_tmp_path,
        capture_output=True,
    )
    assert result.returncode


def test_on_import_xds_data(dials_data, run_in_tmp_path):
    import shutil
    import subprocess

    result = subprocess.run(
        [
            shutil.which("dials.import_xds"),
            dials_data("insulin_processed_xds_1"),
            "output.reflections=integrate_hkl_1.refl",
            "output.xds_experiments=xds_models_1.expt",
        ],
        cwd=run_in_tmp_path,
        capture_output=True,
    )
    assert not result.returncode and not result.stderr
    assert (run_in_tmp_path / "xds_models_1.expt").is_file()
    assert (run_in_tmp_path / "integrate_hkl_1.refl").is_file()
    result = subprocess.run(
        [
            shutil.which("dials.import_xds"),
            dials_data("insulin_processed_xds_2"),
            "output.reflections=integrate_hkl_2.refl",
            "output.xds_experiments=xds_models_2.expt",
        ],
        cwd=run_in_tmp_path,
        capture_output=True,
    )
    assert not result.returncode and not result.stderr
    assert (run_in_tmp_path / "xds_models_2.expt").is_file()
    assert (run_in_tmp_path / "integrate_hkl_2.refl").is_file()

    command_line_args = [
        "integrate_hkl_1.refl",
        "integrate_hkl_2.refl",
        "xds_models_1.expt",
        "xds_models_2.expt",
    ]
    result = subprocess.run(
        [shutil.which("xia2.multiplex")] + command_line_args,
        cwd=run_in_tmp_path,
        capture_output=True,
    )
    assert not result.returncode

    for f in expected_data_files:
        assert pathlib.Path(f).is_file(), "expected file %s missing" % f

    expts = load.experiment_list(
        run_in_tmp_path / "Processing" / "scaled.expt", check_format=False
    )
    assert len(expts) == 2


def test_shelx_output(proteinase_k, run_in_tmp_path):
    expts, refls = proteinase_k
    parameters = ["composition=CHSNO"]
    command_line_args = parameters + expts[:-1] + refls[:-1]
    result = subprocess.run(
        [shutil.which("xia2.multiplex")] + command_line_args,
        cwd=run_in_tmp_path,
        capture_output=True,
    )
    assert not result.returncode

    for f in expected_data_files:
        assert pathlib.Path(f).is_file(), "expected file %s missing" % f

    assert (pathlib.Path("DataFiles") / "scaled.hkl").is_file(), (
        "expected file %s missing" % f
    )
    assert (pathlib.Path("DataFiles") / "scaled.ins").is_file(), (
        "expected file %s missing" % f
    )


def test_selected_identifiers(protk_experiments_and_reflections, run_in_tmp_path):
    # This test mimics behaviour of selecting subset of data from html and using the working-phil to reprocess a subset
    expts, refls = protk_experiments_and_reflections
    test_uuid_1 = expts[2].identifier
    test_uuid_2 = expts[5].identifier
    expts.as_file(run_in_tmp_path / "tmp.expt")
    refls.as_file(run_in_tmp_path / "tmp.refl")
    result = subprocess.run(
        [shutil.which("xia2.multiplex")] + ["tmp.expt", "tmp.refl"],
        cwd=run_in_tmp_path,
        capture_output=True,
    )
    assert not result.returncode

    subset_path = run_in_tmp_path / "subset"
    subset_path.mkdir(exist_ok=True)

    working_phil = run_in_tmp_path / "xia2-multiplex-working.phil"

    command_line = [str(working_phil), f"identifiers={test_uuid_1},{test_uuid_2}"]

    result = subprocess.run(
        [shutil.which("xia2.multiplex")] + command_line,
        cwd=subset_path,
        capture_output=True,
    )
    assert not result.returncode

    multiplex_expts = load.experiment_list(
        subset_path / "Processing" / "scaled.expt", check_format=False
    )
    assert len(multiplex_expts) == 2
    assert test_uuid_1 in multiplex_expts.identifiers()
    assert test_uuid_2 in multiplex_expts.identifiers()


def test_small_molecule(dials_data, run_in_tmp_path):
    # We don't have any small molecule multi-crystal data in dials-data, so
    # make a copy of the single dataset to be able to trigger multiplex and
    # test the small molecule symmetry determination.
    nidppe = dials_data("nidppe_processed")
    expts = nidppe / "integrated.expt"
    refls = nidppe / "integrated.refl.gz"
    subprocess.run(
        [
            shutil.which("dials.assign_experiment_identifiers"),
            expts,
            refls,
            "identifiers='copy'",
        ],
        cwd=run_in_tmp_path,
    )
    command_line_args = [
        "small_molecule=True",
        os.fspath(expts),
        os.fspath(refls),
        run_in_tmp_path / "assigned.expt",
        run_in_tmp_path / "assigned.refl",
    ]
    result = subprocess.run(
        [shutil.which("xia2.multiplex")] + command_line_args,
        cwd=run_in_tmp_path,
        capture_output=True,
    )
    assert not result.returncode
    multiplex_expts = load.experiment_list(
        run_in_tmp_path / "Processing" / "scaled.expt", check_format=False
    )
    # Check small molecule symmetry assessment was done.
    assert str(multiplex_expts[0].crystal.get_space_group().info()) == "P 1 21/c 1"
    # Check that shelx files were also generated, even though no composition was specified
    assert (run_in_tmp_path / "DataFiles" / "scaled.hkl").is_file()
    assert (run_in_tmp_path / "DataFiles" / "scaled.ins").is_file()
