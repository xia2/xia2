from __future__ import annotations

import json
import os
import subprocess
from typing import List

import pytest

from dxtbx.serialize import load


def check_output(main_dir, find_spots=False, index=False, integrate=False):

    assert find_spots is (main_dir / "batch_1" / "strong.refl").is_file()
    assert index is (main_dir / "batch_1" / "indexed.expt").is_file()
    assert index is (main_dir / "batch_1" / "indexed.refl").is_file()
    assert integrate is (main_dir / "batch_1" / "integrated_1.expt").is_file()
    assert integrate is (main_dir / "batch_1" / "integrated_1.refl").is_file()


def test_import_without_reference_or_crystal_info(dials_data, tmp_path):
    """
    Test a basic run. Expect to import and then do crystal assessment,
    and nothing more (for now).
    """

    ssx = dials_data("cunir_serial", pathlib=True)

    args = ["dev.xia2.ssx"]
    args.append("image=" + os.fspath(ssx / "merlin0047_1700*.cbf"))

    result = subprocess.run(args, cwd=tmp_path, capture_output=True)
    assert not result.returncode and not result.stderr

    # want to test
    assert (tmp_path / "import").is_dir()
    assert (tmp_path / "import" / "file_input.json").is_file()

    with (tmp_path / "import" / "file_input.json").open(mode="r") as f:
        file_input = json.load(f)
        assert file_input["reference_geometry"] is None
        assert file_input["images"] == [os.fspath(ssx / "merlin0047_1700*.cbf")]

    assert (tmp_path / "assess_crystals").is_dir()
    assert (tmp_path / "assess_crystals" / "dials.ssx_index.html").is_file()


def test_geometry_refinement_and_run_with_reference(dials_data, tmp_path):
    """
    Test a basic run. Expect to import and then do geometry refinement.
    Then rerun using this as a reference to do integration.
    """

    ssx = dials_data("cunir_serial", pathlib=True)

    args = [
        "dev.xia2.ssx",
        "steps=None",
        "unit_cell=96.4,96.4,96.4,90,90,90",
        "space_group=P213",
        "integration.algorithm=stills",
    ]
    args.append("image=" + os.fspath(ssx / "merlin0047_1700*.cbf"))

    result = subprocess.run(args, cwd=tmp_path, capture_output=True)
    assert not result.returncode and not result.stderr

    # Check that the processing went straight to geometry refinement and then
    # stopped before processing the batches
    assert not (tmp_path / "assess_crystals").is_dir()
    assert (tmp_path / "geometry_refinement").is_dir()
    reference = tmp_path / "geometry_refinement" / "refined.expt"
    reference_import = tmp_path / "geometry_refinement" / "imported.expt"
    assert reference.is_file()
    assert reference_import.is_file()
    assert not (tmp_path / "batch_1").is_dir()
    without_reference_identifiers = load.experiment_list(
        reference_import, check_format=False
    ).identifiers()

    # Test the data was reimported correctly ready for next run
    assert (tmp_path / "import").is_dir()
    assert (tmp_path / "import" / "file_input.json").is_file()
    with (tmp_path / "import" / "file_input.json").open(mode="r") as f:
        file_input = json.load(f)
        assert file_input["reference_geometry"] == os.fspath(reference)
        assert file_input["images"] == [os.fspath(ssx / "merlin0047_1700*.cbf")]
    expts = tmp_path / "import" / "imported.expt"
    assert expts.is_file()
    with_reference_identifiers = load.experiment_list(
        expts, check_format=False
    ).identifiers()

    # now rerun the processing using this reference geometry
    del args[1]
    args.append(f"reference_geometry={os.fspath(reference)}")
    args.append("enable_live_reporting=True")

    result = subprocess.run(args, cwd=tmp_path, capture_output=True)
    assert not result.returncode and not result.stderr

    assert without_reference_identifiers != with_reference_identifiers

    # Check that the data were integrated with this new reference geometry
    assert (tmp_path / "batch_1").is_dir()
    assert (tmp_path / "batch_1/nuggets").is_dir()
    sliced_expts = tmp_path / "batch_1" / "imported.expt"
    assert sliced_expts.is_file()
    sliced_identifiers = load.experiment_list(
        sliced_expts, check_format=False
    ).identifiers()
    assert with_reference_identifiers == sliced_identifiers
    check_output(tmp_path, find_spots=True, index=True, integrate=True)
    assert len(list((tmp_path / "batch_1/nuggets").glob("nugget_index*"))) == 5
    assert len(list((tmp_path / "batch_1/nuggets").glob("nugget_integrate*"))) == 4


def test_full_run_without_reference(dials_data, tmp_path):
    ssx = dials_data("cunir_serial", pathlib=True)

    args = [
        "dev.xia2.ssx",
        "unit_cell=96.4,96.4,96.4,90,90,90",
        "space_group=P213",
        "integration.algorithm=stills",
        "d_min=2.0",
    ]
    args.append("image=" + os.fspath(ssx / "merlin0047_1700*.cbf"))

    result = subprocess.run(args, cwd=tmp_path, capture_output=True)
    assert not result.returncode and not result.stderr

    # Now check that the processing went straight to geometry refinement
    assert not (tmp_path / "assess_crystals").is_dir()
    assert (tmp_path / "geometry_refinement").is_dir()
    reference = tmp_path / "geometry_refinement" / "refined.expt"
    assert reference.is_file()

    # Now check that the data was reimported with this reference
    assert (tmp_path / "import" / "file_input.json").is_file()
    with (tmp_path / "import" / "file_input.json").open(mode="r") as f:
        file_input = json.load(f)
        assert file_input["reference_geometry"] == os.fspath(reference)
        assert file_input["images"] == [os.fspath(ssx / "merlin0047_1700*.cbf")]
    expts = tmp_path / "import" / "imported.expt"
    assert expts.is_file()
    with_reference_identifiers = load.experiment_list(
        expts, check_format=False
    ).identifiers()

    # Check that the data were integrated with this new reference geometry
    assert (tmp_path / "batch_1").is_dir()
    sliced_expts = tmp_path / "batch_1" / "imported.expt"
    assert sliced_expts.is_file()
    sliced_identifiers = load.experiment_list(
        sliced_expts, check_format=False
    ).identifiers()
    assert with_reference_identifiers == sliced_identifiers
    check_output(tmp_path, find_spots=True, index=True, integrate=True)

    # Check that data reduction completed.
    check_data_reduction_files(tmp_path)


def test_stepwise_run_without_reference(dials_data, tmp_path):
    ssx = dials_data("cunir_serial", pathlib=True)

    args = [
        "dev.xia2.ssx",
        "unit_cell=96.4,96.4,96.4,90,90,90",
        "space_group=P213",
        "integration.algorithm=stills",
        "d_min=2.0",
        "steps=find_spots+index+integrate",
    ]
    args.append("image=" + os.fspath(ssx / "merlin0047_1700*.cbf"))
    args.append("steps=find_spots")

    result = subprocess.run(args, cwd=tmp_path, capture_output=True)
    assert not result.returncode and not result.stderr

    # Now check that the processing went straight to geometry refinement
    assert not (tmp_path / "assess_crystals").is_dir()
    assert (tmp_path / "geometry_refinement").is_dir()
    reference = tmp_path / "geometry_refinement" / "refined.expt"
    assert reference.is_file()

    # Now check that the data was reimported with this reference
    assert (tmp_path / "import" / "file_input.json").is_file()
    with (tmp_path / "import" / "file_input.json").open(mode="r") as f:
        file_input = json.load(f)
        assert file_input["reference_geometry"] == os.fspath(reference)
        assert file_input["images"] == [os.fspath(ssx / "merlin0047_1700*.cbf")]
    expts = tmp_path / "import" / "imported.expt"
    assert expts.is_file()
    with_reference_identifiers = load.experiment_list(
        expts, check_format=False
    ).identifiers()

    # Check that find_spots was run with this new reference geometry
    assert (tmp_path / "batch_1").is_dir()
    sliced_expts = tmp_path / "batch_1" / "imported.expt"
    assert sliced_expts.is_file()
    sliced_identifiers = load.experiment_list(
        sliced_expts, check_format=False
    ).identifiers()
    assert with_reference_identifiers == sliced_identifiers
    check_output(tmp_path, find_spots=True)

    # Now rerun, check nothing further done if forgetting to specify geometry
    args[-1] = "steps=index"
    result = subprocess.run(args, cwd=tmp_path, capture_output=True)
    assert not result.returncode and not result.stderr
    check_output(tmp_path, find_spots=True)

    # Now specify geometry
    args.append("reference_geometry=geometry_refinement/refined.expt")
    result = subprocess.run(args, cwd=tmp_path, capture_output=True)
    assert not result.returncode and not result.stderr
    check_output(tmp_path, find_spots=True, index=True)

    # Now specify geometry
    args[-2] = "steps=integrate"
    result = subprocess.run(args, cwd=tmp_path, capture_output=True)
    assert not result.returncode and not result.stderr
    check_output(tmp_path, find_spots=True, index=True, integrate=True)


def check_data_reduction_files(tmp_path):
    assert (tmp_path / "data_reduction").is_dir()
    assert (tmp_path / "data_reduction" / "prefilter").is_dir()
    assert (tmp_path / "data_reduction" / "reindex").is_dir()
    assert (tmp_path / "data_reduction" / "scale").is_dir()
    assert (tmp_path / "data_reduction" / "scale" / "merged.mtz").is_file()
    assert (tmp_path / "data_reduction" / "scale" / "scaled.mtz").is_file()


def test_ssx_reduce_on_directory(dials_data, tmp_path):
    ssx = dials_data("cunir_serial_processed", pathlib=True)
    args = ["dev.xia2.ssx_reduce", f"directory={ssx}"]

    result = subprocess.run(args, cwd=tmp_path, capture_output=True)
    assert not result.returncode and not result.stderr
    check_data_reduction_files(tmp_path)

    # Now check that results were output at various stages to allow iterative
    # workflows
    filter_results = tmp_path / "data_reduction/prefilter/filter_results.json"
    with filter_results.open(mode="r") as f:
        result = json.load(f)
    # check that the unit cells were written to file
    assert result["best_unit_cell"] == [96.4105, 96.4105, 96.4105, 90.0, 90.0, 90.0]
    assert result["n_cryst"] == 5
    assert len(result["unit_cells"]) == 5
    assert result["space_group"] == 198

    data_reduction_json = tmp_path / "data_reduction/data_reduction.json"
    with data_reduction_json.open(mode="r") as f:
        reduction_result = json.load(f)
    assert reduction_result["files_processed"] == {
        "refls": [os.fspath(ssx / "integrated.refl")],
        "expts": [os.fspath(ssx / "integrated.expt")],
    }

    reindex_results_json = tmp_path / "data_reduction/reindex/reindexing_results.json"
    with reindex_results_json.open(mode="r") as f:
        reidx_results = json.load(f)
    assert reidx_results["reindexed_files"] == {
        "0": {
            "refl": os.fspath(tmp_path / "data_reduction/reindex/processed_0.refl"),
            "expt": os.fspath(tmp_path / "data_reduction/reindex/processed_0.expt"),
        }
    }


def test_ssx_reduce_on_files(dials_data, tmp_path):
    ssx = dials_data("cunir_serial_processed", pathlib=True)
    refls = ssx / "integrated.refl"
    expts = ssx / "integrated.expt"
    args = ["dev.xia2.ssx_reduce", f"reflections={refls}", f"experiments={expts}"]

    result = subprocess.run(args, cwd=tmp_path, capture_output=True)
    assert not result.returncode and not result.stderr
    check_data_reduction_files(tmp_path)


@pytest.mark.parametrize(
    ("cluster_args", "expected_results"),
    [
        (
            ["clustering.threshold=1"],
            {
                "best_unit_cell": [96.411, 96.411, 96.411, 90.0, 90.0, 90.0],
                "n_cryst": 3,
            },
        ),
        (
            [
                "central_unit_cell=96.4,96.4,96.4,90,90,90",
                "absolute_length_tolerance=0.015",
            ],
            {
                "best_unit_cell": [96.4107, 96.4107, 96.4107, 90.0, 90.0, 90.0],
                "n_cryst": 4,
            },
        ),
        (
            ["absolute_length_tolerance=0.001"],
            {
                "best_unit_cell": [96.4107, 96.4107, 96.4107, 90.0, 90.0, 90.0],
                "n_cryst": 2,
            },
        ),
    ],
)
def test_ssx_reduce_filter_options(
    dials_data, tmp_path, cluster_args: List[str], expected_results: dict
):
    ssx = dials_data("cunir_serial_processed", pathlib=True)
    args = ["dev.xia2.ssx_reduce", f"directory={ssx}"] + cluster_args

    result = subprocess.run(args, cwd=tmp_path, capture_output=True)
    assert not result.returncode and not result.stderr
    check_data_reduction_files(tmp_path)

    # Now check that results were output at various stages to allow iterative
    # workflows
    filter_results = tmp_path / "data_reduction/prefilter/filter_results.json"
    with filter_results.open(mode="r") as f:
        result = json.load(f)
    # check that the unit cells were written to file
    assert result["best_unit_cell"] == expected_results["best_unit_cell"]
    assert result["n_cryst"] == expected_results["n_cryst"]
