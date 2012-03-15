import sys
import os

def parse_ccp4_loggraph(textlines):
    '''Look through the standard output of the program for
    CCP4 loggraph text. When this is found store it in a
    local dictionary to allow exploration.'''

    # reset the loggraph store
    loggraph = { }

    for i in range(len(textlines)):
        line = textlines[i]
        if '$TABLE' in line:
            n_dollar = line.count('$$')

            current = line.split(':')[1].replace('>',
                                                 '').strip()
            loggraph[current] = { }
            loggraph[current]['columns'] = []
            loggraph[current]['data'] = []

            loggraph_info = ''

            while n_dollar < 4:
                n_dollar += line.count('$$')
                loggraph_info += line

                if n_dollar == 4:
                    break

                i += 1
                line = textlines[i]

            tokens = loggraph_info.split('$$')
            loggraph[current]['columns'] = tokens[1].split()

            if len(tokens) < 4:
                raise RuntimeError, 'loggraph "%s" broken' % current

            data = tokens[3].split('\n')

            columns = len(loggraph[current]['columns'])

            for j in range(len(data)):
                record = data[j].split()
                if len(record) == columns:
                    loggraph[current]['data'].append(record)

    return loggraph

def rummage(loggraphs):
    for name in loggraphs:
        if 'Analysis against all Batches for all runs' in name:
            return loggraphs[name]

    raise RuntimeError, 'you no get here'

def understand(analysis_as_batch):
    batch_column = analysis_as_batch['columns'].index('Batch_number')
    rmerge_column = analysis_as_batch['columns'].index('Rmerge')

    batches = [int(record[batch_column]) for record in \
               analysis_as_batch['data']]

    rmerges = [float(record[rmerge_column]) for record in \
               analysis_as_batch['data']]

    run = 0

    results = { }

    batch = 0
    runstart = 0

    rmerges_this_run = { }

    for j, b in enumerate(batches):
        if b - batch > 1:
            batch = b - 1
            runstart = batch
            run += 1
            results[run] = rmerges_this_run
            rmerges_this_run = { }

        batch = b
        rmerges_this_run[b - runstart] = rmerges[j]

    run += 1
    results[run] = rmerges_this_run

    return results

def print_results(results):
    runs = sorted(results)
    maxbatch = max([max(results[run]) for run in runs])

    fout = open('plot.dat', 'w')

    for j in range(1, maxbatch + 1):
        fout.write('%d' % j)
        for run in runs:
            fout.write(' %6.3f' % results[run].get(j, 0.0))
        fout.write('\n')

    fout.close()

    fout = open('plot.gnu', 'w')

    fout.write('set term pos col\n')
    fout.write('set out "plot.ps"\n')
    fout.write('set xlabel "batch"\n')
    fout.write('set ylabel "rmerge"\n')

    fout.write('plot "plot.dat" using 1:2 with lines title "run 1"')
    for j in runs[1:]:
        fout.write(', "" using 1:%d with lines title "run %d"' % (j + 1, j))
    fout.write('\n')

if __name__ == '__main__':

    print_results(understand(rummage(parse_ccp4_loggraph(
        open(sys.argv[1]).readlines()))))

    os.system('gnuplot plot.gnu')
    os.system('ps2pdf plot.ps')
