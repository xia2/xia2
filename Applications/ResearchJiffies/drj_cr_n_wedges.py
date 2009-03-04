import math
import sys

def meansd(values):
    mean = sum(values) / len(values)
    var = sum([(v - mean) * (v - mean) for v in values]) / len(values)
    return mean, math.sqrt(var)

def gather(files):
    data = { }

    for j in range(10):
        data[j + 1] = []

    for f in files:
        records = open(f, 'r').readlines()
        if not len(records) == 10:
            continue

        for r in records:
            s = r.split()
            n = int(s[0])
            m = float(s[1])

            data[n].append(m)

    for j in range(0, 10):
        positive_data = []
        for d in data[j + 1]:
            if d > 0:
                positive_data.append(d)
        m, s = meansd(positive_data)

        print '%d %.3f %.3f' % (j + 1, m, s)

    print '%d points' % len(data[2])

if __name__ == '__main__':
    gather(sys.argv[1:])
            
