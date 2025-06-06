from __future__ import annotations

import copy

from dials.array_family import flex
from dxtbx.serialize import load

from xia2.cli.multiplex import phil_scope
from xia2.Modules.MultiCrystal.ScaleAndMerge import MultiCrystalScale


def test_init(dials_data):
    """
    Test the filtering done as part of the initialisation of the MultiCrystalScale class
    """
    params = phil_scope.extract()
    lcy = dials_data("l_cysteine_4_sweeps_scaled", pathlib=True)
    expts = load.experiment_list(lcy / "scaled_20_25.expt", check_format=False)
    refls = flex.reflection_table.from_file(lcy / "scaled_20_25.refl")
    identifiers = list(expts.identifiers())

    # Unset the integrated_prf flags for the second dataset.
    refls1 = copy.deepcopy(refls)
    sel = refls1["id"] == 1
    refls1.unset_flags(sel, refls1.flags.integrated_prf)

    runner = MultiCrystalScale(expts, refls1, params)
    assert list(runner._data_manager.experiments.identifiers()) == [identifiers[0]]

    # Unset the used_in_refinement flags for the second dataset.
    refls2 = copy.deepcopy(refls)
    sel = refls2["id"] == 0
    refls2.unset_flags(sel, refls2.flags.used_in_refinement)

    runner = MultiCrystalScale(expts, refls2, params)
    assert list(runner._data_manager.experiments.identifiers()) == [identifiers[1]]

    # If no datasets have the flags set, then all are kept (or we would have no data)
    refls3 = copy.deepcopy(refls)
    sel = flex.bool(refls.size())
    refls3.unset_flags(sel, refls3.flags.used_in_refinement)
    refls3.unset_flags(sel, refls3.flags.integrated_prf)

    runner = MultiCrystalScale(expts, refls3, params)
    assert list(runner._data_manager.experiments.identifiers()) == identifiers
