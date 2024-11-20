# System testing: run xia2 and check for zero exit code


from __future__ import annotations

import os
import subprocess

from xia2.Driver.DriverHelper import windows_resolve


def test_start_xia2():
    cmd = ["xia2"]
    if os.name == "nt":
        cmd = windows_resolve(cmd)
    result = subprocess.run(cmd)
    assert result.returncode == 0
