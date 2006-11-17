#!/usr/bin/env python
# SubstructureLib.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
#
# 16th November 2006
#
# A library of things pertaining to substructure manipulation:
# 
# .pdb file -> fractional coordinates
# invert hand

import sys
import os
import copy

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))

if not os.environ['DPA_ROOT'] in sys.path:
    sys.path.append(os.environ['DPA_ROOT'])

from SymmetryLib import spacegroup_name_short_to_long

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

    sites = []
    cell = ()
    symm = ''

    for d in data:
        if 'SCALE' in d[:5]:
            scale = map(float, d.split()[1:4])
            scales[int(d.split()[0].replace('SCALE', '')) - 1] = scale

        # need to store this to handle the inversion...
        
        if 'CRYST1' in d[:6]:
            cell = tuple(map(float, d.split()[1:7]))

            # need to ensure that this has a standard format name - so
            # zap the spaces then look it up in the CCP4 symop.lib.
            symm = spacegroup_name_short_to_long(
                d[55:].strip().replace(' ', ''))

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

            fractional = tuple([_dot(scales[i], cartesian) for i in range(3)])

            # no longer record cartesian coordinates
            # 'cartesian':cartesian,

            sites.append({'atom':atom,
                          'occupancy':occ,
                          'fractional':fractional})

    results = { }
    results['sites'] = sites
    results['cell'] = cell
    results['spacegroup'] = symm
    results['scale'] = scales
    
    return results

def invert_hand(sites_info):
    '''Invert the hand (and perhaps the spacegroup) of substructure sites.'''

    new_sites_info = copy.deepcopy(sites_info)

    new_sites = []
    old_sites = sites_info['sites']

    # check first for special cases...

    if sites['spacegroup'] == 'I 41':
        for site in old_sites:
            fractional = site['fractional']
            new_fractional = (1 - fractional[0],
                              0.5 - fractional[1],
                              1 - fractional[2])
            new_sites.append({'atom':site['atom'],
                              'occupancy':site['occupancy'],
                              'fractional':new_fractional})
        
    elif sites['spacegroup'] == 'I 41 2 2':
        for site in old_sites:
            fractional = site['fractional']
            new_fractional = (1 - fractional[0],
                              0.5 - fractional[1],
                              0.25 - fractional[2])
            new_sites.append({'atom':site['atom'],
                              'occupancy':site['occupancy'],
                              'fractional':new_fractional})
        
    elif sites['spacegroup'] == 'F 41 3 2':
        for site in old_sites:
            fractional = site['fractional']
            new_fractional = (0.25 - fractional[0],
                              0.25 - fractional[1],
                              0.25 - fractional[2])
            new_sites.append({'atom':site['atom'],
                              'occupancy':site['occupancy'],
                              'fractional':new_fractional})
        
    else:
        # we have the general case
        for site in old_sites:
            fractional = site['fractional']
            new_fractional = (1.0 - fractional[0],
                              1.0 - fractional[1],
                              1.0 - fractional[2])
            new_sites.append({'atom':site['atom'],
                              'occupancy':site['occupancy'],
                              'fractional':new_fractional})

        # perhaps invert the spacegroup to it's enantiomorph
        

    new_sites_info['sites'] = new_sites


if __name__ == '__main__':
    if len(sys.argv) < 2:
        pdb = os.path.join(os.environ['SS_ROOT'],
                           'Data', 'Test', 'Sites', 'hyss-sites.pdb')
    else:
        pdb = sys.argv[1]

    print parse_pdb_sites_file(pdb)

    
