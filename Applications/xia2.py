#!/usr/bin/env python
# xia2.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
#
# 21/SEP/06
#
# A top-level interface to the whole of xia2, for data processing & analysis.
# 
# 


import sys
import os

if not os.environ.has_key('DPA_ROOT'):
    raise RuntimeError, 'DPA_ROOT not defined'
if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['DPA_ROOT']))

from Handlers.CommandLine import CommandLine
from Handlers.Streams import Chatter

def xia2():
    if not CommandLine.get_xinfo():
        raise RuntimeError, 'xinfo not defined'
    
    Chatter.write(str(CommandLine.get_xinfo()))

    return

if __name__ == '__main__':
    xia2()

    
