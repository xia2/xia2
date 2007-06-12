#!/usr/bin/env python
# Solve.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# A wrapper for the phasing program SOLVE (Tom Terwilliger)
#
# 11th June 207
# 

import sys
import os
import shutil

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Driver.DriverFactory import DriverFactory

def Solve(DriverType = None):
    '''Create a Solve instance based on the DriverType.'''

    DriverInstance = DriverFactory.Driver(DriverType)

    class SolveWrapper(DriverInstance.__class__):
        '''A wrapper class for Solve. This will take input from an
        MTZ file.'''

        def __init__(self):
            DriverInstance.__class__.__init__(self)

            # presume that this will use a "big" version of solve...
            self.set_executable('solve_huge')

            self._hklin = None
            self._hklout = None

            self._resolution_high = 40.0
            self._resolution_low = 0.0

            self._atom = None
            self._sites = None
            self._n_sites = 0
            self._nres = 0

            # this needs to contain label information for the
            # data sets and also the wavelength, f' anf f'' values
            self._wavelengths = []

            return

        def set_resolution_high(self, resolution_high):
            self._resolution_high = resolution_high
            return

        def set_resolution_low(self, resolution_low):
            self._resolution_low = resolution_low
            return

        def set_hklin(self, hklin):
            self._hklin = hklin
            return

        def get_hklout(self, hklout):
            return os.path.join(self.get_working_directory(),
                                'solve.mtz')

        def set_atom(self, atom):
            self._atom = atom
            return

        def set_sites(self, sites):
            self._sites = sites
            return

        def set_n_sites(self, n_sites):
            self._n_sites = n_sites
            return

        def set_nres(self, nres):
            self._nres = nres
            return

        def add_wavelength(self, name, wavelength, fp, fpp):
            self._wavelengths.append({'name':name,
                                      'wavelength':wavelength,
                                      'fp':fp,
                                      'fpp':fpp})
            return

        def run(self):
            if not self._hklin:
                raise RuntimeError, 'no HKLIN set'

            hklin = os.path.join(
                self.get_working_directory(),
                os.path.split(self._hklin)[-1])

            shutil.copyfile(self._hklin, hklin)

            self.start()

            self.input('logfile solve.logfile')
            self.input('resolution %f %f' % \
                       (self._resolution_low,
                        self._resolution_high))
            self.input('fixscattfactors')

            for j in range(len(self._wavelengths)):
                name = self._wavelengths[j]['name']
                number = j + 1
                self.input(
                    'labin FPH%d=F_%s SIGFPH%d=SIGF_%s DPH%d=DANO_%s SIGDPH%d=SIGDANO_%s' % \
                    (number, name, number, name, number, name, number, name))

            self.input('hklin %s' % os.path.split(hklin)[-1])
            self.input('mad_atom %s' % self._atom)
        
            for j in range(len(self._wavelengths)):

                number = j + 1
                self.input('lambda %d' % number)

                if j == 0 and self._sites:
                    # write the sites in too...
                    sites = self._sites['sites']
                    self.input('atomname %s' % sites[0]['atom'])
                    for site in sites:
                        self.input('xyz %s %s %s' % \
                                   site['fractional'])
                
                self.input('wavelength %f' % \
                           self._wavelengths[j]['wavelength'])
                self.input('fprimv_mad %f' % self._wavelengths[j]['fp'])
                self.input('fprprv_mad %f' % self._wavelengths[j]['fpp'])
                
            self.input('nres %d' % self._nres)
            self.input('nanomalous %d' % self._n_sites)

            if self._sites:
                self.input('analyze_solve')
                
            self.input('scale_mad')
            self.input('analyze_mad')

            self.input('solve')

            self.close_wait()

            # need to get some interesting stuff out here...

            return
            

    return SolveWrapper()


