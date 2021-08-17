import pytest

import xia2.Experts.LatticeExpert


def test_lattice_expert():
    cell, dist = xia2.Experts.LatticeExpert.ApplyLattice(
        "oP", (23.0, 24.0, 25.0, 88.9, 90.0, 90.1)
    )
    assert cell == (23.0, 24.0, 25.0, 90.0, 90.0, 90.0)
    assert dist == pytest.approx(1.2)


def test_SortLattices():
    lattices_cells = [
        ("aP", (57.70, 57.70, 149.80, 90.00, 90.00, 90.00)),
        ("tP", (57.70, 57.70, 149.80, 90.00, 90.00, 90.00)),
        ("mC", (81.60, 81.60, 149.80, 90.00, 90.00, 90.00)),
        ("mP", (57.70, 57.70, 149.80, 90.00, 90.00, 90.00)),
        ("oC", (81.60, 81.60, 149.80, 90.00, 90.00, 90.00)),
        ("oP", (57.70, 57.70, 149.80, 90.00, 90.00, 90.00)),
    ]

    result = xia2.Experts.LatticeExpert.SortLattices(lattices_cells)

    r0 = [r[0] for r in result]

    assert r0 == ["tP", "oC", "oP", "mC", "mP", "aP"]
