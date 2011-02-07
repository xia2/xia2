import math
import sys

def get_ccs(xscale_lp):

    ccs = { }

    xmax = 0

    records = open(xscale_lp).readlines()

    for j, record in enumerate(records):

        if 'CORRELATIONS BETWEEN INPUT DATA SETS' in record:

            k = j + 5

            while len(records[k].split()) == 6:
                values = records[k].split()

                _i = int(values[0])
                _j = int(values[1])
                _n = int(values[2])
                _cc = float(values[3])

                ccs[(_i, _j)] = (_n, _cc)
                ccs[(_j, _i)] = (_n, _cc)

                xmax = _i + 1

                k += 1

    for j in range(xmax):
        ccs[(j + 1, j + 1)] = (0, 0)
        print '%4d %6.4f' % (j + 1, sum([ccs[(i + 1, j + 1)][1]
                                         for i in range(xmax)]) / xmax)

if __name__ == '__main__':

    get_ccs(sys.argv[1])
                
