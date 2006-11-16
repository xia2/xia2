#!/usr/bin/env python
# FileName.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
#
# 16th November 2006
# 

import sys
import os

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))

if not os.environ['DPA_ROOT'] in sys.path:
    sys.path.append(os.environ['DPA_ROOT'])

def _dot(a, b):
    '''Compute a.b. For converting with the aid of a SCALEN record in a
    pdb file...'''

    if not len(a) == len(b):
        raise RuntimeError, 'different length vectors'

    result = 0.0
    
    for i in range(len(a)):
        result += a[i] * b[i]

    return result

def parse_pdb_sites_file(pdb_file):
    '''Parse a pdb file full of heavy atoms and transmogrify this into
    a form suitable for input to e.g. bp3 (with fractional coordinates
    and occupancies.)'''

    data = open(pdb_file, 'r').readlines()

    scales = { }

    results = []

    for d in data:
        if 'SCALE' in d[:5]:
            scale = map(float, d.split()[1:4])
            scales[int(d.split()[0].replace('SCALE', '')) - 1] = scale

    if not scales.has_key(0):
        raise RuntimeError, 'SCALE1 record missing'

    if not scales.has_key(1):
        raise RuntimeError, 'SCALE2 record missing'

    if not scales.has_key(2):
        raise RuntimeError, 'SCALE3 record missing'

    for d in data:
        if 'ATOM' in d[:4]:
            cartesian = map(float, d.split()[5:8])
            occ = float(d.split()[8])
            atom = d.split()[2].lower()

            fractional = [_dot(scales[i], cartesian) for i in range(3)]

            results.append({'atom':atom,
                            'occupancy':occ,
                            'cartesian':cartesian,
                            'fractional':fractional})

    return results

if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise RuntimeError, '%s pdb_file' % sys.argv[0]

    print parse_pdb_sites_file(sys.argv[1])

    
