from __future__ import annotations

import pytest
from dials.array_family import flex
from dxtbx.serialize import load

from xia2.Wrappers.Dials.Functional.Export import Export


@pytest.fixture()
def lcy_data(dials_data):
    lcy = dials_data("l_cysteine_4_sweeps_scaled", pathlib=True)
    expts = load.experiment_list(lcy / "scaled_20_25.expt", check_format=False)
    refls = flex.reflection_table.from_file(lcy / "scaled_20_25.refl")
    yield expts, refls


@pytest.fixture()
def lcy_data_unscaled(dials_data):
    lcy_unscaled = dials_data("l_cysteine_dials_output", pathlib=True)
    expts = load.experiment_list(
        lcy_unscaled / "23_integrated.expt", check_format=False
    )
    refls = flex.reflection_table.from_file(lcy_unscaled / "23_integrated.refl")
    yield expts, refls


def test_merge(lcy_data, run_in_tmp_path):
    expts, refls = lcy_data
    export = Export()
    export.run(expts, refls)

    # Check output generated
    assert (run_in_tmp_path / "dials.hkl").is_file()
    assert (run_in_tmp_path / "dials.ins").is_file()
    assert (run_in_tmp_path / f"{export._xpid}_dials.export.log").is_file()


def test_non_default_parameters(lcy_data, run_in_tmp_path):
    expts, refls = lcy_data
    export = Export()
    export.use_xpid = False
    export.set_composition("C26NiP2Cl2")
    export.set_output_names("test_export")
    export.run(expts, refls)

    # Check output generated
    assert (run_in_tmp_path / "test_export.hkl").is_file()
    assert (run_in_tmp_path / "test_export.ins").is_file()
    assert (run_in_tmp_path / "dials.export.log").is_file()


def test_unscaled(lcy_data_unscaled, run_in_tmp_path):
    expts, refls = lcy_data_unscaled
    export = Export()
    export.run(expts, refls)
    # Check output generated
    assert (run_in_tmp_path / "dials.hkl").is_file()
    assert (run_in_tmp_path / "dials.ins").is_file()
    assert (run_in_tmp_path / f"{export._xpid}_dials.export.log").is_file()
