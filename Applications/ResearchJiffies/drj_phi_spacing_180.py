import math
import sys

def meansd(values):

    if len(values) == 0:
        return 0.0, 0.0
    if len(values) == 1:
        return values[0], 0.0
    
    mean = sum(values) / len(values)
    var = sum([(v - mean) * (v - mean) for v in values]) / len(values)
    
    return mean, math.sqrt(var)

def nint(a):
    i = int(a)
    if a - i > 0.5:
        i += 1
    return i

def gather(files):
    data = { }

    for j in range(90):
        data[j + 1] = []

    for f in files:
        records = open(f, 'r').readlines()
        if not len(records) == 85:
            continue

        for r in records:
            s = r.split()
            n = nint(float(s[0]))
            m = float(s[1])

            data[n].append(m)

    for j in range(90):
        m, s = meansd(data[j + 1])

        print '%d %.3f %.3f' % (j + 1, m, s)

    print '%d points' % len(data[6])

if __name__ == '__main__':
    gather(sys.argv[1:])
            
