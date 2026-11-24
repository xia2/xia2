from __future__ import annotations

import pytest

import xia2.lib.NMolLib


def test_compute_nmol():
    nmol = xia2.lib.NMolLib.compute_nmol(
        96.0, 96.0, 36.75, 90.0, 90.0, 90.0, "P 43 21 2", 1.8, 82
    )

    assert nmol == 2, "error in nmol per asu"


def test_compute_solvent():
    solvent = xia2.lib.NMolLib.compute_solvent(
        96.0, 96.0, 36.75, 90.0, 90.0, 90.0, "P 43 21 2", 2, 82
    )

    # matthews_coef gives 46.43%
    assert solvent == pytest.approx(0.4643, abs=1e-4), "error in solvent content"
