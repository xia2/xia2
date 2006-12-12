#!/usr/bin/env python
# XDSIdxrefHelpers.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
# 
# Routines which help with working with XDS IDXREF - e.g. parsing the 
# output IDXREF.LP.
# 

import math
import os
import sys

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Experts.LatticeExpert import ApplyLattice

def _parse_idxref_lp(lp_file_lines):
    '''Parse the list of lines from idxref.lp.'''

    lattice_character_info = {}

    i = 0
    while i < len(lp_file_lines):
        line = lp_file_lines[i]
        i += 1

        # get the lattice character information
        
        if 'CHARACTER  LATTICE     OF FIT      a      b      c' in line:
            j = i + 1
            while lp_file_lines[j].strip() != "":
                record = lp_file_lines[j].split()
                character = int(record[0])
                lattice = record[1]
                fit = float(record[2])
                cell = tuple(map(float, record[3:9]))
                reindex_card = tuple(map(int, record[9:]))
                constrained_cell = ApplyLattice(lattice, cell)[0]

                lattice_character_info[character] = {
                    'lattice':lattice,
                    'fit':fit,
                    'cell':constrained_cell,
                    'reidx':reindex_card}

                j += 1


    return lattice_character_info

