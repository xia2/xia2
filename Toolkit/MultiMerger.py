#!/usr/bin/env cctbx.python
# MultiMerger.py
# 
#   Copyright (C) 2010 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# A playpen for figuring out merging multi-crystal merging...

import sys
import math
import os
import time
import copy

from Merger import merger

def correlation_coefficient(a, b):
    '''Calculate the correlation coefficient between values a and b.'''
    
    ma = sum(a) / len(a)
    mb = sum(b) / len(b)

    da = [_a - ma for _a in a]
    db = [_b - mb for _b in b]

    sab = sum([_da * _db for _da, _db in zip(da, db)])
    saa = math.sqrt(sum([_da * _da for _da in da]))
    sbb = math.sqrt(sum([_db * _db for _db in db]))

    return sab / (saa * sbb)

class MultiMerger:
    '''A class to mediate merging of multiple reflection files from putatively
    isomorphous structures. This will include list of possible reindexing
    operations which could be needed. N.B. these could one day be generated
    internally.'''

    def __init__(self, hklin_list, reindex_op_list):
        '''Set up stuff!'''
        
        self._hklin_list = hklin_list
        self._reindex_op_list = ['h,k,l'].extend(reindex_op_list)

        # N.B. will need to verify that the reindexing operations are
        # not spacegroup / pointgroup symmetry operations.

        self._merger_list = []

        self.setup()
        
        return

    def setup(self):
        '''Load in all of the reflection files and so on.'''

        for hklin in self._hklin_list:
            m = merger(hklin)
            m.reindex('h,k,l')
            self._merger_list.append(m)

        return

    def decide_correct_indexing(self, file_no):
        '''For a given reflection file number, decide the correct indexing
        convention, and reindex to this. Correct indexing is defined to
        be the indexing which gives the correlation coefficient.'''

        assert(file_no > 0)
        
        m_ref = self._merger_list[0]
        m_work = self._merger_list[file_no]

        ccs = []

        for reindex_op in self._reindex_op_list:

            m_work.reindex(reindex_op)

            r_ref = m_ref.get_merged_reflections()
            r_work = m_work.get_merged_reflections()

            ref = []
            work = []

            for hkl in r_ref:
                if hkl in r_work:
                    ref.append(r_ref[hkl][0])
                    work.append(r_work[hkl][0])

            cc = correlation_coefficient(ref, work)

            ccs.append((cc, reindex_op))

        ccs.sort()

        

        return

    def unify_indexing(self):
        '''Unify the indexing conventions, to the first reflection file.'''

        return
    
        

    


m1 = merger('R1.mtz')
m2 = merger('R2.mtz')
m3 = merger('R3.mtz')
m4 = merger('R4.mtz')

# ensure consistent ASU
m1.reindex('h,k,l')
m2.reindex('h,k,l')
m3.reindex('h,k,l')
m4.reindex('h,k,l')

r1 = m1.get_merged_reflections()

print '1, 2'

r2 = m2.get_merged_reflections()

c1 = []
c2 = []

for hkl in r1:
    if hkl in r2:
        c1.append(r1[hkl][0])
        c2.append(r2[hkl][0])

print correlation_coefficient(c1, c2)
print len(c1)

print '1, 3'

r3 = m3.get_merged_reflections()

c1 = []
c3 = []

for hkl in r1:
    if hkl in r3:
        c1.append(r1[hkl][0])
        c3.append(r3[hkl][0])

print correlation_coefficient(c1, c3)
print len(c1)

print '1, 4'

r4 = m4.get_merged_reflections()

c1 = []
c4 = []

for hkl in r1:
    if hkl in r4:
        c1.append(r1[hkl][0])
        c4.append(r4[hkl][0])

print correlation_coefficient(c1, c4)
print len(c1)

print '1, 4R'

m4.reindex('-k,h,l')

r4 = m4.get_merged_reflections()

c1 = []
c4 = []

for hkl in r1:
    if hkl in r4:
        c1.append(r1[hkl][0])
        c4.append(r4[hkl][0])

print correlation_coefficient(c1, c4)
print len(c1)

