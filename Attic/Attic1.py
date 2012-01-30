# Attic1 - code removed as useless from Experts/SymmetryExpert.py

def reduce(symops, v):
    '''Reduce the vector v to the minimal standard i.e. the symmetry
    related one with x < y < z ideally. x, y, z are fractional
    coordinates.'''

    from MatrixExpert import matvecmul

    reduced = v

    for s in symops:
        v2 = matvecmul(s, v)

        v2[0] = modulo(1.0, v2[0])
        v2[1] = modulo(1.0, v2[1])
        v2[2] = modulo(1.0, v2[2])

        if v2[0] > reduced[0]:
            continue
        if v2[0] < reduced[0]:
            reduced = v2
            continue
        if v2[1] > reduced[1]:
            continue
        if v2[1] < reduced[1]:
            reduced = v2
            continue
        if v2[2] > reduced[2]:
            continue
        if v2[2] < reduced[2]:
            reduced = v2
            continue

    return reduced
