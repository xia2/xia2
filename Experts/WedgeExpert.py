#!/usr/bin/env python
# WedgeExpert.py
# 
#   Copyright (C) 2009 STFC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
# 
# Some code to help figure out how the experiment was performed and tell
# Chef where we could consider cutting the data at...
# 

import math
import sys

dose_batch = { }
batch_dose = { }

for record in open(sys.argv[1], 'r').readlines():
    tokens = record.split()
    if not tokens:
        continue

    batch = int(tokens[1])
    dose = float(tokens[3])

    dose_batch[dose] = batch
    batch_dose[batch] = dose

# now try to understand this...

doses = sorted(dose_batch.keys())

is_monotonic = True

b0 = dose_batch[doses[0]]

start_batches = [b0]
current = b0
length_wedge = {b0:1}

for d in doses[1:]:
    if dose_batch[d] < b0:
        current = dose_batch[d]
        start_batches.append(current)
        length_wedge[current] = 0
        is_monotonic = False

    if dose_batch[d] > (b0 + 1):
        current = dose_batch[d]
        start_batches.append(current)
        length_wedge[current] = 0

    b0 = dose_batch[d]
    length_wedge[current] += 1

# print is_monotonic

start_batches.sort()

for batch in start_batches:
    exposure = batch_dose[batch + 1] - batch_dose[batch]
    print '%d %d %.1f %.1f' % (batch, length_wedge[batch],
                               exposure, batch_dose[batch])

# ok so so far we have a good understanding of the structure of the
# wedges - next need to chase down the pairing of the wedges, and define
# some rules for this...

# (i) assert: multiple wavelengths, same phi range => paired wedges
# (ii) assert: inverse beam measurements, phi + 180 => paired wedges
# (iii) assume want complete pairs

# ok, to do this will need wavelength information, phi start, phi offset,
# dose and batch stuff. so, ideally work from the contents of the cheffy
# MTZ files via MTZdump, or cctbx code to do same. c/f autochef module.
