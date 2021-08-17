def test_lauegroup_to_lattice_functions(ccp4):
    from xia2.lib.SymmetryLib import lauegroup_to_lattice

    assert lauegroup_to_lattice("I m m m") == "oI"
    assert lauegroup_to_lattice("C 1 2/m 1") == "mC"
    assert lauegroup_to_lattice("P -1") == "aP"
    assert lauegroup_to_lattice("P 4/mmm") == "tP"


def test_lattice_order(ccp4):
    from xia2.lib.SymmetryLib import lattices_in_order

    assert lattices_in_order() == [
        "aP",
        "mP",
        "mC",
        "oP",
        "oC",
        "oF",
        "oI",
        "tP",
        "tI",
        "hP",
        "hR",
        "cP",
        "cF",
        "cI",
    ]
