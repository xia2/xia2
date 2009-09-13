import math
import sys

isig = { }
lines = open(sys.argv[1]).readlines()

totals_h = { }
totals_k = { }
totals_l = { }

for offset in 0, 1, 2, 3, 4, 6:
    totals_h[offset] = []
    totals_k[offset] = []
    totals_l[offset] = []

def digest(values):
    hs = sorted(values)

    totals = { }
    counts = { }

    for offset in 0, 1, 2, 3, 4, 6:
        totals[offset] = 0
        counts[offset] = 0
        for j in hs:
            if j + offset in hs:
                totals[offset] += values[j] * values[j + offset]
                counts[offset] += 1
                
    t0 = totals[0] / counts[0]
    for offset in 0, 1, 2, 3, 4, 6:
        if counts[offset]:
            temp = totals[offset] / counts[offset]
        else:
            temp = 0
        totals[offset] = temp / t0

    return totals
    
for j, record in enumerate(lines):
    if '$TABLE: Axial reflections, axis ' in record:
        axis = record.split()[4].replace(',', '')
        dataset = record.split()[5]
        isig = { }
        k = j + 6

        while not '$$' in lines[k]:
            values = lines[k].split()
            h = int(values[0])
            i = float(values[-1])
            isig[h] = i
            k += 1

        totals = digest(isig)

        # print axis, dataset

        for offset in [0, 1, 2, 3, 4, 6]:
            if axis == 'h':
                totals_h[offset].append(totals[offset])
            elif axis == 'k':
                totals_k[offset].append(totals[offset])
            elif axis == 'l':
                totals_l[offset].append(totals[offset])
                
            # print '%d %.4f' % (offset, totals[offset])
            
if totals_h[0]:
    print '(h, 0, 0) axial reflections'
    for offset in [0, 1, 2, 3, 4, 6]:
        totals = totals_h[offset]
        print '%d %7.4f' % (offset, sum(totals) / len(totals))

if totals_k[0]:
    print '(0, k, 0) axial reflections'
    for offset in [0, 1, 2, 3, 4, 6]:
        totals = totals_k[offset]
        print '%d %7.4f' % (offset, sum(totals) / len(totals))

if totals_l[0]:
    print '(0, 0, l) axial reflections'
    for offset in [0, 1, 2, 3, 4, 6]:
        totals = totals_l[offset]
        print '%d %7.4f' % (offset, sum(totals) / len(totals))
    

    
