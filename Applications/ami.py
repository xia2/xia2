#!/usr/bin/env python
# ami.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 18th June 2007
#
# Top-level interface for AMI - Analyse My Intensities
#

import sys
import os
import time
import exceptions
import traceback

sys.path.append(os.environ['XIA2_ROOT'])

from Handlers.Streams import Chatter
from Handlers.Files import cleanup
from Handlers.Citations import Citations

from Modules.AnalyseMyIntensities import AnalyseMyIntensities

from XIA2Version import Version

def ami():
    '''Perform the analysis via AnalyseMyIntensities.'''

    # print a banner

    Chatter.write(
        '###############################################################')
    Chatter.write(
        '###############################################################')
    Chatter.write(
        '###############################################################')
    Chatter.write(
        '### CCP4 6.0: AMI       version %7s                ###' \
        % Version)
    Chatter.write(
        '###############################################################')
    Chatter.write('Run time / date: %s' % time.asctime())

    arguments = sys.argv

    hklin_list = []
    hklout = None

    for j in range(len(arguments)):

        if 'hklin' in arguments[j].lower():
            counter = int(arguments[j].lower().replace('hklin', ''))
            if counter != (len(hklin_list) + 1):
                raise RuntimeError, 'hklin out of sequence'
            hklin_list.append(arguments[j + 1])

        if arguments[j].lower() == 'hklout':
            hklout = arguments[j + 1]

    # next parse the command line input

    cell = None
    symm = None
    dren = { }
    solv = None
    nmol = None
    nres = None
    rein = None
    anom = None
    rotf = None
    verb = False

    while True:
        try:
            a = raw_input()
        except EOFError, e:
            break

        if not a.strip():
            continue

        if a[0] == '#' or a[0] == '!':
            continue

        if a.lower() == 'end':
            break

        command = a.split()[0][:4].lower()

        if command == 'cell':
            cell = tuple(map(float, a.split()[1:7]))

        elif command == 'symm':
            symm = ''
            for token in a.split()[1:]:
                symm += token

        elif command == 'dren':
            tokens = a.split()
            dren[int(tokens[2]) - 1] = tokens[4], tokens[6], tokens[8]

        elif command == 'solv':
            solv = float(a.split()[1])

        elif command == 'nmol':
            nmol = int(a.split()[1])

        elif command == 'nres':
            nres = int(a.split()[1])

        elif command == 'anom':
            value = a.split()[1].lower()

            if value in ['true', 'on', 'y']:
                anom = True
            elif value in ['false', 'off', 'n']:
                anom = False
            else:
                raise RuntimeError, 'value %s unknown for anomalous: ' % \
                      a.split()[1]

        elif command == 'rotf':
            value = a.split()[1].lower()

            if value in ['true', 'on', 'y']:
                rotf = True
            elif value in ['false', 'off', 'n']:
                rotf = False
            else:
                raise RuntimeError, \
                      'value %s unknown for self rotation search: ' % \
                      a.split()[1]

        elif command == 'verb':
            value = a.split()[1].lower()

            if value in ['true', 'on', 'y']:
                verb = True
            elif value in ['false', 'off', 'n']:
                verb = False
            else:
                raise RuntimeError, 'value %s unknown for verbose: ' % \
                      a.split()[1]

        elif command == 'rein':
            rein = a.split()[1]

    # so let's set ourselves up!

    _ami = AnalyseMyIntensities()

    for j in range(len(hklin_list)):
        _ami.add_hklin(hklin_list[j], dren.get(j, None))

    _ami.set_hklout(hklout)

    if not anom is None:
        _ami.set_anomalous(anom)

    if not rotf is None:
        _ami.set_rotation_function(rotf)

    if not cell is None:
        _ami.set_cell(cell)

    if not symm is None:
        _ami.set_symmetry(symm)

    if not nmol is None:
        _ami.set_nmol(nmol)

    if not nres is None:
        _ami.set_nres(nres)

    if not solv is None:
        _ami.set_solvent(solv)

    if not rein is None:
        _ami.set_reindex(rein)

    _ami.convert_to_mtz()
    _ami.analyse_input_hklin()
    _ami.merge_analyse()
    solvent = _ami._get_solvent()

    Chatter.write('Solvent fraction estimated as %s' % solvent)

    _ami.write_log_file('ami.log')

    if verb:
        for line in _ami.get_log_file():
            Chatter.write(line[:-1])

    return

if __name__ == '__main__':
    ami()
