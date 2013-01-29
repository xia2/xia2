#!/usr/bin/env python
# bits.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 21/SEP/06
#
# Python routines which don't really belong anywhere else.
#

import os
import sys
import math

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'
if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

from Handlers.Streams import Chatter, Debug

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

def is_xds_file(filename):
    '''Check to see if a file looks like XDS_ASCII format.'''

    first_token = open(filename, 'r').readline().split()[0]

    if first_token == '!FORMAT=XDS_ASCII':
        return True

    return False

def is_scalepack_file(filename):
    '''Determine if a file looks like scalepack format.'''

    return True

def nifty_power_of_ten(num):
    '''Return 10^n: 10^n > num; 10^(n-1) <= num.'''

    result = 10

    while result <= num:
        result *= 10

    return result

def mean_sd(list_of_numbers):
    mean = sum(list_of_numbers) / len(list_of_numbers)
    sd = 0.0
    for l in list_of_numbers:
        sd += (l - mean) * (l - mean)
    sd /= len(list_of_numbers)
    return (mean, math.sqrt(sd))

# FIXNE redundant

def meansd(values):
    mean = sum(values) / len(values)
    var = sum([(v - mean) * (v - mean) for v in values]) / len(values)
    return mean, math.sqrt(var)

def remove_outliers(values, limit):
    result = []
    outliers = []
    for j in range(len(values)):
        scratch = []
        for k in range(len(values)):
            if j != k:
                scratch.append(values[k])
        m, s = meansd(scratch)
        if math.fabs(values[j] - m) / s <= limit * s:
            result.append(values[j])
        else:
            outliers.append(values[j])

    return result, outliers

##### START MESSY CODE #####

_run_number = 0

def _get_number():
    global _run_number
    _run_number += 1
    return _run_number

###### END MESSY CODE ######

def auto_logfiler(DriverInstance, extra = None):
    '''Create a "sensible" log file for this program wrapper & connect it.'''

    working_directory = DriverInstance.get_working_directory()

    if not working_directory:
        return
    
    executable = os.path.split(DriverInstance.get_executable())[-1]
    number = _get_number()

    if executable[-4:] == '.bat':
        executable = executable[:-4]

    if executable[-4:] == '.exe':
        executable = executable[:-4]

    if extra:
        logfile = os.path.join(working_directory,
                               '%d_%s_%s.log' % (number, executable, extra))
    else:
        logfile = os.path.join(working_directory,
                               '%d_%s.log' % (number, executable))

    DriverInstance.set_xpid(number)

    Debug.write('Logfile: %s -> %s' % (executable,
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

    if a > 0:
        if a - i > 0.5:
            i += 1

    elif a < 0:
        if a - i < -0.5:
            i -= 1

    return i

if __name__ == '__main__test__':
    # test out nint
    tests = [(2.9, 3), (3.1, 3), (-2.9, -3), (-3.1, -3)]
    for t in tests:
        if nint(t[0]) != t[1]:
            raise RuntimeError, 'nint failed for %f' % t[0]

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
