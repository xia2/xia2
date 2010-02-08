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

def merge_scala_intensities(hklin):
    '''Read in reflection file given in hklin, merge the observations to a
    minimal set.'''

    reflections = { }

    mf = mtz_file(hklin)

    # assert: for my purposes here I am looking for H, K, L, M_ISYM,
    # I, SIGI columns as are expected in Scala output unmerged MTZ format.

    assert('HKL_base' in mf.get_crystal_names())
    assert('HKL_base' in mf.get_crystal('HKL_base').get_datasets())

    md = mf.get_crystal('HKL_base').get_dataset('HKL_base')

    assert('H' in md.column_names())
    assert('K' in md.column_names())
    assert('L' in md.column_names())
    assert('M_ISYM' in md.column_names())
    assert('I' in md.column_names())
    assert('SIGI' in md.column_names())

    h = md.get_column_values('H')
    k = md.get_column_values('K')
    l = md.get_column_values('L')
    m_isym = md.get_column_values('M_ISYM')
    i = md.get_column_values('I')
    sigi = md.get_column_values('SIGI')
    
    for j in range(len(i)):
        hkl = int(round(h[j])), int(round(k[j])), int(round(l[j]))
        if not hkl in reflections:
            reflections[hkl] = unmerged_intensity()
        reflections[hkl].add(misym[j], i[j], sigi[j])

    # ok that should be all the reflections gathered.... now merge them

    

if __name__ == '__main__':

    import random

    ui = unmerged_intensity()

    for j in range(10):
        ui.add(1, 10 * random.random(), random.random())

    print '%.3f %.3f' % ui.merge()

    


