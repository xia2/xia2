from __future__ import absolute_import, division, print_function

import procrunner
import xia2.Test.regression

expected_data_files = [
    "AUTOMATIC_DEFAULT_scaled.mtz",
    "AUTOMATIC_DEFAULT_scaled.sca",
    "AUTOMATIC_DEFAULT_scaled_unmerged.mtz",
    "AUTOMATIC_DEFAULT_scaled_unmerged.sca",
]


def test_dials(regression_test, dials_data, tmpdir, ccp4):
    command_line = [
        "xia2",
        "pipeline=dials",
        "nproc=2",
        "small_molecule=True",
        "read_all_image_headers=False",
        "trust_beam_centre=True",
        dials_data("small_molecule_example").strpath,
    ]
    result = procrunner.run(command_line, working_directory=tmpdir.strpath)
    success, issues = xia2.Test.regression.check_result(
        "small_molecule.dials",
        result,
        tmpdir,
        ccp4,
        expected_data_files=expected_data_files,
    )
    assert success, issues


def test_dials_full(regression_test, dials_data, tmpdir, ccp4):
    command_line = [
        "xia2",
        "pipeline=dials-full",
        "nproc=2",
        "small_molecule=True",
        "read_all_image_headers=False",
        "trust_beam_centre=True",
        dials_data("small_molecule_example").strpath,
    ]
    result = procrunner.run(command_line, working_directory=tmpdir.strpath)
    success, issues = xia2.Test.regression.check_result(
        "small_molecule.dials-full",
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
        "pipeline=3dii",
        "nproc=2",
        "small_molecule=True",
        "read_all_image_headers=False",
        "trust_beam_centre=True",
        dials_data("small_molecule_example").strpath,
    ]
    result = procrunner.run(command_line, working_directory=tmpdir.strpath)
    success, issues = xia2.Test.regression.check_result(
        "small_molecule.xds",
        result,
        tmpdir,
        ccp4,
        xds,
        expected_data_files=expected_data_files,
    )
    assert success, issues


def test_xds_ccp4a(regression_test, dials_data, tmpdir, ccp4, xds):
    command_line = [
        "xia2",
        "pipeline=3dii",
        "nproc=2",
        "small_molecule=True",
        "read_all_image_headers=False",
        "trust_beam_centre=True",
        "scaler=ccp4a",
        dials_data("small_molecule_example").strpath,
    ]
    result = procrunner.run(command_line, working_directory=tmpdir.strpath)
    success, issues = xia2.Test.regression.check_result(
        "small_molecule.ccp4a",
        result,
        tmpdir,
        ccp4,
        xds,
        expected_data_files=expected_data_files,
    )
    assert success, issues
