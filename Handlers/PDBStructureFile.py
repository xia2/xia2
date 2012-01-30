#!/usr/bin/env python
# PDBStructureFile.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# A handler for PDB files for macromolecular structures. This is to
# enable analysis programs.
#

import os

residue_letters = { }

residue_letters['ALA'] = 'A'
residue_letters['ARG'] = 'R'
residue_letters['ASN'] = 'N'
residue_letters['ASP'] = 'D'
residue_letters['CYS'] = 'C'
residue_letters['GLN'] = 'Q'
residue_letters['GLU'] = 'E'
residue_letters['GLY'] = 'G'
residue_letters['HIS'] = 'H'
residue_letters['ILE'] = 'I'
residue_letters['LEU'] = 'L'
residue_letters['LYS'] = 'K'
residue_letters['MET'] = 'M'
residue_letters['PHE'] = 'F'
residue_letters['PRO'] = 'P'
residue_letters['SER'] = 'S'
residue_letters['THR'] = 'T'
residue_letters['TRP'] = 'W'
residue_letters['TYR'] = 'Y'
residue_letters['VAL'] = 'V'

def parse_pdb_remark_200(pdb_file_records):
    '''Look for REMARK 200 data and transform into a dictionary.'''

    j = 0

    results = []

    while j < len(pdb_file_records):
        record = pdb_file_records[j]
        if not 'REMARK 200' in record:
            j += 1
            continue

        if ':' in record:
            pair = record.replace('REMARK 200', '').strip(
                ).split(':')
            results.append((pair[0].strip(), pair[1].strip()))

        j += 1

    return results

found = []

def compute(pdb_file):
    '''Compute some interesting stuff from the pdb file.'''
    data = open(pdb_file).readlines()
    remarks = parse_pdb_remark_200(data)

    dmin = 0.0
    multiplicity = 0.0
    completeness = 0.0
    r_merge = 0.0
    i_sigma = 0.0

    for remark in remarks:
        if 'HIGHEST RESOLUTION SHELL, RANGE HIGH (A)' in \
           remark[0] and not 'NULL' in remark[1]:
            dmin = float(remark[1])
        if 'COMPLETENESS FOR SHELL     (%)' in \
           remark[0] and not 'NULL' in remark[1]:
            completeness = float(remark[1])
        if 'DATA REDUNDANCY IN SHELL' in \
           remark[0] and not 'NULL' in remark[1]:
            multiplicity = float(remark[1])
        if '<I/SIGMA(I)> FOR SHELL' in \
           remark[0] and not 'NULL' in remark[1]:
            i_sigma = float(remark[1])
        if 'R MERGE FOR SHELL' in \
           remark[0] and not 'NULL' in remark[1]:
            r_merge = float(remark[1])
        if 'R SYM FOR SHELL' in \
           remark[0] and not 'NULL' in remark[1]:
            r_merge = float(remark[1])

    if dmin > 0.0 and completeness > 0.0 and multiplicity > 0.0 \
           and i_sigma > 0.0 and r_merge > 0.0 and i_sigma < 200:
        pdb = os.path.split(pdb_file)[-1][:4]
        datum = (dmin, completeness, multiplicity,
                 i_sigma, r_merge)
        if not datum in found:
            found.append(datum)

        # print '%4s %4.2f %5.1f %4.1f %5.1f %6.4f' % \
        # (pdb, dmin, completeness, multiplicity,
        # i_sigma, r_merge)

def analyse():
    '''Analyse all of the data already collected.'''

    for f in found:
        dmin, completeness, multiplicity, i_sigma, r_merge = f

        predicted_r = 0.7979 / i_sigma
        print '%4.2f %5.1f %4.1f %5.1f %6.4f %6.4f %4.2f' % \
              (dmin, completeness, multiplicity,
               i_sigma, r_merge, predicted_r, r_merge /
               predicted_r)

def read_modifications(pdb_file):

    modifications = { }

    for record in open(pdb_file):
        if not 'MODRES' in record[:6]:
            continue

        modifications[record.split()[2]] = record.split()[5]

    return modifications

def read_sequence(pdb_file):
    '''Read the sequence from the SEQRES records and return as a dictionary.'''

    sequences = { }
    chains = []
    lengths = { }

    modifications = read_modifications(pdb_file)

    for record in open(pdb_file):
        if not 'SEQRES' in record[:6]:
            continue

        chain = record.split()[2]
        residues = record.split()[4:]

        if not chain in chains:
            chains.append(chain)

        if not chain in sequences:
            sequences[chain] = ''

        for r in residues:
            if r in modifications:
                r = modifications[r]
            sequences[chain] += residue_letters[r]

        if not chain in lengths:
            lengths[chain] = int(record.split()[3])

    for chain in chains:
        assert(len(sequences[chain]) == lengths[chain])

    return sequences

if __name__ == '__main__' and False:

    import sys

    if len(sys.argv) < 2:
        raise RuntimeError, '%s pdb_file ...' % sys.argv[0]

    for arg in sys.argv[1:]:
        compute(arg)

    analyse()

if __name__ == '__main__':

    import sys

    if len(sys.argv) < 2:
        raise RuntimeError, '%s pdb_file ...' % sys.argv[0]

    for arg in sys.argv[1:]:
        sequences = read_sequence(arg)
        for k in sorted(sequences):
            sequence = sequences[k]
            print k
            print sequence
