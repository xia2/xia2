import sys
import os

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'
if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

from Wrappers.Phenix.LatticeSymmetry import LatticeSymmetry
from lib.SymmetryLib import lattice_to_spacegroup

def lattice_symmetry(cell):
    ls = LatticeSymmetry()

    ls.set_cell(cell)
    ls.set_spacegroup('P1')

    ls.generate()

    result = { }

    lattices = ls.get_lattices()

    for lattice in lattices:
        result[lattice] = {'cell':ls.get_cell(lattice),
                           'penalty':ls.get_distortion(lattice)}
    
    return result

if __name__ == '__main__':

    result = lattice_symmetry((44.13, 52.63, 116.86, 77.14, 79.74, 89.85))

    lattices = result.keys()
    lattices.reverse()

    for l in lattices:
        print '%s %.2f' % (l, result[l]['penalty'])

