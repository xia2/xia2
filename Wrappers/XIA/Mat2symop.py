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
import math

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Driver.DriverFactory import DriverFactory

from lib.Guff import nint

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

            # multiply all elements of matrix by 6 (equal to the
            # product of 2, 3 - can't find any elements with a 4
            # in them...

            matrix = [m * 6.0 for m in matrix]

            # check integerness

            for m in matrix:
                if math.fabs(m - nint(m)) > 0.1:
                    raise RuntimeError, \
                          'non multiple of 1/6 in matrix'

            self.reset()
            self.add_command_line('MAT')

            # compose the input

            matrix_string = ''

            for m in matrix:
                if nint(m) == 1:
                    raise RuntimeError, \
                          'mat2symop error # 2724 - please report'

            if len(matrix) == 9:
                for j in range(9):
                    matrix_string = '%s %d' % (matrix_string, nint(matrix[j]))
            else:
                for j in range(12):
                    if j % 4 == 0:
                        continue
                    matrix_string = '%s %d' % (matrix_string, nint(matrix[j]))
                
            self.add_command_line(matrix_string)

            self.start()
            
            self.close_wait()
            self.check_for_errors()
            
            operation = None

            output = self.get_all_output()
            for j in range(len(output)):
                line = output[j].strip()

                if 'OPERATION' in line:
                    operation = line.replace('OPERATION', '').replace(
                        ' ', '')
                    # check it is not on next line...
                    if operation == '':
                        operation = output[j + 1].replace(' ', '')

            if not operation:
                raise RuntimeError, 'error reading operation'

            # convert to H,K,L from X,Y,Z

            operation = operation.replace('X', 'H')
            operation = operation.replace('Y', 'K')
            operation = operation.replace('Z', 'L')

            # and convert back to fractions... messy but...
            operation = operation.replace('6', '')
            operation = operation.replace('3', '1/M')
            operation = operation.replace('2', '1/3')
            operation = operation.replace('4', '2/3')
            operation = operation.replace('M', '2')
            operation = operation.replace('9', '3/2')
                                
            return operation.lower()

    return Mat2symopWrapper()

if __name__ == '__main__':

    operations = [[0.5, 0.5, 0.0, -1.5, 0.5, 0.0, 0.0, 0.0, 1.0]]
                  
    mat2symop = Mat2symop()

    for o in operations:
        print o, mat2symop.convert(o)
