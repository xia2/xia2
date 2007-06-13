#!/usr/bin/env python
# Flags.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 4th May 2007
# 
# A singleton to handle flags, which can be imported more easily
# as it will not suffer the problems with circular references that
# the CommandLine singleton suffers from.

class _Flags:
    '''A singleton to manage boolean flags.'''

    def __init__(self):
        self._quick = False
        self._migrate_data = False
        self._trust_timestaps = False
        self._parallel = 0

        # these are development parameters for the XDS implementation
        self._z_min = 0.0
        self._always_refine = False

        return

    def set_quick(self, quick):
        self._quick = quick
        return

    def get_quick(self):
        return self._quick

    def set_migrate_data(self, migrate_data):
        self._migrate_data = migrate_data
        return

    def get_migrate_data(self):
        return self._migrate_data

    def set_trust_timestamps(self, trust_timestamps):
        self._trust_timestamps = trust_timestamps
        return

    def get_trust_timestamps(self):
        return self._trust_timestamps

    def set_parallel(self, parallel):
        self._parallel = parallel
        return

    def get_parallel(self):
        return self._parallel

    def set_z_min(self, z_min):
        self._z_min = z_min
        return

    def get_z_min(self):
        return self._z_min

    def set_always_refine(self, always_refine):
        self._always_refine = always_refine
        return

    def get_always_refine(self):
        return self._always_refine

Flags = _Flags()




    
