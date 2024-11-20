from __future__ import annotations

import os
import subprocess

from xia2.Driver.DriverHelper import windows_resolve


def test(dials_data, tmp_path):
    images = list(dials_data("centroid_test_data", pathlib=True).glob("centroid*.cbf"))

    cmd = ["xia2.overload"]
    if os.name == "nt":
        cmd = windows_resolve(cmd)
    result = subprocess.run(cmd + images, cwd=tmp_path, capture_output=True)
    assert not result.returncode and not result.stderr
    assert (tmp_path / "overload.json").is_file()
