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

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Driver.DriverFactory import DriverFactory
from Decorators.DecoratorFactory import DecoratorFactory

def normalize(angle):
    '''Find the nearest 10 degree angle to this angle...'''
    
    a = angle / 10.0

    n = int(a)
    if a - n > 0.5:
        n += 1
        
    return 10.0 * n

def Polarrfn(DriverType = None):
    '''A factory for PolarrfnWrapper classes.'''

    DriverInstance = DriverFactory.Driver(DriverType)
    CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, 'ccp4')

    class PolarrfnWrapper(CCP4DriverInstance.__class__):
        '''A wrapper for Polarrfn, using the CCP4-ified Driver.'''

        def __init__(self):
            # generic things
            CCP4DriverInstance.__class__.__init__(self)

            self.set_executable('polarrfn')

            self._labin_f = 'F'
            self._labin_sigf = 'SIGF'

            return

        def set_labin(self, labin_f, labin_sigf):
            self._labin_f = labin_f
            self._labin_sigf = labin_sigf
            return            

        def polarrfn(self):
            
            self.check_hklin()

            self.start()

            self.input('self 20')
            self.input('resolution 15 3')
            self.input('crystal file 1')
            self.input('labin file 1 F=%s SIGF=%s' % (self._labin_f,
                                                      self._labin_sigf))
            self.input('noprint')

            # look for peaks 1/3 the size of the origin peak
            
            self.input('find 33 100')

            self.close_wait()

            # should check for errors etc here

            # next try and read the various peaks...

            output = self.get_all_output()

            j = 0

            peaks = { }
            
            while j < len(self.get_all_output()):

                line = output[j]

                current_peak = 0

                if 'Alpha   Beta   Gamma      Peak' in line:

                    while not 'The rotation given' in line:
                        line = output[j]
                        if ['Peak'] == line.split()[:1]:
                            current_peak = int(line.split()[-1])
                            peaks[current_peak] = []
                        elif ['1', '1'] == line.split()[:2]:
                            peak = map(normalize,
                                       map(float, line.split()[2:5]))
                            peak.append(float(line.split()[5]))
                            peaks[current_peak].append(peak)


                        j += 1

                j += 1

            numbers = peaks.keys()
            numbers.sort()
            if 0 in numbers:
                numbers.remove(0)

            for n in numbers:
                for p in peaks[n]:
                    print '%2d %5.1f %5.1f %5.1f %5.1f' % \
                          (n, p[0], p[1], p[2], p[3])


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
    
    
