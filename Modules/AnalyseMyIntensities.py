#!/usr/bin/env python
# AnalyseMyIntensities.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 16th June 2007
# 
# A tool to use for the analysis and gathering of scaled intensity data
# from a single macromolecular crystal. This will be both a module (for
# use in xia2) and an application in it's own right, AMI.
#
# Example usage:
#
# ami hklin1 PEAK.HKL hklin2 INFL.HKL hklin3 LREM.HKL HKLOUT merged.mtz << eof
# drename file 1 pname demo xname only dname peak
# drename file 2 pname demo xname only dname infl
# drename file 3 pname demo xname only dname lrem
# solvent 0.53
# symm P43212 
# reindex h,k,l
# cell 55.67 55.67 108.92 90.0 90.0 90.0
# anomalous on
# eof
#
# should also allow for a HKLREF.

import os
import sys
import math

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Wrappers.CCP4.CCP4Factory import CCP4Factory

from Modules.Scalepack2Mtz import Scalepack2Mtz
from Modules.Mtz2Scalepack import Mtz2Scalepack
from Modules.XDS2Mtz import XDS2Mtz

from lib.Guff import is_mtz_file, is_xds_file, is_scalepack_file

class AnalyseMyIntensities:
    '''A class to use for intensity analysis. This will gather intensities
    (merged or unmerged) from multiple data sets and merge them together
    as well as telling you all about your data.'''

    def __init__(self):
        self._hklin_list = []
        self._project_info = []
        self._hklout = ''
        self._solvent = 0.0
        self._nres = 0
        self._nmol = 0
        self._cell = None
        self._symm = None
        self._reindex = None
        self._anomalous = False

        self._working_directory = os.getcwd()

        self._factory = CCP4Factory()

        # places to store the merging statistics
        self._merging_statistics = { }
        self._merging_statistics_keys = []

        return

    # admin functions

    def set_working_directory(self, working_directory):
        self._working_directory = working_directory
        self._factory.set_working_directory(working_directory)
        return

    def get_working_directory(self):
        return self._working_directory 

    # input functions

    def add_hklin(self, hklin, project_info = None):
        self._hklin_list.append(hklin)
        self._project_info.append(project_info)
        return

    def set_hklout(self, hklout):
        self._hklout = hklout
        return

    def set_solvent(self, solvent):
        self._solvent = solvent
        return

    def set_nres(self, nres):
        self._nres = nres
        return

    def set_nmol(self, nmol):
        self._nmol = nmol
        return

    def set_cell(self, cell):
        self._cell = cell
        return

    def set_symm(self, symm):
        self._symm = symm
        return

    def set_reindex(self, reindex):
        self._reindex = reindex
        return

    def set_anomalous(self, anomalous):
        self._anomalous = anomalous
        return

    def convert_to_mtz(self):
        '''Convert all HKLIN to MTZ format, storing merging statistics
        if available.'''

        mtz_in = []

        for j in range(len(self._hklin_list)):
            hklin = self._hklin_list[j]
            
            if is_mtz_file(hklin):
                mtz_in.append(hklin)
                
            elif is_xds_file(hklin):

                hklout = os.path.join(
                    self.get_working_directory(),
                    'AMI_HKLIN%d.mtz' % j)

                xds2mtz = XDS2Mtz()
                s = xds2mtz.xds_to_mtz(hklin, hklout, self._anomalous,
                                       spacegroup = self._symm,
                                       cell = self._cell,
                                       project_info = self._project_info[j])

                if s:
                    k = (j, self._project_info[i])
                    self._merging_statistics[j] = s
                    self._merging_statistucs_keys.append(k)

                mtz_in.append(hklout)
                
            elif is_scalepack_file(hklin):

                hklout = os.path.join(
                    self.get_working_directory(),
                    'AMI_HKLIN%d.mtz' % j)

                scalepack2mtz = Scalepack2Mtz()
                s = scalepack2mtz.scalepack_to_mtz(hklin, hklout,
                                                   self._anomalous,
                                                   self._symm, self._cell,
                                                   self._project_info[j])

                if s:
                    k = (j, self._project_info[i])
                    self._merging_statistics[j] = s
                    self._merging_statistucs_keys.append(k)
                
                mtz_in.append(hklout)

            else:
                raise RuntimeError, 'file %s unrecognised' % hklin

        self._hklin_list = mtz_in

        return

    
            
if __name__ == '__main__':
    infl = os.path.join(os.environ['XIA2_ROOT'],
                        'Data', 'Test', 'AMI', 'xds_unmerged',
                        'TS03_INFL_ANOM.hkl')
    lrem = os.path.join(os.environ['XIA2_ROOT'],
                        'Data', 'Test', 'AMI', 'xds_unmerged',
                        'TS03_LREM_ANOM.hkl')
    
    ami = AnalyseMyIntensities()

    ami.add_hklin(infl, project_info = ('AMI', 'TEST', 'INFL'))
    ami.add_hklin(lrem, project_info = ('AMI', 'TEST', 'LREM'))

    ami.convert_to_mtz()
