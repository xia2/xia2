import math
import sys

def get_ccs(xscale_lp):

    ccs = { }

    file_names = { }

    xmax = 0

    records = open(xscale_lp).readlines()

    # first scan through to get the file names...

    for j, record in enumerate(records):
        if 'NUMBER OF UNIQUE REFLECTIONS' in record:

            k = j + 5

            while len(records[k].split()) == 5:
                values = records[k].split()
                file_names[int(values[0])] = values[-1]

                k += 1

            break

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

            break

    for j in range(xmax):
        ccs[(j + 1, j + 1)] = (0, 0)
        print '%4d %6.4f %s' % (j + 1,
                                sum([ccs[(i + 1, j + 1)][1]
                                     for i in range(xmax)]) / (xmax - 1),
                                file_names[j + 1])

if __name__ == '__main__':

    get_ccs(sys.argv[1])
                
