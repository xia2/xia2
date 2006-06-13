#!/usr/bin/env python
# xia2scan.py
# Maintained by G.Winter
# 9th June 2006
# 
# A small program to summarise the diffraction strength from a list of
# diffraction images. This will use labelit for both indexing and 
# distling.
# 
# Requires:
# 
# The correct beam centre.
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


