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
#
# FIXME separate out hkl for centric and acentric reflections. The code for
#       this is I think in PyChef for the completeness calculation:
# 
#             sg = mtz_obj.space_group()
#             if sg.is_centric((h, k, l)) &c.
# 
# FIXME should also include a completeness calculation in here for all of the
#       resolution shells:
# 
# def compute_unique_reflections(unit_cell,
#                                space_group,
#                                anomalous,
#                                high_resolution_limit,
#                                low_resolution_limit = None):
#     '''Compute the list of unique reflections from the unit cell and space
#     group.'''
# 
#     cs = crystal_symmetry(unit_cell = unit_cell,
#                           space_group = space_group)
# 
#     return [hkl for hkl in build_set(cs, anomalous,
#                                      d_min = high_resolution_limit,
#                                      d_max = low_resolution_limit).indices()]
#
# FIXME restructure this (or extend) to include the Chef calculations =>
#       can then apply these to any derived data types.
#
# FIXME add capability to read in XDS (G)XPARM file as well as e.g. INTEGRATE
#       HKL format file (or pointless equivalent, if possible) to compute
#       LP corrections. This will allow XDS INTEGRATE -> Scala to be performed
#       correctly. N.B. will be useful to add extra column for LP correction
#       values. N.B. INTEGRATE applies an LP correction assuming that the
#       fraction is 0.5 - this is improved by CORRECT. Pointless copies this
#       across correctly and computes LP column. 


import sys
import math
import os
import time
import itertools

from iotbx import mtz

from MtzFactory import mtz_file

class unmerged_intensity:
    '''A class to represent and encapsulate the multiple observations of a
    given intensity defined in terms of the Miller index. It is assumed that
    these are compatible observations.'''

    def __init__(self):
        self._observations = []

        return

    def add(self, misym, i, sigi, b):
        self._observations.append((misym, i, sigi, b))
        return

    def get(self):
        return self._observations

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

    def merge_anomalous(self):
        '''Merge the observations recorded so far, return Imean+, SigImean+
        &c. N.B. will return a 4-ple. +/- defined by M_ISYM record, which
        if odd = I+, even I-.'''

        assert(self._observations)

        sum_wi_p = 0.0
        sum_w_p = 0.0
        
        sum_wi_m = 0.0
        sum_w_m = 0.0

        for o in self._observations:
            i = o[1]
            w = 1.0 / (o[2] * o[2])
            if o[0] % 2:
                sum_w_p += w
                sum_wi_p += w * i
            else:
                sum_w_m += w
                sum_wi_m += w * i
                
        if sum_w_p:
            i_mean_p = sum_wi_p / sum_w_p
            sigi_mean_p = math.sqrt(1.0 / sum_w_p)
        else:
            i_mean_p = 0.0
            sigi_mean_p = 0.0

        if sum_w_m:
            i_mean_m = sum_wi_m / sum_w_m
            sigi_mean_m = math.sqrt(1.0 / sum_w_m)
        else:
            i_mean_m = 0.0 
            sigi_mean_m = 0.0        

        return i_mean_p, sigi_mean_p, i_mean_m, sigi_mean_m

    def multiplicity(self):
        return len(self._observations)

    def multiplicity_anomalous(self):
        def p(x): return x[0] % 2
        def m(x): return not x[0] % 2
        return len(filter(p, self._observations)), \
               len(filter(m, self._observations))

    def rmerge_contribution(self, i_mean):
        '''Calculate the contribution of this reflection to Rmerge.'''

        return sum([math.fabs(o[1] - i_mean) for o in self._observations])

    def rmerge_contribution_anomalous(self, i_mean_p, i_mean_m):
        '''Calculate the contribution of this reflection to Rmerge,
        separating anomalous pairs. Returns contributions for I+, I-.'''

        rmerge_p = 0.0
        rmerge_m = 0.0

        for o in self._observations:
            if o[0] % 2:
                rmerge_p += math.fabs(o[1] - i_mean_p)
            else:
                rmerge_m += math.fabs(o[1] - i_mean_m)
                
        return rmerge_p, rmerge_m

    def isigma_contribution(self):
        '''Calculate the contribution to the I/sigma. N.B. multiplicity!'''
        return sum(o[1] / o[2] for o in self._observations)

    def chisq_contribution(self, i_mean):
        '''Calculate the contribution to the reduced chi^2.'''
        
        return [(o[1] - i_mean) / o[2] for o in self._observations]

    def calculate_unmerged_di(self):
        '''Calculate unmerged dI values, returns a list of putative unmerged
        observations in same structure, though misym is replaced with dose
        difference...'''

        def isp(x): return x[0] % 2
        def ism(x): return not x[0] % 2

        i_p = filter(isp, self._observations)
        i_m = filter(ism, self._observations)

        dis = sorted([(math.fabs(m[3] - p[3]), ip, im) \
                      for ip, p in enumerate(i_p) \
                      for im, m in enumerate(i_m)])

        ip_used = []
        im_used = []

        result = unmerged_intensity()

        for d, ip, im in dis:
            if ip in ip_used:
                continue
            if im in im_used:
                continue

            ip_used.append(ip)
            im_used.append(im)

            # calculate intensity difference ...

            _ip = i_p[ip]
            _im = i_m[im]

            _i = _ip[1] - _im[1]
            _si = math.sqrt(_ip[2] * _ip[2] + _im[2] * _im[2])
            _b = 0.5 * (_ip[3] + _im[3])

            result.add(d, _i, _si, _b)

        return result
            
class merger:
    '''A class to calculate things from merging reflections.'''

    def __init__(self, hklin):
        self._mf = mtz_file(hklin)
        self._unmerged_reflections = { }
        self._merged_reflections = { }
        self._merged_reflections_anomalous = { }
        self._unmerged_di = { }

        all_columns = self._mf.get_column_names()

        assert('M_ISYM' in all_columns)
        assert('I' in all_columns)
        assert('SIGI' in all_columns)

        if 'DOSE' in all_columns and False:
            self._b_column = 'DOSE'
        elif 'BATCH' in all_columns:
            self._b_column = 'BATCH'
        else:
            raise RuntimeError, 'no baseline column (DOSE or BATCH) found'

        self._read_unmerged_reflections()
        self._merge_reflections()
        self._merge_reflections_anomalous()

        if True:
            return

        t0 = time.time()
        self._calculate_unmerged_di()
        print 'Unmerged dI calculation: %.2fs' % (time.time() - t0)

        diff = []

        for hkl in self._unmerged_di:
            [diff.append(o[0]) for o in self._unmerged_di[hkl].get()]

        mean = sum(diff) / len(diff)
        var = sum([(d - mean) * (d - mean) for d in diff]) / len(diff)

        print mean, math.sqrt(var)
    
        return

    def _read_unmerged_reflections(self):
        '''Actually read the reflections in to memory.'''

        mi = self._mf.get_miller_indices()
        m_isym = self._mf.get_column_values('M_ISYM')
        i = self._mf.get_column_values('I')
        sigi = self._mf.get_column_values('SIGI')
        b = self._mf.get_column_values(self._b_column)
        
        for j in range(len(i)):
            hkl = mi[j]
            if not hkl in self._unmerged_reflections:
                self._unmerged_reflections[hkl] = unmerged_intensity()
            self._unmerged_reflections[hkl].add(
                m_isym[j], i[j], sigi[j], b[j])

        return

    def _merge_reflections(self):
        '''Merge the currently recorded unmerged reflections.'''

        for hkl in self._unmerged_reflections:
            self._merged_reflections[hkl] = self._unmerged_reflections[
                hkl].merge()

        return

    def _merge_reflections(self):
        '''Merge the currently recorded unmerged reflections.'''

        for hkl in self._unmerged_reflections:
            self._merged_reflections[hkl] = self._unmerged_reflections[
                hkl].merge()

        return

    def _merge_reflections_anomalous(self):
        '''Merge the currently recorded unmerged reflections.'''

        for hkl in self._unmerged_reflections:
            self._merged_reflections_anomalous[
                hkl] = self._unmerged_reflections[hkl].merge_anomalous()

        return

    def _calculate_unmerged_di(self):
        '''Calculate a set of unmerged intensity differences.'''

        for hkl in self._unmerged_reflections:
            self._unmerged_di[hkl] = self._unmerged_reflections[
                hkl].calculate_unmerged_di()

        return

    def calculate_resolution_ranges(self, nbins = 20):
        '''Calculate semi-useful resolution ranges for analysis.'''

        miller_indices = list(self._merged_reflections)
        uc = self._mf.get_unit_cell()

        d_mi = []

        for mi in miller_indices:
            d = uc.d(mi)
            d_mi.append((d, mi))

        d_mi.sort()

        chunk_size = int(round(float(len(d_mi)) / nbins))

        hkl_ranges = []
        resolution_ranges = []

        for chunk in [d_mi[i:i + chunk_size] \
                      for i in range(0, len(d_mi), chunk_size)]:
            mi = [c[1] for c in chunk]
            d = [c[0] for c in chunk]
            hkl_ranges.append(mi)
            resolution_ranges.append((min(d), max(d)))

        # stitch together the two low res bins

        self._hkl_ranges = hkl_ranges[:-1]
        for mi in hkl_ranges[-1]:
            self._hkl_ranges[-1].append(mi)
            
        self._resolution_ranges = resolution_ranges[:-1]
        self._resolution_ranges[-1] = (self._resolution_ranges[-1][0],
                                       resolution_ranges[-1][1])
        
        return

    def get_resolution_bins(self):
        return self._hkl_ranges, self._resolution_ranges

    def calculate_rmerge(self, hkl_list = None):
        '''Calculate the overall Rmerge.'''

        t = 0.0
        b = 0.0

        if not hkl_list:
            hkl_list = list(self._unmerged_reflections)
        
        for hkl in hkl_list:
            i_mean = self._merged_reflections[hkl][0]
            t += self._unmerged_reflections[hkl].rmerge_contribution(i_mean)
            b += self._unmerged_reflections[hkl].multiplicity() * i_mean

        return t / b

    def calculate_rmerge_anomalous(self, hkl_list = None):
        '''Calculate the overall Rmerge, separating anomalous pairs.'''

        t = 0.0
        b = 0.0

        if not hkl_list:
            hkl_list = list(self._unmerged_reflections)
        
        for hkl in hkl_list:
            is_pm = self._merged_reflections_anomalous[hkl]
            i_mean_p, i_mean_m = is_pm[0], is_pm[2]
            r_pm = self._unmerged_reflections[
                hkl].rmerge_contribution_anomalous(i_mean_p, i_mean_m)
            t += r_pm[0] + r_pm[1]
            multiplicity_pm = self._unmerged_reflections[
                hkl].multiplicity_anomalous()
            b += multiplicity_pm[0] * i_mean_p + multiplicity_pm[1] * i_mean_m

        return t / b

    def calculate_chisq(self, hkl_list = None):
        '''Calculate the overall erzatz chi^2.'''

        if not hkl_list:
            hkl_list = list(self._unmerged_reflections)

        deltas = []
        
        for hkl in hkl_list:
            i_mean = self._merged_reflections[hkl][0]
            for d in self._unmerged_reflections[hkl].chisq_contribution(
                i_mean):
                deltas.append(d)

        mean = sum(deltas) / len(deltas)
        var = sum([(d - mean) * (d - mean) for d in deltas]) / len(deltas)

        return mean, math.sqrt(var)

    def calculate_multiplicity(self, hkl_list = None):
        '''Calculate the overall average multiplicity.'''
        
        if not hkl_list:
            hkl_list = list(self._unmerged_reflections)

        multiplicity = [float(self._unmerged_reflections[hkl].multiplicity()) \
                        for hkl in hkl_list]
        
        return sum(multiplicity) / len(multiplicity)

    def calculate_completeness(self, hkl_list = None):
        '''Calculate the completeness of measurements in this resolution
        range.'''

        raise RuntimeError, 'FIXME implement this'

    def calculate_merged_isigma(self, hkl_list = None):
        '''Calculate the average merged I/sigma.'''

        if not hkl_list:
            hkl_list = list(self._unmerged_reflections)

        isigma_values = [self._merged_reflections[hkl][0] / \
                         self._merged_reflections[hkl][1] \
                         for hkl in hkl_list]

        return sum(isigma_values) / len(isigma_values)

    def calculate_unmerged_isigma(self, hkl_list = None):
        '''Calculate the average unmerged I/sigma.'''

        if not hkl_list:
            hkl_list = list(self._unmerged_reflections)

        return sum([self._unmerged_reflections[hkl].isigma_contribution() \
                    for hkl in hkl_list]) / \
                    sum([self._unmerged_reflections[hkl].multiplicity() \
                         for hkl in hkl_list])

    def calculate_z2(self, hkl_list = None):
        '''Calculate average Z^2 values, where Z = I/<I> in the bin,
        from the merged observations. Now also separate centric and
        acentric reflections.'''

        if not hkl_list:
            hkl_list = list(self._merged_reflections)

        # separate centric and acentric reflections

        sg = self._mf.get_space_group()

        hkl_centric = [hkl for hkl in
                       itertools.ifilter(sg.is_centric, hkl_list)]
        hkl_acentric = [hkl for hkl in
                        itertools.ifilterfalse(sg.is_centric, hkl_list)]

        i_s = [self._merged_reflections[hkl][0] for hkl in hkl_centric]
        mean_i = sum(i_s) / len(i_s)
        
        z_s = [i / mean_i for i in i_s]
        z_centric = sum([z * z for z in z_s]) / len(z_s)

        i_s = [self._merged_reflections[hkl][0] for hkl in hkl_acentric]
        mean_i = sum(i_s) / len(i_s)
        
        z_s = [i / mean_i for i in i_s]
        z_acentric = sum([z * z for z in z_s]) / len(z_s)

        return z_centric, z_acentric

if __name__ == '__main__':

    nbins = 20

    m = merger(sys.argv[1])

    if len(sys.argv) > 2:
        nbins = int(sys.argv[2])

    print 'Overall'
    t0 = time.time()
    print 'Rmerge:       %6.3f' % m.calculate_rmerge()
    t1 = time.time()
    print 'Rmerge +/-:   %6.3f' % m.calculate_rmerge_anomalous()
    t2 = time.time()
    print 'Multiplicity: %6.3f' % m.calculate_multiplicity()
    print 'Mn(I/sigma):  %6.3f' % m.calculate_merged_isigma()
    print 'I/sigma:      %6.3f' % m.calculate_unmerged_isigma()
    print 'Z^2:          %6.3f %6.3f' % m.calculate_z2()
    print 'Chi^2:        %6.3f %6.3f' % m.calculate_chisq()
    
    m.calculate_resolution_ranges(nbins = nbins)

    bins, ranges = m.get_resolution_bins()

    print 'By resolution shell'
    print '%6s %6s %6s %6s %6s %6s %6s %6s %6s %6s %6s' % \
          ('Low', 'High', 'N', 'Rmerge', 'Mult',
           'M(I/s)', 'I/s', 'cZ^2', 'aZ^2', 'Chi^2', 'Chi^2')
    
    for j, bin in enumerate(bins):
        dmin, dmax = ranges[j]
        n = len(bin)
        rmerge = m.calculate_rmerge(bin)
        mult = m.calculate_multiplicity(bin)
        misigma = m.calculate_merged_isigma(bin)
        isigma = m.calculate_unmerged_isigma(bin)
        z2 = m.calculate_z2(bin)
        chisq = m.calculate_chisq(bin)

        print '%6.3f %6.3f %6d %6.3f %6.3f %6.3f %6.3f %6.3f %6.3f %6.3f %6.3f' % \
              (dmin, dmax, n, rmerge, mult, misigma,
               isigma, z2[0], z2[1], chisq[0], chisq[1])
        
    print 'Rmerge times: %.4fs vs. %4fs' % (t1 - t0, t2 - t1)
