from __future__ import annotations

from dxtbx.model import ExperimentList

from xia2.Schema import compare_geometries, load_reference_geometries


def test_load_reference_geometries(dials_data):
    """
    Test `xia2.Schema.load_reference_geometries`.

    Test the function that finds the set of unique instrument models from a list
    of experiment list files.

    There are eight input instrument models, of which only two are unique.
    """
    files = ["scaled_20_25.expt", "scaled_30.expt", "scaled_35.expt"]
    files = [(dials_data("l_cysteine_4_sweeps_scaled") / f).strpath for f in files]
    files.append((dials_data("l_cysteine_dials_output") / "indexed.expt").strpath)

    num_input = sum(len(ExperimentList.from_file(f, check_format=False)) for f in files)
    assert num_input == 8, "Expected to find eight experiments, one for each sweep."

    unique_geometries = load_reference_geometries(files)
    assert len(unique_geometries) == 2, "Expected to find two unique instrument models."

    detectors = (geom["detector"] for geom in unique_geometries)
    assert not compare_geometries(*detectors), "Unique detectors cannot be equivalent."
