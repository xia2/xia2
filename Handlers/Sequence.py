#!/usr/bin/env python
# Sequence.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Handlers and calculations based on sequences for macromolecular structures.
#

import string

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

def to_short_form(residue_list):
    '''Convert a list of residues e.g. ALA GLY to AG or one residue
    if there is only one (e.g. not a list)'''
    if type(residue_list) == type([]):
        short_form = ''

        for r in residue_list:
            short_form += residue_letters[r.upper()]

        return short_form
    else:
        return residue_letters[residue_list.upper()]

class Sequence:
    '''A class to represent a sequence'''

    def __init__(self, file = None, seq = None):

        if seq and file:
            raise RuntimeError, 'cannot specify file and sequence'

        if file:
            lines = open(file, 'r').readlines()

            if lines[0].split()[0] == 'HEADER':
                self.fromPDB(file)
                return

            if lines[0][0] == '>':

                self.sequence = ''

                for l in lines[2:]:
                    self.sequence += l

            else:
                self.sequence = ''

                for l in lines:
                    self.sequence += l.strip()

            sequence = self.sequence.upper()

            self.sequence = ''

            for s in sequence:
                if s in string.ascii_uppercase:
                    self.sequence += s

        elif seq:

            self.sequence = seq.upper()

        return

    def len(self):
        return len(self.sequence)

    def seq(self):
        return self.sequence

    def pir(self):
        return '>dummy\n\n%s' % self.sequence

    def fromPDB(self, pdb_file):
        '''Read the Sequence from a PDB file'''

        long_sequence = []
        modifications = { }
        for l in open(pdb_file, 'r').readlines():
            list = l.split()
            if list[0] == 'SEQRES':
                # the residues are in records 22-70 (from reference
                # http://bioinformatics.ljcrf.edu/liwz/reference/
                # pdb/part_35.html
                # so
                list = l[18:72].split()
                for res in list:
                    long_sequence.append(res)
            if list[0] == 'MODRES':
                modifications[list[2]] = list[5]

        sequence = []
        for l in long_sequence:
            if modifications.has_key(l):
                sequence.append(modifications[l])
            else:
                sequence.append(l)

        self.sequence = to_short_form(sequence)

    def weight(self):
        total = 0.0
        for s in self.sequence.lower():
            if s == 'a':
                total += 89
            elif s == 'c':
                total += 121
            elif s == 'd':
                total += 133
            elif s == 'e':
                total += 147
            elif s == 'f':
                total += 165
            elif s == 'g':
                total == 75
            elif s == 'h':
                total += 155
            elif s == 'i':
                total += 131
            elif s == 'k':
                total += 146
            elif s == 'l':
                total += 131
            elif s == 'm':
                total += 149
            elif s == 'n':
                total += 132
            elif s == 'p':
                total += 115
            elif s == 'q':
                total += 146
            elif s == 'r':
                total += 174
            elif s == 's':
                total += 105
            elif s == 't':
                total += 119
            elif s == 'v':
                total += 117
            elif s == 'w':
                total += 204
            elif s == 'y':
                total += 181

        return total

if __name__ == '__main__':

    sequence = \
             '''MHKMWPSDSNDHRVTRRNVIIFSSLLLGSLAILLALLLIRTKDQYYELRDFALGTSVRIV
             VSSQKINPRTIAEAILEDMKRITYKFSFTDERSVVKKINDHPNEWVEVDEETYSLIKAAC
             AFAELTDGAFDPTVGRLLELWGFTGNYENLRVPSREEIEEALKHTGYKNVLFDDKNMRVM
             VKNGVKIDLGGIAKGYALDRARQIALSFDENATGFVEAGGDVRIIGPKFGKYPWVIGVKD
             PRGDDVIDYIYLKSGAVATSGDYERYFVVDGVRYHHILDPSTGYPARGVWSVTIIAEDAT
             TADALSTAGFVMAGKDWRKVVLDFPNMGAHLLIVLEGGAIERSETFKLFERE'''

    s = Sequence(seq = sequence)
    print s.weight()
