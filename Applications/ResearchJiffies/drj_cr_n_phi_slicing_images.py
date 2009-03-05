import math
import sys
import os

from rj_lib_parse_labelit import rj_parse_labelit_log_file, \
     rj_parse_labelit_log

from rj_lib_find_images import rj_get_phi

from rj_lib_run_job import rj_run_job

def meansd(values):
    mean = sum(values) / len(values)
    var = sum([(v - mean) * (v - mean) for v in values]) / len(values)
    return mean, math.sqrt(var)

def gather(pmin, pmax, files):
    data = { }

    for j in range(1, 10):
        data[j + 1] = []

    here = os.getcwd()

    for f in files:
        # hack to get the image name, so that I can then get (and test) the 
        # phi range...

        directory = os.path.split(f)[0]
        os.chdir(directory)
        output = rj_run_job('labelit.stats_index', [], [])
        os.chdir(here)
        b, l, m, c, i = rj_parse_labelit_log(output)

        phi = rj_get_phi(i)

        if phi < pmin or phi > pmax:
            continue
        
        records = open(f, 'r').readlines()
        if not len(records) == 9:
            continue

        for r in records:
            s = r.split()
            n = int(s[0])
            m = float(s[1])

            data[n].append(m)

    for j in range(1, 10):
        positive_data = []
        for d in data[j + 1]:
            if d > 0:
                positive_data.append(d)
        m, s = meansd(positive_data)

        print '%d %.3f %.3f' % (j + 1, m, s)

    print '%d points' % len(data[2])

if __name__ == '__main__':
    gather(float(sys.argv[1]), float(sys.argv[2]), sys.argv[3:])
            
