from __future__ import annotations

import os

from iotbx.reflection_file_reader import any_reflection_file

import xia2.Modules.CctbxFrenchWilson


def test_french_wilson(dials_data, tmp_path):
    scaled_mtz = (
        dials_data("x4wide_processed", pathlib=True) / "AUTOMATIC_DEFAULT_scaled.mtz"
    )
    truncated_mtz = tmp_path / "truncate.mtz"
    xia2.Modules.CctbxFrenchWilson.do_french_wilson(
        scaled_mtz, truncated_mtz, anomalous=True
    )
    assert truncated_mtz.is_file()
    result = any_reflection_file(os.fspath(truncated_mtz))
    assert result.file_type() == "ccp4_mtz"
    all_labels = [
        ma.info().labels for ma in result.as_miller_arrays(merge_equivalents=False)
    ]

    for expected in (
        ["F", "SIGF"],
        ["F(+)", "SIGF(+)", "F(-)", "SIGF(-)"],
        ["DANO", "SIGDANO"],
    ):
        assert expected in all_labels
