#!/usr/bin/env python
# xia2invert_hand.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
#
# 16th November 2006
#
# A tiny application to invert the hand of a pdb file.
# 

import sys
import os

if not os.environ['SS_ROOT'] in sys.path:
    sys.path.append(os.environ['SS_ROOT'])

from lib import SubstructureLib

def run():
    if len(sys.argv) < 2:
        raise RuntimeError, '%s pdb.in [pdb.out]'

    sites = SubstructureLib.parse_pdb_sites_file(sys.argv[1])

    if len(sys.argv) == 3:
        out = open(sys.argv[2], 'w')
        SubstructureLib.write_pdb_sites_file(
            SubstructureLib.invert_hand(sites), out)
        out.close()
    else:
        SubstructureLib.write_pdb_sites_file(
            SubstructureLib.invert_hand(sites))

if __name__ == '__main__':
    run()

 

