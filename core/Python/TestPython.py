#!/usr/bin/env python
# TestPython.py
#
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 24 May 2006
# 
# A small test script for ensuring that all of the modules required for the
# Driver class to work are installed.

def test_python_setup():
    '''Run tests...'''

    import os
    import subprocess

    if os.name == 'nt' and False:
        import win32api

if __name__ == '__main__':
    test_python_setup()


    
