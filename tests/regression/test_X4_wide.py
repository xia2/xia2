from __future__ import annotations

import subprocess

import iotbx.mtz
import pytest
from dxtbx.serialize import load

import xia2.Test.regression


def _split_xinfo(data_dir, tmp_path) -> str:
    split_xinfo_template = """/
BEGIN PROJECT AUTOMATIC
BEGIN CRYSTAL DEFAULT

BEGIN WAVELENGTH NATIVE
WAVELENGTH 0.979500
END WAVELENGTH NATIVE

BEGIN SWEEP SWEEP1
WAVELENGTH NATIVE
DIRECTORY {0}
IMAGE X4_wide_M1S4_2_0001.cbf
START_END 1 40
BEAM 219.84 212.65
END SWEEP SWEEP1

BEGIN SWEEP SWEEP2
WAVELENGTH NATIVE
DIRECTORY {0}
IMAGE X4_wide_M1S4_2_0001.cbf
START_END 45 90
BEAM 219.84 212.65
END SWEEP SWEEP2

END CRYSTAL DEFAULT
END PROJECT AUTOMATIC
"""
    xinfo_file = tmp_path / "split.xinfo"
    xinfo_file.write_text(
        split_xinfo_template.format(str(data_dir).replace("\\", "\\\\"))
    )
    return str(xinfo_file)


@pytest.mark.parametrize("pipeline,scaler", (("dials", "xdsa"), ("3dii", "dials")))
def test_incompatible_pipeline_scaler(pipeline, scaler, tmp_path, ccp4):
    result = subprocess.run(
        ["xia2", f"pipeline={pipeline}", "nproc=1", f"scaler={scaler}"],
        cwd=tmp_path,
        capture_output=True,
    )
    assert result.returncode
    assert (
        f"Error: scaler={scaler} not compatible with pipeline={pipeline}"
        in result.stdout.decode("latin-1")
    )


def test_dials_aimless(regression_test, dials_data, tmp_path, ccp4):
    command_line = [
        "xia2",
        "pipeline=dials-aimless",
        "nproc=1",
        "trust_beam_centre=True",
        "read_all_image_headers=False",
        "truncate=cctbx",
        dials_data("x4wide", pathlib=True),
    ]
    result = subprocess.run(command_line, cwd=tmp_path, capture_output=True)
    success, issues = xia2.Test.regression.check_result(
        "X4_wide.dials-aimless", result, tmp_path, ccp4, expected_space_group="P41212"
    )
    assert success, issues


def test_dials_aimless_with_dials_pipeline(regression_test, dials_data, tmp_path, ccp4):
    # This should be functionally equivalent to 'test_dials_aimless' above
    command_line = [
        "xia2",
        "pipeline=dials",
        "scaler=ccp4a",
        "nproc=1",
        "trust_beam_centre=True",
        "read_all_image_headers=False",
        "truncate=cctbx",
        dials_data("x4wide", pathlib=True),
    ]
    result = subprocess.run(command_line, cwd=tmp_path, capture_output=True)
    success, issues = xia2.Test.regression.check_result(
        "X4_wide.dials-aimless", result, tmp_path, ccp4
    )
    assert success, issues


def test_dials(regression_test, dials_data, tmp_path, ccp4):
    command_line = [
        "xia2",
        "pipeline=dials",
        "nproc=1",
        "trust_beam_centre=True",
        "read_all_image_headers=False",
        "truncate=cctbx",
        "free_total=1000",
        "project=foo",
        "crystal=bar",
        dials_data("x4wide", pathlib=True),
    ]
    result = subprocess.run(command_line, cwd=tmp_path, capture_output=True)
    scaled_expt_file = tmp_path / "DataFiles" / "foo_bar_scaled.expt"
    assert scaled_expt_file.is_file()
    scaled_expt = load.experiment_list(scaled_expt_file)
    for crystal in scaled_expt.crystals():
        assert crystal.get_recalculated_unit_cell() is not None
        assert len(crystal.get_recalculated_cell_parameter_sd()) == 6
        assert crystal.get_recalculated_cell_volume_sd() > 0
    for mtz_file in (
        "foo_bar_scaled.mtz",
        "foo_bar_free.mtz",
        "foo_bar_scaled_unmerged.mtz",
    ):
        mtz_obj = iotbx.mtz.object(str(tmp_path / "DataFiles" / mtz_file))
        assert mtz_obj.crystals()[1].project_name() == "foo"
        assert mtz_obj.crystals()[1].name() == "bar"
        for ma in mtz_obj.as_miller_arrays():
            assert ma.unit_cell().parameters() == pytest.approx(
                scaled_expt[0].crystal.get_recalculated_unit_cell().parameters(),
                abs=1e-4,
            )
    success, issues = xia2.Test.regression.check_result(
        "X4_wide.dials",
        result,
        tmp_path,
        ccp4,
        expected_data_files=[
            "foo_bar_scaled.mtz",
            "foo_bar_scaled_unmerged.mtz",
            "foo_bar_scaled.sca",
            "foo_bar_scaled_unmerged.sca",
        ],
        expected_space_group="P41212",
    )
    assert success, issues


def test_dials_aimless_split(regression_test, dials_data, tmp_path, ccp4):
    command_line = [
        "xia2",
        "pipeline=dials-aimless",
        "nproc=1",
        "njob=2",
        "mode=parallel",
        "trust_beam_centre=True",
        "xinfo=%s" % _split_xinfo(dials_data("x4wide", pathlib=True), tmp_path),
    ]
    result = subprocess.run(command_line, cwd=tmp_path, capture_output=True)
    success, issues = xia2.Test.regression.check_result(
        "X4_wide_split.dials-aimless", result, tmp_path, ccp4
    )
    assert success, issues


def test_dials_split(regression_test, dials_data, tmp_path, ccp4):
    command_line = [
        "xia2",
        "pipeline=dials",
        "nproc=1",
        "njob=2",
        "trust_beam_centre=True",
        "xinfo=%s" % _split_xinfo(dials_data("x4wide", pathlib=True), tmp_path),
        "mode=parallel",
    ]
    result = subprocess.run(command_line, cwd=tmp_path, capture_output=True)
    success, issues = xia2.Test.regression.check_result(
        "X4_wide_split.dials",
        result,
        tmp_path,
        ccp4,
        expected_data_files=[
            "AUTOMATIC_DEFAULT_scaled.mtz",
            "AUTOMATIC_DEFAULT_scaled_unmerged.mtz",
        ],
    )
    assert success, issues


def test_xds(regression_test, dials_data, tmp_path, ccp4, xds):
    command_line = [
        "xia2",
        "pipeline=3di",
        "nproc=1",
        "trust_beam_centre=True",
        "read_all_image_headers=False",
        dials_data("x4wide", pathlib=True),
    ]
    result = subprocess.run(command_line, cwd=tmp_path, capture_output=True)
    success, issues = xia2.Test.regression.check_result(
        "X4_wide.xds", result, tmp_path, ccp4, xds, expected_space_group="P41212"
    )
    assert success, issues


def test_xds_split(regression_test, dials_data, tmp_path, ccp4, xds):
    command_line = [
        "xia2",
        "pipeline=3di",
        "nproc=1",
        "njob=2",
        "mode=parallel",
        "trust_beam_centre=True",
        "xinfo=%s" % _split_xinfo(dials_data("x4wide", pathlib=True), tmp_path),
    ]
    result = subprocess.run(command_line, cwd=tmp_path, capture_output=True)
    success, issues = xia2.Test.regression.check_result(
        "X4_wide_split.xds", result, tmp_path, ccp4, xds
    )
    assert success, issues


def test_xds_ccp4a(regression_test, dials_data, tmp_path, ccp4, xds):
    command_line = [
        "xia2",
        "pipeline=3di",
        "nproc=1",
        "scaler=ccp4a",
        "trust_beam_centre=True",
        dials_data("x4wide", pathlib=True),
    ]
    result = subprocess.run(command_line, cwd=tmp_path, capture_output=True)
    success, issues = xia2.Test.regression.check_result(
        "X4_wide.ccp4a", result, tmp_path, ccp4, xds
    )
    assert success, issues


def test_xds_ccp4a_split(regression_test, dials_data, tmp_path, ccp4, xds):
    command_line = [
        "xia2",
        "pipeline=3di",
        "nproc=1",
        "scaler=ccp4a",
        "njob=2",
        "merging_statistics.source=aimless",
        "trust_beam_centre=True",
        "mode=parallel",
        "xinfo=%s" % _split_xinfo(dials_data("x4wide", pathlib=True), tmp_path),
    ]
    result = subprocess.run(command_line, cwd=tmp_path, capture_output=True)
    success, issues = xia2.Test.regression.check_result(
        "X4_wide_split.ccp4a", result, tmp_path, ccp4, xds
    )
    assert success, issues


@pytest.mark.parametrize("space_group", ("P41212", "P422"))
@pytest.mark.parametrize("pipeline", ("dials", "dials-aimless"))
def test_space_group_dials(
    pipeline, space_group, regression_test, dials_data, tmp_path, ccp4
):
    command_line = [
        "xia2",
        "pipeline=%s" % pipeline,
        f"space_group={space_group}",
        "nproc=1",
        "trust_beam_centre=True",
        "read_all_image_headers=False",
        "truncate=cctbx",
        "free_total=1000",
        "image=%s"
        % dials_data("x4wide", pathlib=True).joinpath("X4_wide_M1S4_2_0001.cbf:20:30"),
    ]
    result = subprocess.run(command_line, cwd=tmp_path, capture_output=True)
    success, issues = xia2.Test.regression.check_result(
        "X4_wide.space_group.%s" % pipeline,
        result,
        tmp_path,
        ccp4,
        expected_space_group=space_group,
    )
    assert success, issues


@pytest.mark.parametrize("space_group", ("P41212", "P422"))
def test_space_group_3dii(
    space_group, regression_test, dials_data, tmp_path, ccp4, xds
):
    command_line = [
        "xia2",
        "pipeline=3dii",
        f"space_group={space_group}",
        "nproc=1",
        "trust_beam_centre=True",
        "read_all_image_headers=False",
        "truncate=cctbx",
        "free_total=1000",
        "image=%s"
        % dials_data("x4wide", pathlib=True).joinpath("X4_wide_M1S4_2_0001.cbf:20:30"),
    ]
    result = subprocess.run(command_line, cwd=tmp_path, capture_output=True)
    success, issues = xia2.Test.regression.check_result(
        "X4_wide.space_group.3dii",
        result,
        tmp_path,
        ccp4,
        xds=xds,
        expected_space_group=space_group,
    )
    assert success, issues
