#!/usr/bin/env cctbx.python
# MultiMerger.py
# 
#   Copyright (C) 2010 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# A playpen for figuring out merging multi-crystal merging... start by
# figuring out a way of comparing the indexing, then by adding together the
# lists of reindexed observations. Then can compare the other data sets
# with this accumulation of measurements to see how well the named data set
# agrees.

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

class multi_merger:
    '''A class to mediate merging of multiple reflection files from putatively
    isomorphous structures. This will include list of possible reindexing
    operations which could be needed. N.B. these could one day be generated
    internally.'''

    def __init__(self, hklin_list, reindex_op_list):
        '''Copy in list of reflection files, alternate indexing options.'''
        
        self._hklin_list = hklin_list
        self._reindex_op_list = ['h,k,l']
        self._reindex_op_list.extend(reindex_op_list)

        # N.B. will need to verify that the reindexing operations are
        # not spacegroup / pointgroup symmetry operations.

        self._merger_list = []

        self.setup()
        
        return

    def get_mergers(self):
        return self._merger_list

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

            m_work.reload()
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

        best_reindex = ccs[-1][1]

        m_work.reload()
        m_work.reindex(best_reindex)

        return best_reindex

    def unify_indexing(self):
        '''Unify the indexing conventions, to the first reflection file.'''

        for j in range(1, len(self._merger_list)):
            reindex = self.decide_correct_indexing(j)

            print 'File (%s): %s' % (self._hklin_list[j], reindex)

        return
    
if __name__ == '__main__':

    hklin_list = ['R1.mtz', 'R2.mtz', 'R3.mtz', 'R4.mtz']
    reindex_op_list = ['-k,h,l']

    mm = multi_merger(hklin_list, reindex_op_list)

    mm.unify_indexing()

    mergers = mm.get_mergers()

    m = mergers[0]

    print '%.3f %.2f' % (m.calculate_completeness(),
                         m.calculate_multiplicity())

    for j in range(1, len(mergers)):
        m.accumulate(mergers[j])
        print '%.3f %.2f' % (m.calculate_completeness(),
                             m.calculate_multiplicity())
        
