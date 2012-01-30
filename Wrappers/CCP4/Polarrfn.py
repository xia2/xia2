#!/usr/bin/env python
# Polarrfn.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 20th June 2007
#

import sys
import os
import math

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Driver.DriverFactory import DriverFactory
from Decorators.DecoratorFactory import DecoratorFactory
from Handlers.Streams import Chatter

from Experts.SymmetryExpert import gen_rot_mat_euler, symop_to_mat
from Handlers.Syminfo import Syminfo

def matrix_diff(a, b):
    return sum([(a[i] - b[i]) * (a[i] - b[i]) for i in range(9)])

def Polarrfn(DriverType = None):
    '''A factory for PolarrfnWrapper classes.'''

    DriverInstance = DriverFactory.Driver(DriverType)
    CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, 'ccp4')

    class PolarrfnWrapper(CCP4DriverInstance.__class__):
        '''A wrapper for Polarrfn, using the CCP4-ified Driver.'''

        def __init__(self):
            # generic things
            CCP4DriverInstance.__class__.__init__(self)

            self.set_executable(os.path.join(
                os.environ.get('CBIN', ''), 'polarrfn'))

            self._labin_f = 'F'
            self._labin_sigf = 'SIGF'
            self._height = 50

            return

        def set_height(self, height):
            self._height = height

        def set_labin(self, labin_f, labin_sigf):
            self._labin_f = labin_f
            self._labin_sigf = labin_sigf
            return

        def polarrfn(self):

            self.check_hklin()

            self.start()

            self.input('self 20 4')
            self.input('resolution 15 3')
            self.input('crystal file 1')
            self.input('labin file 1 F=%s SIGF=%s' % (self._labin_f,
                                                      self._labin_sigf))
            self.input('noprint')

            self.input('find %d 100' % self._height)

            self.close_wait()

            # should check for errors etc here

            # next try and read the various peaks...

            output = self.get_all_output()

            j = 0

            peaks = { }

            symops = { }

            while j < len(self.get_all_output()):

                line = output[j]

                if 'Space group =' in line:
                    operations = Syminfo.get_symops(
                        int(line.replace(')', '').split()[-1]))
                    for op in operations:
                        symops[tuple(symop_to_mat(op))] = op

                current_peak = 0

                if 'Alpha   Beta   Gamma      Peak' in line:

                    while not 'The rotation given' in line:
                        line = output[j]
                        if ['Peak'] == line.split()[:1]:
                            current_peak = int(line.split()[-1])
                            peaks[current_peak] = []
                        else:
                            try:
                                a = int(line.split()[0])
                                b = int(line.split()[1])
                                if a == 1 and b == 1:
                                    peak = map(float, line.split()[2:5])
                                    peak.append(float(line.split()[5]))
                                    peaks[current_peak].append(peak)
                            except:
                                pass


                        j += 1

                j += 1

            numbers = peaks.keys()
            numbers.sort()
            if 0 in numbers:
                numbers.remove(0)

            unique = { }
            keys = []

            for n in numbers:
                for p in peaks[n]:
                    key = p[0], p[1], p[2]
                    if unique.has_key(key):
                        if unique[key] > p[3]:
                            continue

                    unique[key] = p[3]
                    if not key in keys:
                        keys.append(key)

            Chatter.write('... Alpha Beta  Gamma Height (matching symop)')

            for k in keys:

                # in here compute a matrix for this rotation
                # compare it to the matrices derived from the
                # symmetry operations - if it matches, record
                # the symop, else don't.

                matrix = gen_rot_mat_euler(k[2], k[1], k[0])

                matstr = '[%.2f %.2f %.2f %.2f %.2f %.2f %.2f %.2f %.2f]' % \
                         tuple(matrix)

                symop = ''

                for mat in symops.keys():
                    diff = matrix_diff(list(mat), matrix)
                    if diff < 0.1:
                        symop = symops[mat]


                if symop:
                    Chatter.write('... %5.1f %5.1f %5.1f %5.1f  (%s)' % \
                                  (k[0], k[1], k[2], unique[k], symop))
                else:
                    Chatter.write('... %5.1f %5.1f %5.1f %5.1f' % \
                                  (k[0], k[1], k[2], unique[k]))

            return


    return PolarrfnWrapper()


if __name__ == '__main__':

    from Ecalc import Ecalc

    if len(sys.argv) < 2:
        raise RuntimeError, '%s hklin [F SIGF]' % sys.argv[0]

    hklin = sys.argv[1]

    if len(sys.argv) == 4:
        labin_f = sys.argv[2]
        labin_sigf = sys.argv[3]
    else:
        labin_f = 'F'
        labin_sigf = 'SIGF'

    ecalc = Ecalc()
    ecalc.set_hklin(hklin)
    ecalc.set_hklout('temp.mtz')
    ecalc.set_labin(labin_f, labin_sigf)
    ecalc.ecalc()

    polar = Polarrfn()
    polar.set_hklin('temp.mtz')
    polar.set_labin('E', 'SIGE')
    polar.polarrfn()
