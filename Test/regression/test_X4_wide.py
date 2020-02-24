from __future__ import absolute_import, division, print_function

import itertools

import procrunner
import pytest
import xia2.Test.regression


def split_xinfo(data_dir, tmpdir):
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
    xinfo_file = tmpdir / "split.xinfo"
    xinfo_file.write(
        split_xinfo_template.format(data_dir.strpath.replace("\\", "\\\\"))
    )
    return xinfo_file.strpath


@pytest.mark.parametrize("pipeline,scaler", (("dials", "xdsa"), ("3dii", "dials")))
def test_incompatible_pipeline_scaler(pipeline, scaler, tmpdir, ccp4):
    command_line = ["xia2", "pipeline=%s" % pipeline, "nproc=1", "scaler=%s" % scaler]
    result = procrunner.run(command_line, working_directory=tmpdir)
    assert result.returncode
    assert "Error: scaler=%s not compatible with pipeline=%s" % (
        scaler,
        pipeline,
    ) in result.stdout.decode("latin-1")


def test_dials_aimless(regression_test, dials_data, tmpdir, ccp4):
    command_line = [
        "xia2",
        "pipeline=dials-aimless",
        "nproc=1",
        "trust_beam_centre=True",
        "read_all_image_headers=False",
        "truncate=cctbx",
        dials_data("x4wide").strpath,
    ]
    result = procrunner.run(command_line, working_directory=tmpdir)
    success, issues = xia2.Test.regression.check_result(
        "X4_wide.dials-aimless", result, tmpdir, ccp4, expected_space_group="P41212"
    )
    assert success, issues


def test_dials_aimless_with_dials_pipeline(regression_test, dials_data, tmpdir, ccp4):
    # This should be functionally equivalent to 'test_dials_aimless' above
    command_line = [
        "xia2",
        "pipeline=dials",
        "scaler=ccp4a",
        "nproc=1",
        "trust_beam_centre=True",
        "read_all_image_headers=False",
        "truncate=cctbx",
        dials_data("x4wide").strpath,
    ]
    result = procrunner.run(command_line, working_directory=tmpdir)
    success, issues = xia2.Test.regression.check_result(
        "X4_wide.dials-aimless", result, tmpdir, ccp4
    )
    assert success, issues


def test_dials(regression_test, dials_data, tmpdir, ccp4):
    command_line = [
        "xia2",
        "pipeline=dials",
        "nproc=1",
        "trust_beam_centre=True",
        "read_all_image_headers=False",
        "truncate=cctbx",
        "free_total=1000",
        dials_data("x4wide").strpath,
    ]
    result = procrunner.run(command_line, working_directory=tmpdir)
    print(result)
    success, issues = xia2.Test.regression.check_result(
        "X4_wide.dials",
        result,
        tmpdir,
        ccp4,
        expected_data_files=[
            "AUTOMATIC_DEFAULT_scaled.mtz",
            "AUTOMATIC_DEFAULT_scaled_unmerged.mtz",
        ],
        expected_space_group="P41212",
    )
    assert success, issues


def test_dials_aimless_split(regression_test, dials_data, tmpdir, ccp4):
    command_line = [
        "xia2",
        "pipeline=dials-aimless",
        "nproc=1",
        "njob=2",
        "mode=parallel",
        "trust_beam_centre=True",
        "xinfo=%s" % split_xinfo(dials_data("x4wide"), tmpdir),
    ]
    result = procrunner.run(command_line, working_directory=tmpdir)
    success, issues = xia2.Test.regression.check_result(
        "X4_wide_split.dials-aimless", result, tmpdir, ccp4
    )
    assert success, issues


@pytest.mark.parametrize("multi_sweep_indexing", (True, False))
def test_dials_split(multi_sweep_indexing, regression_test, dials_data, tmpdir, ccp4):
    command_line = [
        "xia2",
        "pipeline=dials",
        "nproc=1",
        "njob=2",
        "trust_beam_centre=True",
        "multi_sweep_indexing=%s" % multi_sweep_indexing,
        "xinfo=%s" % split_xinfo(dials_data("x4wide"), tmpdir),
    ]
    if not multi_sweep_indexing:
        command_line.append("mode=parallel")
    result = procrunner.run(command_line, working_directory=tmpdir)
    success, issues = xia2.Test.regression.check_result(
        "X4_wide_split.dials",
        result,
        tmpdir,
        ccp4,
        expected_data_files=[
            "AUTOMATIC_DEFAULT_scaled.mtz",
            "AUTOMATIC_DEFAULT_scaled_unmerged.mtz",
        ],
    )
    assert success, issues


def test_xds(regression_test, dials_data, tmpdir, ccp4, xds):
    command_line = [
        "xia2",
        "pipeline=3di",
        "nproc=1",
        "trust_beam_centre=True",
        "read_all_image_headers=False",
        dials_data("x4wide").strpath,
    ]
    result = procrunner.run(command_line, working_directory=tmpdir)
    success, issues = xia2.Test.regression.check_result(
        "X4_wide.xds", result, tmpdir, ccp4, xds, expected_space_group="P41212"
    )
    assert success, issues


def test_xds_split(regression_test, dials_data, tmpdir, ccp4, xds):
    command_line = [
        "xia2",
        "pipeline=3di",
        "nproc=1",
        "njob=2",
        "mode=parallel",
        "trust_beam_centre=True",
        "xinfo=%s" % split_xinfo(dials_data("x4wide"), tmpdir),
    ]
    result = procrunner.run(command_line, working_directory=tmpdir)
    success, issues = xia2.Test.regression.check_result(
        "X4_wide_split.xds", result, tmpdir, ccp4, xds
    )
    assert success, issues


def test_xds_ccp4a(regression_test, dials_data, tmpdir, ccp4, xds):
    command_line = [
        "xia2",
        "pipeline=3di",
        "nproc=1",
        "scaler=ccp4a",
        "trust_beam_centre=True",
        dials_data("x4wide").strpath,
    ]
    result = procrunner.run(command_line, working_directory=tmpdir)
    success, issues = xia2.Test.regression.check_result(
        "X4_wide.ccp4a", result, tmpdir, ccp4, xds
    )
    assert success, issues


def test_xds_ccp4a_split(regression_test, dials_data, tmpdir, ccp4, xds):
    command_line = [
        "xia2",
        "pipeline=3di",
        "nproc=1",
        "scaler=ccp4a",
        "njob=2",
        "merging_statistics.source=aimless",
        "trust_beam_centre=True",
        "mode=parallel",
        "xinfo=%s" % split_xinfo(dials_data("x4wide"), tmpdir),
    ]
    result = procrunner.run(command_line, working_directory=tmpdir)
    success, issues = xia2.Test.regression.check_result(
        "X4_wide_split.ccp4a", result, tmpdir, ccp4, xds
    )
    assert success, issues


@pytest.mark.parametrize(
    "pipeline,space_group",
    itertools.product(("dials", "dials-aimless", "3dii"), ("P41212", "P422")),
)
def test_space_group(pipeline, space_group, regression_test, dials_data, tmpdir, ccp4):
    command_line = [
        "xia2",
        "pipeline=%s" % pipeline,
        "space_group=%s" % space_group,
        "nproc=1",
        "trust_beam_centre=True",
        "read_all_image_headers=False",
        "truncate=cctbx",
        "free_total=1000",
        "image=%s" % dials_data("x4wide").join("X4_wide_M1S4_2_0001.cbf:20:30"),
    ]
    result = procrunner.run(command_line, working_directory=tmpdir)
    success, issues = xia2.Test.regression.check_result(
        "X4_wide.space_group.%s" % pipeline,
        result,
        tmpdir,
        ccp4,
        expected_data_files=[],
        expected_space_group=space_group,
    )
    assert success, issues
