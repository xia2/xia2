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

def merge_scala_intensities(hklin):
    '''Read in reflection file given in hklin, merge the observations to a
    minimal set.'''

    reflections = { }

    mf = mtz_file(hklin)

    # assert: for my purposes here I am looking for H, K, L, M_ISYM,
    # I, SIGI columns as are expected in Scala output unmerged MTZ format.

    all_columns = mf.get_column_names()

    assert('M_ISYM' in all_columns)
    assert('I' in all_columns)
    assert('SIGI' in all_columns)

    mi = mf.get_miller_indices()

    m_isym = mf.get_column_values('M_ISYM')
    i = mf.get_column_values('I')
    sigi = mf.get_column_values('SIGI')
    
    for j in range(len(i)):
        hkl = mi[j]
        if not hkl in reflections:
            reflections[hkl] = unmerged_intensity()
        reflections[hkl].add(m_isym[j], i[j], sigi[j])

    # ok that should be all the reflections gathered.... now merge them

    merged_reflections = { }
    
    for hkl in reflections:
        i_mean, sigi_mean = reflections[hkl].merge()
        merged_reflections[hkl] = i_mean, sigi_mean

    # calculate Rmerge

    t = 0.0
    b = 0.0

    for hkl in reflections:
        i_mean = merged_reflections[hkl][0]
        t += reflections[hkl].rmerge_contribution(i_mean)
        b += reflections[hkl].multiplicity() * i_mean

    print t / b

if __name__ == '__main__':
    import sys

    merge_scala_intensities(sys.argv[1])
    
