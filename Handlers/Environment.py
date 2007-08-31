#!/usr/bin/env python
# Environment.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# Maintained by Graeme Winter
# 18th September 2006
# 
# A handler for matters of the operating environment, which will impact
# on data harvesting, working directories, a couple of other odds & sods.
# 
# 
# 

import os

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

# to make a temporary BINSORT_SCR directory
import tempfile

from Handlers.Streams import Chatter, Debug

class _Environment:
    '''A class to store environmental considerations.'''

    def __init__(self):
        self._cwd = os.getcwd()
        self._is_setup = False
        self._setup()
        return

    def _setup(self):
        if self._is_setup:
            return
        
        self._is_setup = True
        harvest_directory = self.generate_directory('Harvest')
        self.setenv('HARVESTHOME', harvest_directory)

        # create a USER environment variable, to allow harvesting
	# in Mosflm to work (hacky, I know, but it really doesn't
	# matter too much...
        if not os.environ.has_key('USER'):
	    os.environ['USER'] = 'xia2'
            
        # check that BINSORT_SCR exists if set..

        if False:

            if os.environ.has_key('BINSORT_SCR'):
                path = os.environ['BINSORT_SCR']
                if not os.path.exists(path):
                    Debug.write('Making directory: %s (BINSORT_SCR)' % path)
                    os.makedirs(path)

        # create a random BINSORT_SCR directory

        binsort_scr = tempfile.mkdtemp()
        os.environ['BINSORT_SCR'] = binsort_scr
        Debug.write('Created BINSORT_SCR: %s' % binsort_scr)

        return

    def generate_directory(self, path_tuple):
        '''Used for generating working directories.'''
        self._setup()

        path = self._cwd

        if type(path_tuple) == type('string'):
            path_tuple = (path_tuple,)

        for p in path_tuple:
            path = os.path.join(path, p)

        if not os.path.exists(path):
            Debug.write('Making directory: %s' % path)
            os.makedirs(path)
        else:
            Debug.write('Directory exists: %s' % path)
    

        return path

    def setenv(self, name, value):
        '''A wrapper for os.environ.'''

        self._setup()
        os.environ[name] = value

        return

    def getenv(self, name):
        '''A wrapper for os.environ.'''
        self._setup()
        try:
            return os.environ[name]
        except:
            return None

Environment = _Environment()

if __name__ == '__main__':

    print Environment.getenv('HARVESTHOME')
