# System testing: run xia2 and check for zero exit code


from __future__ import annotations

import os
import subprocess


def test_start_xia2():
    cmd = "xia2"
    if os.name == "nt":
        cmd += ".bat"
    result = subprocess.run([cmd])
    assert result.returncode == 0
