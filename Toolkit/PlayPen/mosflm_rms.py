import os
import sys
import math

def meansd(values):
    mean = sum(values) / len(values)
    var = sum([(v - mean) * (v - mean) for v in values]) / len(values)
    return mean, math.sqrt(var)

def get_mosflm_rmsd(records):
    rmsd = { }
    current_image = None

    for record in records:
        if 'Processing Image' in record:
            current_image = int(record.split()[2])

        if 'Rms Resid' in record:
            rmsd[current_image] = float(record.split()[-2])

    return rmsd

def compare(run_a, run_b):
    '''A / B.'''

    rmsd_a = get_mosflm_rmsd(open(run_a).readlines())
    rmsd_b = get_mosflm_rmsd(open(run_b).readlines())

    assert(sorted(rmsd_a) == sorted(rmsd_b))

    ratios = []

    for image in sorted(rmsd_a):
        ratios.append(rmsd_a[image] / rmsd_b[image])

    m, s = meansd(ratios)

    return m, s, (m - 1.0) / s

if __name__ == '__main__':

    print '%.3f %.3f %.3f' % compare(sys.argv[1], sys.argv[2])
