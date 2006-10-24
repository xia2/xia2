#!/usr/bin/env python
# Exception.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
#
# 24th October 2006
# 
# An exception to use in xia2dpa
# 

import exceptions

class DPAException(exceptions.Exception):
    def __init__(self, args):
        self.args = args

    def __repr__(self):
        return repr(self.args)

    def __str__(self):
        return self.__repr__()