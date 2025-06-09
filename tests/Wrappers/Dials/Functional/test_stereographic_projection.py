from __future__ import annotations

from dxtbx.serialize import load

from xia2.Wrappers.Dials.Functional.StereographicProjection import (
    StereographicProjection,
)


def test_deltacchalf(dials_data, run_in_tmp_path):
    lcy = dials_data("l_cysteine_4_sweeps_scaled", pathlib=True)
    sp = StereographicProjection()
    expts = load.experiment_list(lcy / "scaled_20_25.expt", check_format=False)
    sp.set_hkl((1, 0, 0))
    sp.run(expts)
    assert (run_in_tmp_path / "1_stereographic_projection_100.json").is_file()
