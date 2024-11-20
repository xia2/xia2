from __future__ import annotations

import os
import subprocess

import pytest

import xia2.Test.regression
from xia2.Driver.DriverHelper import windows_resolve


@pytest.mark.parametrize("pipeline", ["dials", "3dii"])
def test_xia2(pipeline, regression_test, dials_data, tmp_path, ccp4):
    master_h5 = (
        dials_data("vmxi_thaumatin", pathlib=True) / "image_15799_master.h5:1:20"
    )
    command_line = [
        "xia2",
        f"pipeline={pipeline}",
        "nproc=1",
        "trust_beam_centre=True",
        "read_all_image_headers=False",
        "space_group=P41212",
        f"image={master_h5}",
    ]
    if os.name == "nt":
        command_line = windows_resolve(command_line)
    result = subprocess.run(command_line, cwd=tmp_path, capture_output=True)
    success, issues = xia2.Test.regression.check_result(
        f"vmxi_thaumatin.{pipeline}",
        result,
        tmp_path,
        ccp4,
        expected_space_group="P41212",
    )
    assert success, issues
