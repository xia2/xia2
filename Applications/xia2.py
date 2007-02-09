#!/usr/bin/env python
# xia2.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 21/SEP/06
#
# A top-level interface to the whole of xia2, for data processing & analysis.
# 
# FIXED 28/NOV/06 record the total processing time to Chatter.
#
# FIXME 28/NOV/06 be able to e-mail someone with the job once finished.
#
# FIXME 17/JAN/07 check environment before startup.
# 

import sys
import os
import time

sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

from Handlers.CommandLine import CommandLine
from Handlers.Streams import Chatter
from Handlers.Files import cleanup

from XIA2Version import Version

def check_environment():
    '''Check the environment we are running in...'''

    xia2_keys = ['XIA2_ROOT', 'XIA2CORE_ROOT']

    ccp4_keys = ['CCP4', 'CLIBD']

    Chatter.write('Environment configuration...')
    for k in xia2_keys:
        if not os.environ.has_key(k):
            raise RuntimeError, '%s not defined - is xia2 set up?'
        Chatter.write('%s => %s' % (k, os.environ[k]))

    for k in ccp4_keys:
        if not os.environ.has_key(k):
            raise RuntimeError, '%s not defined - is CCP4 set up?'
        Chatter.write('%s => %s' % (k, os.environ[k]))

    return

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'
if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

def check():
    '''Check that the set-up is ok...'''

    sys.path.append(os.path.join((os.environ['XIA2CORE_ROOT']),
                                 'Python'))

    from TestPython import test_python_setup
    
    test_python_setup()

    return

def xia2():
    '''Actually process something...'''
    
    # print the version
    Chatter.write(Version)

    start_time = time.time()

    if not CommandLine.get_xinfo():
        raise RuntimeError, 'xinfo not defined'
    
    # this actually gets the processing started...
    Chatter.write(str(CommandLine.get_xinfo()))

    duration = time.time() - start_time

    # write out the time taken in a human readable way
    Chatter.write('Processing took %s' % \
                  time.strftime("%Hh %Mm %Ss", time.gmtime(duration)))

    # delete all of the temporary mtz files...
    cleanup()
    
    return

if __name__ == '__main__':

    check_environment()
    check()
    xia2()

    
