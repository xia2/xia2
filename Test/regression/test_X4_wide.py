from __future__ import absolute_import, division, print_function

import procrunner
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
    result = procrunner.run(command_line, working_directory=tmpdir.strpath)
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
    result = procrunner.run(command_line, working_directory=tmpdir.strpath)
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
    result = procrunner.run(command_line, working_directory=tmpdir.strpath)
    success, issues = xia2.Test.regression.check_result(
        "X4_wide_split.dials-aimless", result, tmpdir, ccp4
    )
    assert success, issues


def test_dials_split(regression_test, dials_data, tmpdir, ccp4):
    command_line = [
        "xia2",
        "pipeline=dials",
        "nproc=1",
        "njob=2",
        "mode=parallel",
        "trust_beam_centre=True",
        "xinfo=%s" % split_xinfo(dials_data("x4wide"), tmpdir),
    ]
    result = procrunner.run(command_line, working_directory=tmpdir.strpath)
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
    result = procrunner.run(command_line, working_directory=tmpdir.strpath)
    success, issues = xia2.Test.regression.check_result(
        "X4_wide.xds", result, tmpdir, ccp4, xds
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
    result = procrunner.run(command_line, working_directory=tmpdir.strpath)
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
    result = procrunner.run(command_line, working_directory=tmpdir.strpath)
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
    result = procrunner.run(command_line, working_directory=tmpdir.strpath)
    success, issues = xia2.Test.regression.check_result(
        "X4_wide_split.ccp4a", result, tmpdir, ccp4, xds
    )
    assert success, issues
