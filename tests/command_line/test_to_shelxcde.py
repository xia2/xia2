from __future__ import annotations

import os

import pytest
from libtbx.utils import Sorry

from xia2.cli import to_shelxcde

expected_sad_files = [
    "test.hkl",
    "test.sh",
]


expected_native_files = [
    "test_nat.hkl",
]


expected_sad_script = """shelxc test << eof
cell 42.369499 42.369499 39.691502 90.000000 90.000000 90.000000
spag P41212
sad test.hkl
maxm 1
eof
"""


expected_sites_script = """shelxc test << eof
cell 42.369499 42.369499 39.691502 90.000000 90.000000 90.000000
spag P41212
sad test.hkl
find 10
maxm 1
eof
"""


expected_native_script = """shelxc test << eof
cell 42.369499 42.369499 39.691502 90.000000 90.000000 90.000000
spag P41212
sad test.hkl
nat test_nat.hkl
maxm 1
eof
"""


def check_output(expected_files, expected_sh_script):
    for expected_file in expected_files:
        assert os.path.exists(expected_file)
        if ".sh" in expected_file:
            with open(expected_file) as fp:
                test_sh = fp.read()
            assert test_sh == expected_sh_script


def test_to_shelxcde_sad(dials_data, run_in_tmp_path):
    input_mtz = dials_data("x4wide_processed", pathlib=True) / (
        "AUTOMATIC_DEFAULT_scaled_unmerged.mtz"
    )
    to_shelxcde.run(["--sad", str(input_mtz), "test"])
    check_output(expected_sad_files, expected_sad_script)


def test_to_shelxcde_sad_sites(dials_data, run_in_tmp_path):
    input_mtz = dials_data("x4wide_processed", pathlib=True) / (
        "AUTOMATIC_DEFAULT_scaled_unmerged.mtz"
    )
    to_shelxcde.run(["--sad", str(input_mtz), "--sites", "10", "test"])
    check_output(expected_sad_files, expected_sites_script)


def test_to_shelxcde_sad_label(dials_data, run_in_tmp_path):
    input_mtz = dials_data("x4wide_processed", pathlib=True) / (
        "AUTOMATIC_DEFAULT_scaled_unmerged.mtz"
    )
    to_shelxcde.run(["--sad", str(input_mtz), "--label", "SIGI", "test"])
    check_output(expected_sad_files, expected_sad_script)


def test_to_shelxcde_sad_native(dials_data, run_in_tmp_path):
    input_mtz = dials_data("x4wide_processed", pathlib=True) / (
        "AUTOMATIC_DEFAULT_scaled_unmerged.mtz"
    )
    to_shelxcde.run(["--sad", str(input_mtz), "--nat", str(input_mtz), "test"])
    check_output(expected_sad_files + expected_native_files, expected_native_script)


def test_to_shelxcde_missing_input_file(dials_data, run_in_tmp_path):
    with pytest.raises(SystemExit):
        to_shelxcde.run(["tmp"])


def test_to_shelxcde_missing_prefix(dials_data, run_in_tmp_path):
    input_mtz = dials_data("x4wide_processed", pathlib=True) / (
        "AUTOMATIC_DEFAULT_scaled_unmerged.mtz"
    )
    with pytest.raises(SystemExit):
        to_shelxcde.run(["--sad", str(input_mtz)])


def test_to_shelxcde_invalid_args_sad_mad(dials_data, run_in_tmp_path):
    input_mtz = dials_data("x4wide_processed", pathlib=True) / (
        "AUTOMATIC_DEFAULT_scaled_unmerged.mtz"
    )
    with pytest.raises(SystemExit):
        to_shelxcde.run(["--sad", str(input_mtz), "--mad", str(input_mtz), "tmp"])


def test_to_shelxcde_invalid_args_sad_peak(dials_data, run_in_tmp_path):
    input_mtz = dials_data("x4wide_processed", pathlib=True) / (
        "AUTOMATIC_DEFAULT_scaled_unmerged.mtz"
    )
    with pytest.raises(SystemExit):
        to_shelxcde.run(["--sad", str(input_mtz), "--peak", str(input_mtz), "tmp"])


def test_to_shelxcde_invalid_args_mad_label(dials_data, run_in_tmp_path):
    input_mtz = dials_data("x4wide_processed", pathlib=True) / (
        "AUTOMATIC_DEFAULT_scaled_unmerged.mtz"
    )
    with pytest.raises(SystemExit):
        to_shelxcde.run(["--mad", str(input_mtz), "--label", "invalid", "tmp"])


def test_to_shelxcde_invalid_input_file(dials_data, run_in_tmp_path):
    with pytest.raises(Sorry):
        to_shelxcde.run(["--sad", "invalid_file", "tmp"])


def test_to_shelxcde_invalid_label(dials_data, run_in_tmp_path):
    input_mtz = dials_data("x4wide_processed", pathlib=True) / (
        "AUTOMATIC_DEFAULT_scaled_unmerged.mtz"
    )
    with pytest.raises(ValueError):
        to_shelxcde.run(["--sad", str(input_mtz), "--label", "invalid", "test"])
