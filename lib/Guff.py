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
    
if __name__ == '__main__':
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
