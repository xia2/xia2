from __future__ import annotations

import json
import os

import procrunner

from dxtbx.serialize import load


def test_import_without_reference_or_crystal_info(dials_data, tmp_path):
    """
    Test a basic run. Expect to import and then do crystal assessment,
    and nothing more (for now).
    """

    ssx = dials_data("cunir_serial", pathlib=True)

    args = ["dev.xia2.ssx"]
    args.append("image=" + os.fspath(ssx / "merlin0047_1700*.cbf"))

    result = procrunner.run(args, working_directory=tmp_path)
    assert not result.returncode and not result.stderr

    # want to test
    assert (tmp_path / "initial_import").is_dir()
    assert (tmp_path / "initial_import" / "file_input.json").is_file()

    with (tmp_path / "initial_import" / "file_input.json").open(mode="r") as f:
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
        "stop_after_geometry_refinement=True",
        "unit_cell=96.4,96.4,96.4,90,90,90",
        "space_group=P213",
        "integration.algorithm=stills",
    ]
    args.append("image=" + os.fspath(ssx / "merlin0047_1700*.cbf"))

    result = procrunner.run(args, working_directory=tmp_path)
    assert not result.returncode and not result.stderr

    # First test the data was imported correctly
    assert (tmp_path / "initial_import").is_dir()
    assert (tmp_path / "initial_import" / "file_input.json").is_file()
    with (tmp_path / "initial_import" / "file_input.json").open(mode="r") as f:
        file_input = json.load(f)
        assert file_input["reference_geometry"] is None
        assert file_input["images"] == [os.fspath(ssx / "merlin0047_1700*.cbf")]
    expts = tmp_path / "initial_import" / "imported.expt"
    assert expts.is_file()
    without_reference_identifiers = load.experiment_list(
        expts, check_format=False
    ).identifiers()

    # Now check that the processing went straight to geometry refinement and then
    # stopped before processing the batches
    assert not (tmp_path / "assess_crystals").is_dir()
    assert (tmp_path / "geometry_refinement").is_dir()
    reference = tmp_path / "geometry_refinement" / "refined.expt"
    assert reference.is_file()
    assert not (tmp_path / "batch_1").is_dir()

    # now rerun the processing using this reference geometry
    args.append(f"reference_geometry={os.fspath(reference)}")
    args.append("stop_after_integration=True")

    result = procrunner.run(args, working_directory=tmp_path)
    assert not result.returncode and not result.stderr

    # First test the data was imported correctly with the reference
    assert (tmp_path / "initial_import").is_dir()
    assert (tmp_path / "initial_import" / "file_input.json").is_file()
    with (tmp_path / "initial_import" / "file_input.json").open(mode="r") as f:
        file_input = json.load(f)
        assert file_input["reference_geometry"] == os.fspath(reference)
        assert file_input["images"] == [os.fspath(ssx / "merlin0047_1700*.cbf")]
    expts = tmp_path / "initial_import" / "imported.expt"
    assert expts.is_file()
    with_reference_identifiers = load.experiment_list(
        expts, check_format=False
    ).identifiers()
    assert without_reference_identifiers != with_reference_identifiers

    # Check that the data were integrated with this new reference geometry
    assert (tmp_path / "batch_1").is_dir()
    sliced_expts = tmp_path / "batch_1" / "imported.expt"
    assert sliced_expts.is_file()
    assert (tmp_path / "batch_1" / "integrated_1.refl").is_file()
    assert (tmp_path / "batch_1" / "integrated_1.expt").is_file()
    sliced_identifiers = load.experiment_list(
        sliced_expts, check_format=False
    ).identifiers()
    assert with_reference_identifiers == sliced_identifiers


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

    result = procrunner.run(args, working_directory=tmp_path)
    assert not result.returncode and not result.stderr

    # First test the data was imported correctly
    assert (tmp_path / "initial_import").is_dir()
    assert (tmp_path / "initial_import" / "file_input.json").is_file()
    with (tmp_path / "initial_import" / "file_input.json").open(mode="r") as f:
        file_input = json.load(f)
        assert file_input["reference_geometry"] is None
        assert file_input["images"] == [os.fspath(ssx / "merlin0047_1700*.cbf")]
    expts = tmp_path / "initial_import" / "imported.expt"
    assert expts.is_file()
    without_reference_identifiers = load.experiment_list(
        expts, check_format=False
    ).identifiers()

    # Now check that the processing went straight to geometry refinement
    assert not (tmp_path / "assess_crystals").is_dir()
    assert (tmp_path / "geometry_refinement").is_dir()
    reference = tmp_path / "geometry_refinement" / "refined.expt"
    assert reference.is_file()

    # Now check that the data was reimported with this reference
    assert (tmp_path / "reimported_with_reference").is_dir()
    assert (tmp_path / "reimported_with_reference" / "file_input.json").is_file()
    with (tmp_path / "reimported_with_reference" / "file_input.json").open(
        mode="r"
    ) as f:
        file_input = json.load(f)
        assert file_input["reference_geometry"] == os.fspath(reference)
        assert file_input["images"] == [os.fspath(ssx / "merlin0047_1700*.cbf")]
    expts = tmp_path / "reimported_with_reference" / "imported.expt"
    assert expts.is_file()
    with_reference_identifiers = load.experiment_list(
        expts, check_format=False
    ).identifiers()
    assert without_reference_identifiers != with_reference_identifiers

    # Check that the data were integrated with this new reference geometry
    assert (tmp_path / "batch_1").is_dir()
    sliced_expts = tmp_path / "batch_1" / "imported.expt"
    assert sliced_expts.is_file()
    assert (tmp_path / "batch_1" / "integrated_1.refl").is_file()
    assert (tmp_path / "batch_1" / "integrated_1.expt").is_file()
    sliced_identifiers = load.experiment_list(
        sliced_expts, check_format=False
    ).identifiers()
    assert with_reference_identifiers == sliced_identifiers

    # Check that data reduction completed.
    assert (tmp_path / "data_reduction").is_dir()
    assert (tmp_path / "data_reduction" / "prefilter").is_dir()
    assert (tmp_path / "data_reduction" / "reindex").is_dir()
    assert (tmp_path / "data_reduction" / "scale").is_dir()
    assert (tmp_path / "data_reduction" / "scale" / "merged.mtz").is_file()
    assert (tmp_path / "data_reduction" / "scale" / "scaled.mtz").is_file()

    # now run again to check data reduction from where left off approach
    args = [
        "dev.xia2.ssx_reduce",
        "space_group=P213",
        "directory=batch_1/",
        "d_min=2.0",
    ]
    result = procrunner.run(args, working_directory=tmp_path)
    assert not result.returncode and not result.stderr
