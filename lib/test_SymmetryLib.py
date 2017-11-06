from __future__ import absolute_import, division, print_function

def test_lauegroup_to_lattice_functions(ccp4):
  from xia2.lib.SymmetryLib import lauegroup_to_lattice
  assert lauegroup_to_lattice('I m m m') == 'oI'
  assert lauegroup_to_lattice('C 1 2/m 1') == 'mC'
  assert lauegroup_to_lattice('P -1') == 'aP'
  assert lauegroup_to_lattice('P 4/mmm') == 'tP'

def test_lattice_order(ccp4):
  from xia2.lib.SymmetryLib import lattices_in_order
  assert lattices_in_order() == ['aP',
                                 'mP', 'mC',
                                 'oP', 'oC', 'oF', 'oI',
                                 'tP', 'tI',
                                 'hP', 'hR',
                                 'cP', 'cF', 'cI',
                                ]

def test_spacegroup_conversion(ccp4):
  from xia2.lib.SymmetryLib import spacegroup_name_old_to_xHM
  assert spacegroup_name_old_to_xHM('H 3 2') == 'R 3 2 :H'

def test_hrm(ccp4):
  from xia2.lib.SymmetryLib import compute_enantiomorph, get_all_spacegroups_long

  spacegroups = get_all_spacegroups_long()
  assert len(spacegroups) == 266 # not quite 230 :)

  screw_axes = {
    '31': '32', '32': '31',
    '41': '43', '43': '41',
    '61': '65', '62': '64', '64': '62', '65': '61',
  }
  for spacegroup in spacegroups:
    enantiomorph = compute_enantiomorph(spacegroup)
    if enantiomorph != spacegroup:
      assert enantiomorph[0] == 'P' \
         and enantiomorph[2:4] in screw_axes \
         and spacegroup == enantiomorph[0:2] + screw_axes[enantiomorph[2:4]] + enantiomorph[4:]
