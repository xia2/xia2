from __future__ import absolute_import, division, print_function

import os

from iotbx.reflection_file_reader import any_reflection_file
from xia2.Modules import CctbxFrenchWilson


def test_french_wilson(dials_data):
    scaled_mtz = dials_data("x4wide_processed").join("AUTOMATIC_DEFAULT_scaled.mtz")
    CctbxFrenchWilson.run([scaled_mtz.strpath, "anomalous=True"])
    assert os.path.exists("truncate.mtz")
    result = any_reflection_file("truncate.mtz")
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
