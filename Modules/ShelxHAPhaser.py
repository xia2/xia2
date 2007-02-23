#!/isr/bin/env python
# ShelxHAPhaser.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 20th February 2007
# 
# A HAPhaser implementation using the shelx suite of tools - in particular
# shelxc for data preparation, shelxd for substructure determination and 
# shelxe for phase calculation and some density modification.
# 
# This makes use of peer-to-peer communication among parallel substructure
# determination jobs to determine the correct spacegroup.
# 

import sys
import os

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])


from Wrappers.Shelx.Shelxc import Shelxc
from Wrappers.Shelx.Shelxd import Shelxd
from Wrappers.Shelx.Shelxe import Shelxe

# the code which follows illustrates a way that this could be implemented

data_dir = os.path.join(os.environ['X2TD_ROOT'],
                        'Test', 'UnitTest', 'Interfaces',
                        'Scaler', 'Unmerged')

# spacegroups = ['P222', 'P2221', 'P21212', 'P212121',
#                'P2122', 'P2212', 'P21221', 'P22121']

spacegroups = ['P222', 'P212121']

shelxd_list = []

# only prepare the data once

shelxc = Shelxc()
shelxc.write_log_file('shelxc.log')
shelxc.set_cell((57.74, 76.93, 86.57, 90.00, 90.00, 90.00))
shelxc.set_symmetry(spacegroups[0])
shelxc.set_n_sites(5)
shelxc.set_infl(os.path.join(data_dir, 'TS00_13185_unmerged_INFL.sca'))
shelxc.set_lrem(os.path.join(data_dir, 'TS00_13185_unmerged_LREM.sca'))
shelxc.set_peak(os.path.join(data_dir, 'TS00_13185_unmerged_PEAK.sca'))
shelxc.set_name('peer')
shelxc.prepare()

# then run through to work out the correct spacegroup by
# finding sites in all spacegroups

for s in spacegroups:
    shelxd = Shelxd()
    shelxd.write_log_file('shelxd_%s.log' % s)
    shelxd.set_name('peer')
    shelxd.set_spacegroup(s)
    shelxd_list.append(shelxd)

# this will get the right one from the list!
shelxd_list.sort()
shelxd = shelxd_list[-1]
spacegroup = shelxd.get_spacegroup()

print 'Correct spacegroup from list %s is %s' % \
      (spacegroups, spacegroup)

# write the correct solutions out
open('peer_fa.res', 'w').write(shelxd.get_res())

# do some phasing - this should decide the correct
# enantiomorph of the substructure by magic

se = Shelxe()
se.write_log_file('shelxe.log')
se.set_name('peer')
se.set_solvent(0.49)
se.phase()

se = Shelxe()
se.write_log_file('shelxe_oh.log')
se.set_name('peer')
se.set_solvent(0.49)
se.set_enantiomorph()
se.phase()

from Wrappers.CCP4.F2mtz import F2mtz

f = F2mtz()

f.set_hklin('peer.phs')
f.set_hklout('peer.mtz')
f.set_cell((57.74, 76.93, 86.57, 90.00, 90.00, 90.00))
f.set_symmetry(spacegroup)
f.f2mtz()

f = F2mtz()

f.set_hklin('peer_i.phs')
f.set_hklout('peer_oh.mtz')
f.set_cell((57.74, 76.93, 86.57, 90.00, 90.00, 90.00))
f.set_symmetry(spacegroup)
f.f2mtz()


    
