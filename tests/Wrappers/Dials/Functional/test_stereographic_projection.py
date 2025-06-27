from __future__ import annotations

from dxtbx.serialize import load

from xia2.Wrappers.Dials.Functional.StereographicProjection import (
    StereographicProjection,
)


def test_stereographicprojection(dials_data, run_in_tmp_path):
    lcy = dials_data("l_cysteine_4_sweeps_scaled", pathlib=True)
    sp = StereographicProjection()
    expts = load.experiment_list(lcy / "scaled_20_25.expt", check_format=False)
    sp.hkl = (1, 0, 0)
    sp.labels = ["0", "2"]
    sp.run(expts)
    file1 = sp.json_filename
    log1 = sp.logfile
    assert (file1).is_file()
    assert (log1).is_file()
    sp.hkl = (0, 1, 0)
    sp.run(expts)
    file2 = sp.json_filename
    log2 = sp.logfile
    assert file2 != file1
    assert log2 != log1
    assert (file2).is_file()
    assert (log2).is_file()
