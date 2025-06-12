from __future__ import annotations

from dials.array_family import flex
from dxtbx.serialize import load

from xia2.Wrappers.Dials.Functional.Merge import Merge


def test_merge(dials_data, run_in_tmp_path):
    lcy = dials_data("l_cysteine_4_sweeps_scaled", pathlib=True)
    expts = load.experiment_list(lcy / "scaled_20_25.expt", check_format=False)
    refls = flex.reflection_table.from_file(lcy / "scaled_20_25.refl")
    merge = Merge()
    merge.run(expts, [refls])

    # Check outputs generated
    assert (run_in_tmp_path / "merged.mtz").is_file()
