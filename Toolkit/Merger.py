#!/usr/bin/env cctbx.python
# Merger.py
# 
#   Copyright (C) 2010 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
# 
# A toolkit component for merging symmetry related intensity measurements
# to calculate:
# 
#  - Rmerge vs. batch, resolution
#  - Chi^2
#  - Multiplicity
#  - Unmerged I/sigma
# 
# Then in a separate calculation, E^4, merged I/sigma and completeness will
# be calculated. This should be a different Toolkit component.

import sys
import math
import os
import time

from iotbx import mtz

from MtzFactory import mtz_file

class unmerged_intensity:
    '''A class to represent and encapsulate the multiple observations of a
    given intensity defined in terms of the Miller index. It is assumed that
    these are compatible observations.'''

    def __init__(self):
        self._observations = []

        return

    def add(self, misym, i, sigi):
        self._observations.append((misym, i, sigi))
        return

    def merge(self):
        '''Merge the observations recorded so far, return Imean, SigImean.'''

        assert(self._observations)

        sum_wi = 0.0
        sum_w = 0.0

        for o in self._observations:
            i = o[1]
            w = 1.0 / (o[2] * o[2])
            sum_w += w
            sum_wi += w * i

        i_mean = sum_wi / sum_w
        sigi_mean = math.sqrt(1.0 / sum_w)

        return i_mean, sigi_mean

    def multiplicity(self):
        return len(self._observations)

    def rmerge_contribution(self, i_mean):
        '''Calculate the contribution of this reflection to Rmerge.'''

        return sum([math.fabs(o[1] - i_mean) for o in self._observations])

    def isigma_contribution(self):
        '''Calculate the contribution to the I/sigma. N.B. multiplicity!'''
        return sum(o[1] / o[2] for o in self._observations)

class merger:
    '''A class to calculate things from merging reflections.'''

    def __init__(self, hklin):
        self._mf = mtz_file(hklin)
        self._unmerged_reflections = { }
        self._merged_reflections = { }

        all_columns = self._mf.get_column_names()

        assert('M_ISYM' in all_columns)
        assert('I' in all_columns)
        assert('SIGI' in all_columns)

        self._read_unmerged_reflections()
        self._merge_reflections()

        return

    def _read_unmerged_reflections(self):
        '''Actually read the reflections in to memory.'''

        mi = self._mf.get_miller_indices()
        m_isym = self._mf.get_column_values('M_ISYM')
        i = self._mf.get_column_values('I')
        sigi = self._mf.get_column_values('SIGI')
        
        for j in range(len(i)):
            hkl = mi[j]
            if not hkl in self._unmerged_reflections:
                self._unmerged_reflections[hkl] = unmerged_intensity()
            self._unmerged_reflections[hkl].add(m_isym[j], i[j], sigi[j])

        return

    def _merge_reflections(self):
        '''Merge the currently recorded unmerged reflections.'''

        for hkl in self._unmerged_reflections:
            i_mean, sigi_mean = self._unmerged_reflections[hkl].merge()
            self._merged_reflections[hkl] = i_mean, sigi_mean

        return

    def calculate_rmerge(self):
        '''Calculate the overall Rmerge.'''

        t = 0.0
        b = 0.0
        
        for hkl in self._unmerged_reflections:
            i_mean = self._merged_reflections[hkl][0]
            t += self._unmerged_reflections[hkl].rmerge_contribution(i_mean)
            b += self._unmerged_reflections[hkl].multiplicity() * i_mean

        return t / b

    def calculate_multiplicity(self):
        '''Calculate the overall average multiplicity.'''
        
        multiplicity = [float(self._unmerged_reflections[hkl].multiplicity()) \
                        for hkl in self._unmerged_reflections]
        return sum(multiplicity) / len(multiplicity)

    def calculate_merged_isigma(self):
        '''Calculate the average merged I/sigma.'''

        isigma_values = [self._merged_reflections[hkl][0] / \
                         self._merged_reflections[hkl][1] \
                         for hkl in self._merged_reflections]

        return sum(isigma_values) / len(isigma_values)

    def calculate_unmerged_isigma(self):
        '''Calculate the average unmerged I/sigma.'''

        return sum([self._unmerged_reflections[hkl].isigma_contribution() \
                    for hkl in self._unmerged_reflections]) / \
                    sum([self._unmerged_reflections[hkl].multiplicity() \
                         for hkl in self._unmerged_reflections])


if __name__ == '__main__':
    import sys

    m = merger(sys.argv[1])
    
    print 'Rmerge:       %6.3f' % m.calculate_rmerge()
    print 'Multiplicity: %6.3f' % m.calculate_multiplicity()
    print 'Mn(I/sigma):  %6.3f' % m.calculate_merged_isigma()
    print 'I/sigma):     %6.3f' % m.calculate_unmerged_isigma()
    
