import math
import sys
import copy

def mean_isigma(hkl_file):

    # fixme this needs to work to a given resolution

    isigmas = []

    for record in open(hkl_file):
        if '!' in record[:1]:
            continue
        values = record.split()[3:5]
        isigmas.append((float(values[0]) / float(values[1])))

    return sum(isigmas) / len(isigmas)

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

    if not file_names:
        for j, record in enumerate(records):
            if 'SET# INTENSITY  ACCEPTED REJECTED' in record:

                k = j + 1

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

    fout = open('x1335.log', 'w')
    for j in range(xmax):
        ccs[(j + 1, j + 1)] = (0, 0)

        isigma = mean_isigma(file_names[j + 1])

        print '%4d %6.4f %6.2f %s' % (j + 1,
                                      sum([ccs[(i + 1, j + 1)][1]
                                           for i in range(xmax)]) / (xmax - 1),
                                      isigma, file_names[j + 1])
        fout.write('%4d %6.4f %6.2f %s\n' % \
                   (j + 1, sum([ccs[(i + 1, j + 1)][1]
                                for i in range(xmax)]) / (xmax - 1),
                       isigma, file_names[j + 1]))

    fout.close()
        
def ccs_to_R(xscale_lp):

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

    if not file_names:
        for j, record in enumerate(records):
            if 'SET# INTENSITY  ACCEPTED REJECTED' in record:

                k = j + 1

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

    tokens = []

    distances = {}

    for j in range(xmax):
        for i in range(xmax):
            cc = ccs.get((i + 1, j + 1), (0, 1.0))[1]
            if cc < 0.01:
                cc = 0.01
            tokens.append(((1.0 / cc) - 1))
            distances[(i, j)] = (1.0 / cc) - 1

    fout = open('x1335.R', 'w')
    fout.write('m = matrix(c(')
    for t in tokens[:-1]:
        fout.write('%.4f, ' % t)
    fout.write('%f), nrow = %d)\n' % (tokens[-1], xmax))
    fout.write('d = as.dist(m)\n')
    fout.write('c = hclust(d, method = "ward")\n')
    fout.write('plot(c)\n')

    from ward_cluster import ward_cluster

    data = [(j + 1) for j in range(xmax)]

    history = ward_cluster(data, distances)

    for target, source, distance in history:
        print 'Cluster: %.2f' % distance
        for t in target:
            print data[t], file_names[data[t]]
        for s in source:
            print data[s], file_names[data[s]]

if __name__ == '__main__':

    get_ccs(sys.argv[1])
    ccs_to_R(sys.argv[1])
