from __future__ import annotations

import os
import subprocess


def test_to_shelx(dials_data, tmp_path):
    l_cyst = dials_data("l_cysteine_4_sweeps_scaled", pathlib=True)
    # First create an unmerged mtz.
    expt = l_cyst / "scaled_30.expt"
    refls = l_cyst / "scaled_30.refl"
    cmd = "dials.export"
    if os.name == "nt":
        cmd += ".bat"
    result = subprocess.run([cmd, expt, refls, "mtz.hklout=scaled.mtz"], cwd=tmp_path)
    assert not result.returncode or result.stderr

    # now test the program
    cmd = "xia2.to_shelx"
    if os.name == "nt":
        cmd += ".bat"
    args = [cmd, tmp_path / "scaled.mtz", "lcys", "C3H7NO2S"]
    result = subprocess.run(args, cwd=tmp_path)
    assert not result.returncode or result.stderr
    assert (tmp_path / "lcys.hkl").is_file()
    assert (tmp_path / "lcys.ins").is_file()

    # now test the program with '--cell' option
    args = [
        cmd,
        tmp_path / "scaled.mtz",
        "lcyst",
        "C3H7NO2S",
        f"--cell={expt}",
    ]
    result = subprocess.run(args, cwd=tmp_path)
    assert not result.returncode or result.stderr
    assert (tmp_path / "lcyst.hkl").is_file()
    assert (tmp_path / "lcyst.ins").is_file()
