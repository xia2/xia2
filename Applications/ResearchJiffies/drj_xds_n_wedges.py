import math
import sys

def meansd(values):
    mean = sum(values) / len(values)
    var = sum([(v - mean) * (v - mean) for v in values]) / len(values)
    return mean, math.sqrt(var)

def gather(files):
    data = { }

    for j in range(11):
        data[j] = []

    for f in files:
        records = open(f, 'r').readlines()
        if not len(records) == 11:
            continue

        for r in records:
            s = r.split()
            n = int(s[0])
            m = float(s[1])

            data[n].append(m)

    for j in range(0, 11):
        m, s = meansd(data[j])

        print '%d %.3f %.3f' % (j, m, s)

    print '%d points' % len(data[2])

if __name__ == '__main__':
    gather(sys.argv[1:])
            
