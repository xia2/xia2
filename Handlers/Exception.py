#!/usr/bin/env python
# Exception.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.


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