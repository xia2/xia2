from __future__ import annotations

import shutil
import subprocess

import pytest
from dials.array_family import flex
from dxtbx.serialize import load

from xia2.Wrappers.Dials.Functional.Export import Export

#### NEED TO UPDATE TEST DATA


@pytest.fixture()
def sm_data(dials_data, tmp_path, ccp4):
    # sm = dials_data("small_molecule_example", pathlib=True)
    command_line = [
        shutil.which("xia2"),
        "pipeline=dials",
        "nproc=2",
        "small_molecule=True",
        "read_all_image_headers=False",
        "trust_beam_centre=True",
        dials_data("small_molecule_example", pathlib=True),
    ]
    subprocess.run(command_line, cwd=tmp_path, capture_output=True)

    expts = load.experiment_list(
        tmp_path / "DataFiles" / "AUTOMATIC_DEFAULT_scaled.expt", check_format=False
    )
    refls = flex.reflection_table.from_file(
        tmp_path / "DataFiles" / "AUTOMATIC_DEFAULT_scaled.refl"
    )
    yield expts, refls


def test_merge(sm_data, run_in_tmp_path):
    expts, refls = sm_data
    export = Export()
    export.run(expts, refls)

    # Check output generated
    assert (run_in_tmp_path / "dials.hkl").is_file()
    assert (run_in_tmp_path / "dials.ins").is_file()
    assert (run_in_tmp_path / f"{export._xpid}_dials.export.log").is_file()


def test_non_default_parameters(sm_data, run_in_tmp_path):
    expts, refls = sm_data
    export = Export()
    export.use_xpid = False
    export.set_composition("RuCHNO")  ##### CHANGE THIS FOR WHAT THE THING IS
    export.set_output_names = "test_export"
    export.run(expts, refls)

    # Check output generated
    assert (run_in_tmp_path / "test_export.hkl").is_file()
    assert (run_in_tmp_path / "test_export.ins").is_file()
    assert (run_in_tmp_path / "dials.export.log").is_file()
