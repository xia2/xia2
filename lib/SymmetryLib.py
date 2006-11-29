#!/usr/bin/env python
# Symmetry.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
#
# 16th November 2006
# 
# A library of things to help with simple symmetry operation stuff.
# 
# FIXME 17/NOV/06 add a method in here to give a list of likely, and then
#                 less likely, spacegroups based on an input spacegroup.
#                 For instance, if the input spacegroup is P 41 21 2 then
#                 another likely spacegroup is P 43 21 2 and less likely
#                 spacegroups are all those in the same pointgroup with
#                 different screw axes - e.g. P 41 2 2 (thinking of an Ed
#                 Mitchell example.) This should also allow in the likely
#                 case for body centred spacegroups where the screw axes
#                 are hidden, for example I 2 2 2/I 21 21 21 and I 2 3/I 21 3.
# 

import os
import sys

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT undefined'

symop = os.path.join(os.environ['XIA2_ROOT'],
                     'Data', 'Symmetry', 'symop.lib')

def get_all_spacegroups_short():
    '''Get a list of all short spacegroup names.'''

    result = []
    
    for record in open(symop, 'r').readlines():
        if record[0] != ' ':
            shortname = record.split()[3]
            result.append(shortname)

    return result

def get_all_spacegroups_long():
    '''Get a list of all long spacegroup names.'''

    result = []
    
    for record in open(symop, 'r').readlines():
        if record[0] != ' ':
            longname = record.split('\'')[1]
            result.append(longname)

    return result
    
def spacegroup_name_short_to_long(name):
    '''Get the full spacegroup name from the short version.'''
    for record in open(symop, 'r').readlines():
        if record[0] != ' ':
            shortname = record.split()[3]
            longname = record.split('\'')[1]
            if shortname.lower() == name.lower():
                return longname

    # uh oh this doesn't exist!

def is_own_enantiomorph(spacegroup):
    '''Check if this spacegroup is its own enantiomorph - i.e. its inverse
    hand is itself.'''

    enantiomorph = compute_enantiomorph(spacegroup)

    if enantiomorph == spacegroup:
        return True

    return False

def compute_enantiomorph(spacegroup):
    '''Compute the spacegroup enantiomorph name. There are 11 pairs where
    this is needed.'''

    # should check that this is the long name form here

    elements = spacegroup.split()

    if elements[0] == 'P' and elements[1] == '41':
        new = '43'
    elif elements[0] == 'P' and elements[1] == '43':
        new = '41'

    elif elements[0] == 'P' and elements[1] == '31':
        new = '32'
    elif elements[0] == 'P' and elements[1] == '32':
        new = '31'
        
    elif elements[0] == 'P' and elements[1] == '61':
        new = '65'
    elif elements[0] == 'P' and elements[1] == '65':
        new = '61'

    elif elements[0] == 'P' and elements[1] == '62':
        new = '64'
    elif elements[0] == 'P' and elements[1] == '64':
        new = '62'

    else:
        new = elements[1]

    # construct the new spacegroup

    result = '%s %s' % (elements[0], new)
    for element in elements[2:]:
        result += ' %s' % element

    # check that this is a legal spacegroup

    return result

def lauegroup_to_lattice(lauegroup):
    '''Convert a Laue group representation (from pointless, e.g. I m m m)
    to something useful, like the implied crystal lattice (in this
    case, oI.)'''

    # parse syminfo, symop -> generate mapping table

    current_spacegroup = 0
    lauegroup_info = {0:{ }}

    for record in open(os.path.join(os.environ['CCP4'], 'lib', 'data',
                                    'syminfo.lib'), 'r').readlines():

        if record[0] == '#':
            continue

        if 'begin_spacegroup' in record:
            current_spacegroup = 0

        if 'number' in record[:6]:
            # this will ensure that garbage goes into record '0'
            number = int(record.split()[-1])
            if not number in lauegroup_info.keys():
                current_spacegroup = number
                lauegroup_info[current_spacegroup] = { }

        if 'symbol old' in record:
            name = record.split('\'')[1].split()
            if name:
                centring = name[0]
                lauegroup_info[current_spacegroup]['centring'] = centring

        if 'symbol laue' in record:
            laue = record.split('\'')[-2].strip()
            lauegroup_info[current_spacegroup]['laue'] = laue

    # next invert this to generate the mapping

    mapping = { }

    spacegroups = lauegroup_info.keys()
    spacegroups.sort()

    for spacegroup in spacegroups:
        centring = lauegroup_info[spacegroup]['centring']
        laue = lauegroup_info[spacegroup]['laue']

        # want the lowest spacegroup number for a given configuration
        if not mapping.has_key((centring, laue)):
            mapping[(centring, laue)] = spacegroup

    # transmogrify the input laue group to a useful key

    centring = lauegroup.split()[0]
    laue = ''
    for k in lauegroup.split()[1:]:
        if not k == '1':
            laue += k

    # select correct spacegroup from this mapping table
    spacegroup = mapping[(centring, laue)]

    # FIXME this will need P6 P622 P32 &c as well...

    spacegroup_to_lattice = {1: 'aP', 3: 'mP', 196: 'cF', 5: 'mC',
                             75: 'tP', 143: 'hP', 16: 'oP', 146: 'hR',
                             195: 'cP', 20: 'oC', 22: 'oF', 23: 'oI',
                             79: 'tI', 197: 'cI', 89: 'tP', 97: 'tI'
                             149: 'hP', 150: 'hP', 155: 'hP', 168: 'hP',
                             177: 'hP', 207: 'cP', 211: 'cI', 209: 'cF'}

    return spacegroup_to_lattice[spacegroup]

if __name__ == '__main__':
    print lauegroup_to_lattice('I m m m')
    print lauegroup_to_lattice('C 1 2/m 1')
    print lauegroup_to_lattice('P -1')
    print lauegroup_to_lattice('P 4/mmm')

if __name__ == '__main__':

    for spacegroup in get_all_spacegroups_long():
        enantiomorph = compute_enantiomorph(spacegroup)

        if enantiomorph != spacegroup:
            print '%s -> %s' % (spacegroup, enantiomorph)
