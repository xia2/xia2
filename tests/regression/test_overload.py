from __future__ import annotations

import shutil
import subprocess


def test(dials_data, tmp_path):
    images = list(dials_data("centroid_test_data", pathlib=True).glob("centroid*.cbf"))

    cmd = [shutil.which("xia2.overload")]
    result = subprocess.run(cmd + images, cwd=tmp_path, capture_output=True)
    assert not result.returncode and not result.stderr
    assert (tmp_path / "overload.json").is_file()
