#!/usr/bin/env python
# xia2pdb_lattice.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
# 
# A program to analyse PDB CRYST1 records to "mine" information on the
# spectrum of distortions. This will output the "correct" unit cell
# from the structure, the spectrum of similar lattices & distortions.
# The higher lattices than the correct one will be scored by distortion
# penalty, counting the sneaky high symmetry looking ones as we go.
# 
# This is likely to be messy.
# 

import sys
import os

if not os.environ.has_key('DPA_ROOT'):
    raise RuntimeError, 'DPA_ROOT not defined'
if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['DPA_ROOT']))

from Wrappers.CCP4.Othercell import Othercell
from Handlers.Syminfo import Syminfo

def get_cryst1(pdb_file_name):
    for line in open(pdb_file_name, 'r').readlines():
        if line[:6] == 'CRYST1':
            return line

    raise RuntimeError, 'no CRYST1 record found'

def parse_cryst1(cryst1_line):
    record = cryst1_line.split()
    cell = map(float, record[1:7])
    symm = ''
    for c in record[7: -1]:
        symm += '%s ' % c

    return cell, symm.strip()

def parse_pdb(pdb_file_name):
    pdb_entry = open(pdb_file_name, 'r').readline().split()[-1]
    cell, symm = parse_cryst1(get_cryst1(pdb_file_name))

    return pdb_entry, cell, symm

def print_lattice(lattice):
    print 'Cell: %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % lattice['cell']
    print 'Number: %s     Lattice: %s' % (lattice['number'], 
                                          lattice['lattice'])
    print 'Distortions (PRE, GW):   %5.2f %5.2f' % (lattice['delta'],
                                                    lattice['distortion'])

def do_funky(pdb_file_name):
    pdb, cell, symm = parse_pdb(pdb_file_name)

    if cell[0] * cell[1] * cell[2] < 100.0:
        # this is an unlikely unit cell...
        return

    print '----------- Analysing %s ----------' % pdb

    # check that the symmetry is legal, not something whacky! 
    try:
        original_lattice = Syminfo.get_lattice(symm)
        original = lattice_to_spacegroup[original_lattice]
    except:
        print 'Symmetry not understood: %s' % symm
        print '-------------------------------------'
        return

    o = Othercell()

    o.set_cell(cell)
    o.set_lattice(symm[0].lower())
    o.generate()

    lattices = o.get_possible_lattices()

    # next need to work through some calculations
    # this really needs to go info Syminfo handler

    lattice_to_spacegroup = {'aP':1,  'mP':3, 'mC':5, 'oP':16,
                             'oC':20, 'oF':22, 'oI':23, 'tP':75,
                             'tI':79, 'hP':143, 'hR':143,
                             'cP':195, 'cF':196,  'cI':197}

    for lattice in lattices.keys():
        if lattices[lattice]['number'] > original:
            print '-- Higher --'
            print_lattice(lattices[lattice])
        elif lattices[lattice]['number'] == original:
            print '-- Original --'
	    print 'Cell: %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % tuple(cell)
    	    print 'Number: %s     Lattice: %s' % (original, 
                                                  original_lattice)
            print 'Distortions (PRE, GW):   %5.2f %5.2f' % (0.0, 0.0)

    print '-------------------------------------'

    sys.stdout.flush()

    return

for file in os.listdir('.'):
    if file.split('.')[-1] == 'pdb':
        do_funky(file)

