import sys
import math
import os
from iotbx import mtz
from cctbx.eltbx import sasaki

def guess_the_atom(hklin, nsites, mw):
    '''Guess the atom which gives rise to the observed anomalous differences
    in intensities (i.e. I(+) and I(-)).'''

    mtz_obj = mtz.object(hklin)
    mi = mtz_obj.extract_miller_indices()

    wavelengths = { }

    atoms = ['Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn', 'Se', 'Br', 'S', 'P']

    tables = [sasaki.table(atom) for atom in atoms]

    for crystal in mtz_obj.crystals():
        if crystal.name() == 'HKL_base':
            continue
        assert(len(crystal.datasets()) == 1)
        for dataset in crystal.datasets():
            wavelength = dataset.wavelength()

    mas = mtz_obj.as_miller_arrays()

    best_atom = None
    best_diff = 100.0

    for ma in mas:
        columns = ma.info().label_string()
        if 'I(+)' in columns and 'I(-)' in columns:
            signal = ma.anomalous_signal()
            for j, atom in enumerate(atoms):
                fdp = tables[j].at_angstrom(wavelength).fdp()
                p_signal = fdp * math.sqrt(nsites / mw)
                if math.fabs(p_signal - signal) < best_diff:
                    best_diff = math.fabs(p_signal - signal)
                    best_atom = atom

    return best_atom
                    
if __name__ == '__main__':

    if len(sys.argv) != 4:
        raise RuntimeError, '%s hklin nsites molecular_weight' % sys.argv[0]

    print guess_the_atom(sys.argv[1], int(sys.argv[2]), float(sys.argv[3]))
