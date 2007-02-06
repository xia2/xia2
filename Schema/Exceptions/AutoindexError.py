#!/usr/bin/env python
# AutoindexError.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
# 
# An exception to be raised when an integration program decides that the 
# autoindexing has failed - e.g. through a program error more than 
# bad data.

from exceptions import Exception

class AutoindexError(Exception):
    '''An exception to be raised when autoindexing fails.'''

    pass

if __name__ == '__main__':
    raise AutoindexError, 'rmsd variation too large'


        
