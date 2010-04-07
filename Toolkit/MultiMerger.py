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
import itertools
import copy

from Merger import merger

def correlation_coefficient(a, b):
    ma = sum(a) / len(a)
    mb = sum(b) / len(b)

    da = [_a - ma for _a in a]
    db = [_b - mb for _b in b]

    sab = sum([_da * _db for _da, _db in zip(da, db)])
    saa = math.sqrt(sum([_da * _da for _da in da]))
    sbb = math.sqrt(sum([_db * _db for _db in db]))

    return sab / (saa * sbb)

m1 = merger('R1.mtz')
m2 = merger('R2.mtz')
m3 = merger('R3.mtz')
m4 = merger('R4R.mtz')

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

