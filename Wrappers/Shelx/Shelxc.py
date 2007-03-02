#!/usr/bin/env python
# Shelxc.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 16th November 2006
#  
# A wrapper for SHELXC from the SHELX phasing package. SHELXC prepares 
# the data for substructure determination, and needs to know the "names"
# of the different data sets, e.g. PEAK INFL LREM HREM NATIVE.
# For this to work it is assumed that these will be the dataset (e.g.
# wavelength) names provided.
# 

import sys
import os
import shutil

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Driver.DriverFactory import DriverFactory

def Shelxc(DriverType = None):
    '''Create a Shelxc instance based on the DriverType.'''

    DriverInstance = DriverFactory.Driver(DriverType)

    class ShelxcWrapper(DriverInstance.__class__):
        '''A wrapper class for Shelxc.'''

        def __init__(self):
            DriverInstance.__class__.__init__(self)

            self.set_executable('shelxc')

            # input files
            self._infl = None
            self._lrem = None
            self._peak = None
            self._hrem = None
            self._sad = None
            self._native = None

            # heavy atom information
            self._n_sites = 0

            # cell and symmetry
            self._cell = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
            self._symmetry = None

            # naming information
            self._name = None

            # control information for shelxd (which will go in through the
            # .ins file)

            self._ntry = 20
            self._mind = 3.5

            # output information
            self._fa_hkl = None

            return

        def _jimmy_file_name(self, file):
            '''It appears that the maximum length of an input file name is
            80 characters - so it it is longer than this copy the file.'''

            if len(file) < 70:
                return file

            shutil.copyfile(file,
                            os.path.join(self.get_working_directory(),
                                         os.path.split(file)[-1]))
            return os.path.split(file)[-1]

        def set_cell(self, cell):
            self._cell = cell
            return

        def set_symmetry(self, symmetry):
            self._symmetry = symmetry
            return

        def set_n_sites(self, n_sites):
            self._n_sites = n_sites
            return

        def set_peak(self, peak):
            self._peak = self._jimmy_file_name(peak)
            return

        def set_infl(self, infl):
            self._infl = self._jimmy_file_name(infl)
            return

        def set_lrem(self, lrem):
            self._lrem = self._jimmy_file_name(lrem)
            return

        def set_hrem(self, hrem):
            self._hrem = self._jimmy_file_name(hrem)
            return

        def set_native(self, native):
            self._native = self._jimmy_file_name(native)
            return

        def set_sad(self, sad):
            self._sad = self._jimmy_file_name(sad)
            return

        def set_name(self, name):
            self._name = name
            return

        def prepare(self):
            '''Prepare the experimental phasing data.'''

            self.add_command_line(self._name)

            self.start()

            if self._peak:
                self.input('PEAK %s\n' % self._peak)
            if self._infl:
                self.input('INFL %s\n' % self._infl)
            if self._hrem:
                self.input('HREM %s\n' % self._hrem)
            if self._lrem:
                self.input('LREM %s\n' % self._lrem)
            if self._sad:
                self.input('SAD %s\n' % self._sad)
            if self._native:
                self.input('NATIVE %s\n' % self._native)
            
            self.input('CELL %f %f %f %f %f %f' % tuple(self._cell))
            self.input('SPAG %s' % self._symmetry)
            self.input('FIND %d' % self._n_sites)
            self.input('NTRY %d' % self._ntry)
            self.input('MIND %f' % (-1.0 * self._mind))

            self.close_wait()

            # perform checks here for errors...

            self.check_for_errors()

            for line in self.get_all_output():
                if 'Reflections written' in line and 'SHELXD/E' in line:
                    self._fa_hkl = line.split()[5]

            return

        def get_fa_hkl(self):
            return self._fa_hkl

    return ShelxcWrapper()

if __name__ == '__main__':
    # run a test

    data_dir = os.path.join(os.environ['X2TD_ROOT'],
                            'Test', 'UnitTest', 'Interfaces',
                            'Scaler', 'Unmerged')

    sc = Shelxc()

    sc.write_log_file('shelxc.log')

    sc.set_cell((57.74, 76.93, 86.57, 90.00, 90.00, 90.00))
    # sc.set_symmetry('P212121')
    sc.set_symmetry('P222')
    sc.set_n_sites(5)
    sc.set_infl(os.path.join(data_dir, 'TS00_13185_unmerged_INFL.sca'))
    sc.set_lrem(os.path.join(data_dir, 'TS00_13185_unmerged_LREM.sca'))
    sc.set_peak(os.path.join(data_dir, 'TS00_13185_unmerged_PEAK.sca'))
    sc.set_name('TS00')
    sc.prepare()
    
