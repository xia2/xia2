from __future__ import annotations

import pytest
from dials.array_family import flex
from dials.util.multi_dataset_handling import (
    assign_unique_identifiers,
)
from dxtbx.model import ExperimentList
from dxtbx.serialize import load

from xia2.Wrappers.Dials.Functional.CorrelationMatrix import DialsCorrelationMatrix


@pytest.fixture()
def proteinase_k(dials_data):
    expts = ExperimentList()
    refls = []
    mcp = dials_data("vmxi_proteinase_k_sweeps", pathlib=True)
    for i in [0, 1, 2, 3]:
        expt = load.experiment_list(mcp / f"experiments_{i}.expt", check_format=False)
        refl = flex.reflection_table.from_file(mcp / f"reflections_{i}.refl")
        refls.append(refl)
        expts.append(expt[0])
    expts, refls = assign_unique_identifiers(expts, refls)
    yield expts, refls


def test_clustering(proteinase_k, run_in_tmp_path):
    expts, refls = proteinase_k
    intensity_clustering = DialsCorrelationMatrix()
    intensity_clustering.run(expts, refls)

    # Check output generated
    assert (
        run_in_tmp_path / f"{intensity_clustering._xpid}_dials.correlation_matrix.log"
    ).is_file()
    assert (run_in_tmp_path / "dials.correlation_matrix.json").is_file()


def test_non_default_parameters(proteinase_k, run_in_tmp_path):
    expts, refls = proteinase_k
    intensity_clustering = DialsCorrelationMatrix()
    intensity_clustering.use_xpid = False
    intensity_clustering.set_xi(0.05)
    intensity_clustering.set_buffer(0.7)
    intensity_clustering.set_output_json("test.correlation_matrix.json")
    intensity_clustering.run(expts, refls)

    # Check output generated
    assert (run_in_tmp_path / "dials.correlation_matrix.log").is_file()
    assert (run_in_tmp_path / "test.correlation_matrix.json").is_file()
