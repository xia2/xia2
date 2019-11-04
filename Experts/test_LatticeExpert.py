from __future__ import absolute_import, division, print_function

import pytest

import xia2.Experts.LatticeExpert


def test_lattice_expert():
    cell, dist = xia2.Experts.LatticeExpert.ApplyLattice(
        "oP", (23.0, 24.0, 25.0, 88.9, 90.0, 90.1)
    )
    assert cell == (23.0, 24.0, 25.0, 90.0, 90.0, 90.0)
    assert dist == pytest.approx(1.2)
