"""
Regression tests for multiple-sweep behaviour.

Test the behaviour of the `multiple_sweep_indexing`, `multiple_sweep_refinement` and
`small_molecule` settings.  Run xia2 with
 * `multiple_sweep_indexing=True`, others above set to default values.
 * `multiple_sweep_refinement=True`, others above set to default values.
 * `small_molecule=True`, others above set to default values.
"""

from __future__ import annotations

import os
import subprocess

import pytest


@pytest.mark.parametrize(
    "multi_sweep_type",
    ("multi_sweep_indexing", "multi_sweep_refinement", "small_molecule"),
)
def test_multiple_sweeps(multi_sweep_type, ccp4, dials_data, tmp_path):
    """
    Run xia2 with various different multiple-sweep options.

    Run xia2 using subprocess.run() and look for errors or timeouts.  Run it with a reduced
    number of reflections per degree required for profile modelling and turn off the
    Xtriage analysis, since we won't have enough reflections for the default settings
    of either to be successful.

    Args:
        multi_sweep_type: Parameter governing multiple-sweep behaviour to be set True.
        dials_data: dials-data pytest fixture for access to test data.
        tmp_path: pytest fixture to provide a temporary working directory
    """
    # Use as input the first fifteen images of the first two sweeps of a typical
    # multiple-sweep data set.
    data_dir = dials_data("l_cysteine_dials_output", pathlib=True)
    images = [data_dir / f"l-cyst_{sweep:02d}_00001.cbf:1:15" for sweep in (1, 2)]

    cmd = "xia2"
    if os.name == "nt":
        cmd += ".bat"
    command = [
        # Obviously, we're going to run xia2.
        cmd,
        # Set one of the multiple-sweep flags.
        f"{multi_sweep_type}=True",
        # Reduce the required number of reflections per degree for profile modelling
        # because we don't have enough in these data.
        "min_spots.per_degree=10",
        # Don't run the Xtriage analysis — we don't have enough reflections overall.
        "xtriage_analysis=False",
    ]
    result = subprocess.run(
        command + [f"image={str(image)}" for image in images],
        capture_output=True,
        cwd=tmp_path,
    )

    assert not result.returncode
