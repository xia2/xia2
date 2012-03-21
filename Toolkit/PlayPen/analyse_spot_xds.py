# Read SPOT.XDS; look for blank images.

import sys
import math        

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
    results = { }

    for record in open(spot_xds):
        values = map(float, record.split())
        if not values:
            continue
        j = int(round(values[2]))
        i = values[3]

        if not j in results:
            results[j] = [ ]

        results[j].append(i)

    averages = { }
    zmaxs = { }

    for j in results:
        averages[j] = sum(results[j]) / len(results[j])
        zmaxs[j] = max(values_to_z(results[j]))

    return averages, zmaxs

if __name__ == '__main__':
    averages, zmaxs = read_spot_xds(sys.argv[1])

    m = max(averages) + 1

    for j in range(m):
        print '%4d %.2f %.2f' % (j, averages.get(j, 0.0), zmaxs.get(j, 0.0))

    
