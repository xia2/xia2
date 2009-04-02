import sys
import os

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'
if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

from Wrappers.Phenix.LatticeSymmetry import LatticeSymmetry
from lib.SymmetryLib import lattice_to_spacegroup

def sort_lattices(lattices):
    lattice_to_spacegroup = {'aP':1, 'mP':3, 'mC':5, 
                             'oP':16, 'oC':20, 'oF':22,
                             'oI':23, 'tP':75, 'tI':79,
                             'hP':143, 'hR':146, 'cP':195,
                             'cF':196, 'cI':197}

    spacegroup_to_lattice = { }
    for k in lattice_to_spacegroup.keys():
        spacegroup_to_lattice[lattice_to_spacegroup[k]] = k
    
    spacegroups = [lattice_to_spacegroup[l] for l in lattices]

    spacegroups.sort()
    return [spacegroup_to_lattice[s] for s in spacegroups]
    
def lattice_spacegroup(lattice):
    lattice_to_spacegroup = {'aP':1, 'mP':3, 'mC':5, 
                             'oP':16, 'oC':20, 'oF':22,
                             'oI':23, 'tP':75, 'tI':79,
                             'hP':143, 'hR':146, 'cP':195,
                             'cF':196, 'cI':197}
    
    return lattice_to_spacegroup[lattice]
    
def lattice_symmetry(cell):
    ls = LatticeSymmetry()

    ls.set_cell(cell)
    ls.set_spacegroup('P1')

    ls.generate()

    result = { }

    lattices = sort_lattices(ls.get_lattices())

    for lattice in lattices:
        result[lattice] = {'cell':ls.get_cell(lattice),
                           'penalty':ls.get_distortion(lattice)}
    
    return result

def constrain_lattice(lattice_class, cell):
    '''Constrain cell to fit lattice class x.'''

    a, b, c, alpha, beta, gamma = cell

    if lattice_class == 'a':
        return (a, b, c, alpha, beta, gamma)
    elif lattice_class == 'm':
        return (a, b, c, 90.0, beta, 90.0)
    elif lattice_class == 'o':
        return (a, b, c, 90.0, 90.0, 90.0)
    elif lattice_class == 't':
        e = (a + b) / 2.0
        return (e, e, c, 90.0, 90.0, 90.0)
    elif lattice_class == 'h':
        e = (a + b) / 2.0
        return (e, e, c, 90.0, 90.0, 120.0)
    elif lattice_class == 'c':
        e = (a + b + c) / 3.0
        return (e, e, e, 90.0, 90.0, 90.0)

if __name__ == '__main__':

    if len(sys.argv) < 7:
        cell = (44.13, 52.63, 116.86, 77.14, 79.74, 89.85)
    else:
        cell = tuple(map(float, sys.argv[1:7]))

    result = lattice_symmetry(cell)

    lattices = sort_lattices(result.keys())
    lattices.reverse()

    for l in lattices:
        print '%s %.2f' % (l, result[l]['penalty'])

