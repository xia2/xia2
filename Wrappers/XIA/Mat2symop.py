#!/usr/bin/env python
# Mat2symop.py
# 
#   Copyright (C) 2007 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.# 
#  
# A wrapper for the jiffy program mat2symop, which converts a matrix
# to a symmetry operation, for managing composition of symops.
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

def Mat2symop(DriverType = None):
    '''A factory for mat2symop wrappers.'''

    DriverInstance = DriverFactory.Driver(DriverType)

    class Mat2symopWrapper(DriverInstance.__class__):
        '''A wrapper for the jiffy program mat2symop.'''

        def __init__(self):

            DriverInstance.__class__.__init__(self)
            self.set_executable('mat2symop')
            
            return

        def convert(self, matrix):
            self.reset()
            self.add_command_line('MAT')

            # compose the input

            matrix_string = ''
            if len(matrix) == 9:
                for j in range(9):
                    matrix_string = '%s %d' % (matrix_string, matrix[j])
            else:
                for j in range(12):
                    if j % 4 == 0:
                        continue
                    matrix_string = '%s %d' % (matrix_string, matrix[j])
                
            self.add_command_line(matrix_string)
            
            self.start()
            
            self.close_wait()
            self.check_for_errors()
            
            operation = None
            
            for line in self.get_all_output():
                if 'OPERATION' in line:
                    operation = line.replace('OPERATION', '').replace(
                        ' ', '')

            # convert to H,K,L from X,Y,Z

            operation = operation.replace('X', 'H')
            operation = operation.replace('Y', 'K')
            operation = operation.replace('Z', 'L')
                    
            return operation.lower()

    return Mat2symopWrapper()

if __name__ == '__main__':

    operations = [[1, 0, 0, 0, 1, 0, 0, 0, 1],
                  [0, 1, 0, 0, 0, 1, 1, 0, 0]]
                  
    mat2symop = Mat2symop()

    for o in operations:
        print o, mat2symop.convert(o)
