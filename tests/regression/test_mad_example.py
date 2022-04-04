from __future__ import annotations

import procrunner

import xia2.Test.regression

expected_data_files = [
    "AUTOMATIC_DEFAULT_free.mtz",
    "AUTOMATIC_DEFAULT_scaled_WAVE2.sca",
    "AUTOMATIC_DEFAULT_scaled_unmerged_WAVE1.sca",
    "AUTOMATIC_DEFAULT_scaled_unmerged_WAVE2.sca",
    "AUTOMATIC_DEFAULT_scaled_WAVE1.sca",
    "AUTOMATIC_DEFAULT_scaled_unmerged_WAVE1.mtz",
    "AUTOMATIC_DEFAULT_scaled_unmerged_WAVE2.mtz",
]


def test_dials(regression_test, dials_data, tmp_path, ccp4):
    command_line = [
        "xia2",
        "pipeline=dials",
        "nproc=1",
        "njob=2",
        "mode=parallel",
        "trust_beam_centre=True",
        dials_data("fumarase", pathlib=True),
    ]
    result = procrunner.run(command_line, working_directory=tmp_path)
    success, issues = xia2.Test.regression.check_result(
        "mad_example.dials",
        result,
        tmp_path,
        ccp4,
        expected_data_files=expected_data_files,
    )
    assert success, issues


def test_dials_aimless(regression_test, dials_data, tmp_path, ccp4):
    command_line = [
        "xia2",
        "pipeline=dials-aimless",
        "nproc=1",
        "njob=2",
        "mode=parallel",
        "trust_beam_centre=True",
        dials_data("fumarase", pathlib=True),
    ]
    result = procrunner.run(command_line, working_directory=tmp_path)
    success, issues = xia2.Test.regression.check_result(
        "mad_example.dials-aimless",
        result,
        tmp_path,
        ccp4,
        expected_data_files=expected_data_files,
    )
    assert success, issues


def test_xds(regression_test, dials_data, tmp_path, ccp4, xds):
    command_line = [
        "xia2",
        "pipeline=3di",
        "nproc=1",
        "njob=2",
        "mode=parallel",
        "trust_beam_centre=True",
        dials_data("fumarase", pathlib=True),
    ]
    result = procrunner.run(command_line, working_directory=tmp_path)
    success, issues = xia2.Test.regression.check_result(
        "mad_example.xds",
        result,
        tmp_path,
        ccp4,
        xds,
        expected_data_files=expected_data_files,
    )
    assert success, issues


def test_xds_ccp4a(regression_test, dials_data, tmp_path, ccp4, xds):
    command_line = [
        "xia2",
        "pipeline=3di",
        "nproc=1",
        "njob=2",
        "mode=parallel",
        "trust_beam_centre=True",
        "scaler=ccp4a",
        dials_data("fumarase", pathlib=True),
    ]
    result = procrunner.run(command_line, working_directory=tmp_path)
    success, issues = xia2.Test.regression.check_result(
        "mad_example.ccp4a",
        result,
        tmp_path,
        ccp4,
        xds,
        expected_data_files=expected_data_files,
    )
    assert success, issues
