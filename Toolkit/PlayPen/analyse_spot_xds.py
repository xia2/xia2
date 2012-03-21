# Read SPOT.XDS; look for blank images.

import sys
import math

from libtbx import cluster

def do_cluster(values):
    mean = sum(values) / len(values)
    
    hc = cluster.HierarchicalClustering(
        values, lambda x, y: float(abs(x - y)),
        'average')
    
    return hc.getlevel(mean)

def clusters_i(spot_xds):

    i_values = []
    
    for record in open(spot_xds):
        values = map(float, record.split())
        if not values:
            continue
        i = values[3]

        i_values.append(i)

    return do_cluster(i_values[:200])

def values_to_z(values):
    zs = []
    
    for j in range(len(values)):
        others = values[:j] + values[j + 1:]
        mean = sum(others) / len(others)
        sd = math.sqrt(sum([(o - mean) * (o - mean) for o in others]) /
                       len(others))
        zs.append((values[j] - mean) / sd)
        
    return zs

def read_spot_xds(spot_xds):

    # this is sorted on I, want to consider throwing away unusually strong
    # outlier types. Can do that by clustering strongest few reflections,
    # limit as mean.

    ivalues = []
    jvalues = []
    
    for record in open(spot_xds):
        values = map(float, record.split())
        if not values:
            continue
        j = int(round(values[2]))
        i = values[3]

        ivalues.append(i)
        jvalues.append(j)

    # decide if we want to throw some away? look at nframe / 2 values

    nframe = (max(jvalues) - min(jvalues) + 1) // 2
    clusters = do_cluster(ivalues[:nframe])

    if len(clusters) == 1:
        ignore = 0
    else:
        ignore = len(clusters[0])
    
    results = { }

    for i, j in zip(ivalues, jvalues)[ignore:]:
        if not j in results:
            results[j] = [ ]

        results[j].append(i)

    averages = { }

    for j in results:
        averages[j] = sum(results[j]) / len(results[j])

    return averages

def get_signal(spot_xds):
    averages = read_spot_xds(spot_xds)
    signal = [averages.get(j, 0.0) for j in range(1, len(averages))]
    return min(signal), max(signal)

if __name__ == '__main__':
    print '%.2f %.2f' % get_signal(sys.argv[1])
