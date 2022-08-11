from __future__ import annotations

import subprocess


def test_to_shelx(dials_data, tmp_path):

    l_cyst = dials_data("l_cysteine_4_sweeps_scaled", pathlib=True)
    # First create an unmerged mtz.
    expt = l_cyst / "scaled_30.expt"
    refls = l_cyst / "scaled_30.refl"
    result = subprocess.run(
        ["dials.export", expt, refls, "mtz.hklout=scaled.mtz"], cwd=tmp_path
    )
    assert not result.returncode or result.stderr

    # now test the program
    args = ["xia2.to_shelx", tmp_path / "scaled.mtz", "lcys", "C3H7NO2S"]
    result = subprocess.run(args, cwd=tmp_path)
    assert not result.returncode or result.stderr

    # now test the program with '--cell' option
    args.append(f"--cell={expt}")
    result = subprocess.run(args, cwd=tmp_path)
    assert not result.returncode or result.stderr
