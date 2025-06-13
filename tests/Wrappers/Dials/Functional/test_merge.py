from __future__ import annotations

import pytest
from dials.array_family import flex
from dials.command_line.merge import phil_scope
from dxtbx.serialize import load

from xia2.Wrappers.Dials.Functional.Merge import Merge

params = phil_scope.extract()
params.r_free_flags.d_min = 2.4
params.r_free_flags.d_max = 50.1
params.r_free_flags.fraction = 0.1
params.r_free_flags.extend = True


@pytest.fixture()
def lcy_data(dials_data):
    lcy = dials_data("l_cysteine_4_sweeps_scaled", pathlib=True)
    expts = load.experiment_list(lcy / "scaled_20_25.expt", check_format=False)
    refls = flex.reflection_table.from_file(lcy / "scaled_20_25.refl")
    yield expts, refls


def test_merge(lcy_data, run_in_tmp_path):
    expts, refls = lcy_data
    merge = Merge()
    merge.run(expts, refls)

    # Check output generated
    assert (run_in_tmp_path / "merged.mtz").is_file()
    assert (run_in_tmp_path / f"{merge._xpid}_dials.merge.log").is_file()


def test_non_default_parameters(lcy_data, run_in_tmp_path):
    expts, refls = lcy_data
    merge = Merge()
    merge.set_d_min(2.4)
    merge.set_wavelength_tolerance(0.002)
    merge.set_r_free_params(params.r_free_flags)
    merge.use_xpid = False
    merge.set_assess_space_group(True)
    merge.output_filename = "test_merge.mtz"
    merge.run(expts, refls)

    # Check output generated
    assert (run_in_tmp_path / "test_merge.mtz").is_file()
    assert (run_in_tmp_path / "dials.merge.log").is_file()
