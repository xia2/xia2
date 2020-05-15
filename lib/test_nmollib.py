import pytest

import xia2.lib.NMolLib


def test_compute_nmol():
    nmol = xia2.lib.NMolLib.compute_nmol(
        96.0, 96.0, 36.75, 90.0, 90.0, 90.0, "P 43 21 2", 1.8, 82
    )

    assert nmol == 2, "error in nmol per asu"


def test_compute_solvent(ccp4):
    solvent = xia2.lib.NMolLib.compute_solvent(
        96.0, 96.0, 36.75, 90.0, 90.0, 90.0, "P 43 21 2", 2, 82
    )

    assert solvent == pytest.approx(0.46, abs=0.1), "error in solvent content"
