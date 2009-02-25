import math
import sys

def meansd(values):
    mean = sum(values) / len(values)
    var = sum([(v - mean) * (v - mean) for v in values]) / len(values)
    return mean, math.sqrt(var)

def gather(files):
    data = { }
    time = { }

    for j in range(15):
        data[j + 1] = []
        time[j + 1] = []

    for f in files:
        records = open(f, 'r').readlines()
        if not len(records) == 15:
            continue

        for r in records:
            s = r.split()
            n = int(s[0])
            m = float(s[1])
            t = float(s[2])

            data[n].append(m)
            time[n].append(t)

    for j in range(15):
        m, s = meansd(data[j + 1])
        t = meansd(time[j + 1])[0]

        print '%d %.3f %.3f %5.1f' % (j + 1, m, s, t)

    print '%d points' % len(data[1])

if __name__ == '__main__':
    gather(sys.argv[1:])
            
