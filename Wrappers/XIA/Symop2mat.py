#!/usr/bin/env python
# Symop2mat.py
# 
#   Copyright (C) 2007 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.# 
#  
# A wrapper for the jiffy program symop2mat, which converts a symmetry
# operation to a matrix, for input into XDS CORRECT from e.g. pointless.
# 
# 21st May 2007
#

import os
import sys

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Driver.DriverFactory import DriverFactory

def Symop2mat(DriverType = None):
    '''A factory for symop2mat wrappers.'''

    DriverInstance = DriverFactory.Driver(DriverType)

    class Symop2matWrapper(DriverInstance.__class__):
        '''A wrapper for the jiffy program symop2mat.'''

        def __init__(self):

            DriverInstance.__class__.__init__(self)
            self.set_executable('symop2mat')
            
            return

        def convert12(self, symop):

            # first remove any '*' tokens from the
            # line as these are implied in the definition
            # see bug # 2723

            symop = symop.replace('*', '')
            
            self.reset()
            self.add_command_line('OP')
            self.add_command_line(symop)
            
            self.start()
            
            self.close_wait()
            self.check_for_errors()
            
            matrix = []

            output = self.get_all_output()
            for j in range(len(output)):
                line = output[j]
                if 'The matrix' in line:
                    for k in range(3):
                        for token in output[j + k + 1].split():
                            matrix.append(float(token))
                    
            return matrix

        def convert(self, symop):
            matrix = self.convert12(symop)

            result = []
            for j in range(3):
                for i in range(3):
                    result.append(matrix[j * 4 + i])
            return result

    return Symop2matWrapper()

if __name__ == '__main__':

    operations = ['h,k,l', 'k,l,h']

    symop2mat = Symop2mat()

    for o in operations:
        print o, symop2mat.convert(o)


        
