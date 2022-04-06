from __future__ import annotations

import procrunner
import pytest

import xia2.Test.regression


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
    result = procrunner.run(command_line, working_directory=tmp_path)
    success, issues = xia2.Test.regression.check_result(
        f"vmxi_thaumatin.{pipeline}",
        result,
        tmp_path,
        ccp4,
        expected_space_group="P41212",
    )
    assert success, issues
