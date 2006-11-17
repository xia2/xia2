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
# 

import os
import sys

if not os.environ.has_key('SS_ROOT'):
    raise RuntimeError, 'SS_ROOT undefined'

symop = os.path.join(os.environ['SS_ROOT'],
                     'Data', 'Symmetry', 'symop.lib')

def spacegroup_name_short_to_long(name):
    for record in open(symop, 'r').readlines():
        if record[0] != ' ':
            shortname = record.split()[3]
            longname = record.split('\'')[1]
            if shortname.lower() == name.lower():
                return longname

