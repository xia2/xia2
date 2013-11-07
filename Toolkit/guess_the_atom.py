import sys
import math
import os
from iotbx import mtz
from cctbx.eltbx import sasaki

def wavelength_energy(a):
  h = 6.6260693e-34
  c = 2.9979246e8
  e = 1.6021765e-19
  conv = 1.0e10 * h * c / e
  return conv / a

def guess_the_atom(hklin, nsites):
  '''Guess the atom which gives rise to the observed anomalous differences
  in intensities (i.e. I(+) and I(-)) though CCTBX code internally computes
  F(+) etc.'''

  mtz_obj = mtz.object(hklin)
  mi = mtz_obj.extract_miller_indices()

  sg = mtz_obj.space_group()

  for crystal in mtz_obj.crystals():
    if crystal.name() != 'HKL_base':
      uc = crystal.unit_cell()

  n_ops = len(sg.all_ops())
  v_asu = uc.volume() / n_ops
  mw = v_asu / 2.7

  atoms = ['Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn', 'Se', 'Br', 'S', 'P']

  tables = [sasaki.table(atom) for atom in atoms]

  for crystal in mtz_obj.crystals():
    if crystal.name() == 'HKL_base':
      continue
    assert(len(crystal.datasets()) == 1)
    for dataset in crystal.datasets():
      wavelength = dataset.wavelength()

  energy = wavelength_energy(wavelength)

  mas = mtz_obj.as_miller_arrays()

  best_atom = None
  best_diff = 100.0

  for ma in mas:
    columns = ma.info().label_string()
    if 'I(+)' in columns and 'I(-)' in columns:
      signal = ma.anomalous_signal()
      for j, atom in enumerate(atoms):
        for energy_offset in (-100.0, 0.0, 100.0):
          wavelength = wavelength_energy(energy + energy_offset)
          fdp = tables[j].at_angstrom(wavelength).fdp()
          p_signal = fdp * math.sqrt(nsites / mw)
          if math.fabs(p_signal - signal) < best_diff:
            best_diff = math.fabs(p_signal - signal)
            best_atom = atom

  return best_atom

if __name__ == '__main__':

  print guess_the_atom(sys.argv[1], int(sys.argv[2]))
