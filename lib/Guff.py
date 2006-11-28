#!/usr/bin/env python
# Guff.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
#
# 21/SEP/06
# 
# Python routines which don't really belong anywhere else.
# 

import os
import sys

if not os.environ.has_key('DPA_ROOT'):
    raise RuntimeError, 'DPA_ROOT not defined'
if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.environ['DPA_ROOT'] in sys.path:
    sys.path.append(os.path.join(os.environ['DPA_ROOT']))

from Handlers.Streams import Chatter

def inherits_from(this_class,
                  base_class_name):
    '''Return True if base_class_name contributes to the this_class class.'''

    if this_class.__bases__:
        for b in this_class.__bases__:
            if inherits_from(b, base_class_name):
                return True

    if this_class.__name__ == base_class_name:
        return True

    return False

def is_mtz_file(filename):
    '''Check if a file is MTZ format - at least according to the
    magic number.'''

    magic = open(filename, 'rb').read(4)

    if magic == 'MTZ ':
        return True

    return False

def nifty_power_of_ten(num):
    '''Return 10^n: 10^n > num; 10^(n-1) <= num.'''

    result = 10

    while result <= num:
        result *= 10

    return result

##### START MESSY CODE #####

_run_number = 0

def _get_number():
    global _run_number
    _run_number += 1
    return _run_number

###### END MESSY CODE ######

def auto_logfiler(DriverInstance):
    '''Create a "sensible" log file for this program wrapper & connect it.'''

    working_directory = DriverInstance.get_working_directory()
    executable = os.path.split(DriverInstance.get_executable())[-1]
    number = _get_number()

    if executable[-4:] == '.bat':
        executable = executable[:-4]
        
    if executable[-4:] == '.exe':
        executable = executable[:-4]

    logfile = os.path.join(working_directory,
                           '%d_%s.log' % (number, executable))

    Chatter.write('Logfile: %s -> %s' % (executable,
                                         logfile))

    DriverInstance.write_log_file(logfile)

    return logfile

def transpose_loggraph(loggraph_dict):
    '''Transpose the information in the CCP4-parsed-loggraph dictionary
    into a more useful structure.'''

    columns = loggraph_dict['columns']
    data = loggraph_dict['data']

    results = { }

    # FIXME column labels are not always unique - so prepend the column
    # number - that'll make it unique! PS counting from 1 - 01/NOV/06

    new_columns = []

    j = 0
    for c in columns:
        j += 1
        col = '%d_%s' % (j, c)
        new_columns.append(col)
        results[col] = []

    nc = len(new_columns)

    for record in data:
        for j in range(nc):
            results[new_columns[j]].append(record[j])

    return results                            

def nint(a):
    '''return the nearest integer to a.'''

    i = int(a)
    if (a - i) > 0.5:
        i += 1

    return i

# this should be in a symmetry library somewhere

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

    # and finally convert this to a lattice
    lattice_to_spacegroup = {'aP':1, 'mP':3, 'mC':5,
                             'oP':16, 'oC':20, 'oF':22,
                             'oI':23, 'tP':75, 'tI':79,
                             'hP':143, 'hR':146,
                             'cP':195, 'cF':196,
                             'cI':197}
    
    spacegroup_to_lattice = { }
    for k in lattice_to_spacegroup.keys():
        spacegroup_to_lattice[lattice_to_spacegroup[k]] = k

    return spacegroup_to_lattice[spacegroup]

if __name__ == '__main__':
    print lauegroup_to_lattice('I m m m')
    print lauegroup_to_lattice('C 1 2/m 1')
    print lauegroup_to_lattice('P -1')
    
if __name__ == '__main_old__':
    # run a test

    class A:
        pass

    class B(A):
        pass

    class C:
        pass

    if inherits_from(B, 'A'):
        print 'ok'
    else:
        print 'failed'

    if not inherits_from(C, 'A'):
        print 'ok'
    else:
        print 'failed'
