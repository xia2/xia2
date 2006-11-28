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

if __name__ == '__main__':

    for spacegroup in get_all_spacegroups_long():
        enantiomorph = compute_enantiomorph(spacegroup)

        if enantiomorph != spacegroup:
            print '%s -> %s' % (spacegroup, enantiomorph)
