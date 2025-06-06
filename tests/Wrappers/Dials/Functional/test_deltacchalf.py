from __future__ import annotations

from dials.array_family import flex
from dxtbx.serialize import load

from xia2.Wrappers.Dials.Functional.DeltaCCHalf import DeltaCCHalf


def test_deltacchalf(dials_data, run_in_tmp_path):
    lcy = dials_data("l_cysteine_4_sweeps_scaled", pathlib=True)
    deltacc = DeltaCCHalf()
    expts = load.experiment_list(lcy / "scaled_20_25.expt", check_format=False)
    refls = flex.reflection_table.from_file(lcy / "scaled_20_25.refl")
    deltacc.run(expts, refls)

    # Check the outputs have been generated as expected and are not empty
    assert deltacc.delta_cc_half_graphs["delta_cc_half_histogram"]["data"]
    assert deltacc.delta_cc_half_graphs["delta_cc_half_normalised_score"]["data"]
    assert len(deltacc.delta_cc_half_table) == 3
