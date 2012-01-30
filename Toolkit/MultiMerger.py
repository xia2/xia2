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
from KBScale import lkb_scale

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

    def r(self, file_no):
        '''Compute the residual between related data sets.'''

        assert(file_no > 0)

        m_ref = self._merger_list[0]
        m_work = self._merger_list[file_no]

        r_ref = m_ref.get_merged_reflections()
        r_work = m_work.get_merged_reflections()

        ref = []
        work = []

        r = 0.0
        d = 0.0

        for hkl in r_ref:
            if hkl in r_work:
                r += math.fabs(r_ref[hkl][0] - r_work[hkl][0])
                d += math.fabs(r_ref[hkl][0])

        return r / d

    def r_ext(self, j, ext):
        '''Compute the residual between related data sets, given from an
        external source.'''

        assert(j < len(self._merger_list))

        m_ref = self._merger_list[j]

        r_ref = m_ref.get_merged_reflections()
        r_work = ext.get_merged_reflections()

        ref = []
        work = []

        r = 0.0
        d = 0.0

        for hkl in r_ref:
            if hkl in r_work:
                r += math.fabs(r_ref[hkl][0] - r_work[hkl][0])
                d += math.fabs(r_ref[hkl][0])

        return r / d

    def scale(self, file_no, reference = None):
        '''Scale the measurements in file number j to the reference, here
        defined to be the first one. N.B. assumes that the indexing is
        already consistent.'''

        if not reference:
            assert(file_no > 0)

        if reference:
            m_ref = reference
        else:
            m_ref = self._merger_list[0]

        m_work = self._merger_list[file_no]

        r_ref = m_ref.get_merged_reflections()
        r_work = m_work.get_merged_reflections()

        ref = []
        work = []

        for hkl in r_ref:
            if hkl in r_work:

                if r_ref[hkl][0] / r_ref[hkl][1] < 1:
                    continue

                if r_work[hkl][0] / r_work[hkl][1] < 1:
                    continue

                d = m_work.resolution(hkl)
                s = 1.0 / (d * d)
                ref.append((s, r_ref[hkl][0]))
                work.append((s, r_work[hkl][0]))

        k, b = lkb_scale(ref, work)

        m_work.apply_kb(k, b)

        return k, b

    def unify_indexing(self):
        '''Unify the indexing conventions, to the first reflection file.'''

        for j in range(1, len(self._merger_list)):
            reindex = self.decide_correct_indexing(j)

            # print 'File %s: %s' % (self._hklin_list[j], reindex)

        return

    def scale_all(self, reference = None):
        '''Place all measurements on a common scale using kB scaling.'''

        if reference:
            start = 0
        else:
            start = 1

        for j in range(start, len(self._merger_list)):
            k, b = self.scale(j, reference = reference)

            # print 'File %s: %.2f %.2f' % (self._hklin_list[j], k, b)

        return

    def assign_resolution_unmerged_isigma(self, limit = 1.0):
        '''Assign a resolution limit based on unmerged I/sigma to all
        mergers.'''

        mergers = self.get_mergers()

        for m in mergers:
            m.calculate_resolution_ranges(nbins = 100)
            r = m.resolution_unmerged_isigma(limit = limit)
            m.apply_resolution_limit(r)

        return

if __name__ == '__main__':

    hklin_list = sys.argv[1:]
    reindex_op_list = ['-k,h,l']

    mm = multi_merger(hklin_list, reindex_op_list)
    mm.assign_resolution_unmerged_isigma(limit = 1.0)
    mm.unify_indexing()
    mm.scale_all()

    print 'Internal R factors within scaled data sets'

    for j in range(1, len(hklin_list)):
        print '%d %.2f' % (j, mm.r(j))

    mergers = mm.get_mergers()
    m = mergers[0]

    print 'Accumulating full reference data set'

    print '%.3f %.2f %.2f' % (m.calculate_completeness(),
                              m.calculate_multiplicity(),
                              m.calculate_rmerge())

    for j in range(1, len(mergers)):
        m.accumulate(mergers[j])
        print '%.3f %.2f %.2f' % (m.calculate_completeness(),
                                  m.calculate_multiplicity(),
                                  m.calculate_rmerge())

    print 'Rescaling individual data sets to match full reference'

    mm = multi_merger(hklin_list, reindex_op_list)

    mm.assign_resolution_unmerged_isigma(limit = 1.0)
    mm.unify_indexing()
    mm.scale_all(reference = m)

    print 'R factor between individual data sets and the full set'

    r_list = []

    for j in range(len(hklin_list)):
        r = mm.r_ext(j, m)
        print '%d %.3f' % (j, r)
        r_list.append((r, hklin_list[j]))

    r_list.sort()

    print 'Final level of agreement list'

    for r_f in r_list:

        m = merger(r_f[1])
        m.calculate_resolution_ranges(nbins = 100)
        r = m.resolution_unmerged_isigma(limit = 1.0)
        m.apply_resolution_limit(r)

        print '%.3f %s %.3f %.3f' % (r_f[0], r_f[1],
                                     m.calculate_completeness(),
                                     m.calculate_rmerge())

    hklin_list = sys.argv[1:]
    reindex_op_list = ['-k,h,l']

    print 'Now look at things in a pairwise manner'

    r_matrix = { }

    for j in range(len(hklin_list)):
        for k in range(j, len(hklin_list)):
            l = [hklin_list[j], hklin_list[k]]

            if j != k:
                pmm = multi_merger(l, reindex_op_list)

                pmm.assign_resolution_unmerged_isigma(limit = 1.0)
                pmm.unify_indexing()
                pmm.scale_all()

                r = pmm.r(1)

            else:
                r = 0

            print '%2d %2d %.3f' % (j, k, r)
            r_matrix[(j, k)] = r
            r_matrix[(k, j)] = r

    # now accumulate the columns / rows

    totals = { }

    for j in range(len(hklin_list)):
        totals[j] = sum([r_matrix[(j, k)] for k in range(len(hklin_list))])

    scale = len(hklin_list) - 1

    for j in range(len(hklin_list)):
        print '%s %.2f' % (hklin_list[j], totals[j] / scale)

    p_list = [(totals[j], hklin_list[j]) for j in range(len(hklin_list))]
    p_list.sort()

    sorted_ar = [r[1] for r in r_list]
    sorted_pr = [p[1] for p in p_list]

    print 'AR PR hklin'
    for h in hklin_list:
        print '%2d %2d %s' % (sorted_ar.index(h), sorted_pr.index(h), h)
