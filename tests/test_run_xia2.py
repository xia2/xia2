# System testing: run xia2 and check for zero exit code


from __future__ import annotations

import subprocess


def test_start_xia2():
    result = subprocess.run(["xia2"])
    assert result.returncode == 0
