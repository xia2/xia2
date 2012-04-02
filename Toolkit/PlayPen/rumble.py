import sys
import os
import subprocess
from iotbx import mtz

from ward_cluster import ward_cluster

def run_job(executable, arguments = [], stdin = [], working_directory = None):
    '''Run a program with some command-line arguments and some input,
    then return the standard output when it is finished.'''

    if working_directory is None:
        working_directory = os.getcwd()

    command_line = '%s' % executable
    for arg in arguments:
        command_line += ' "%s"' % arg

    popen = subprocess.Popen(command_line,
                             bufsize = 1,
                             stdin = subprocess.PIPE,
                             stdout = subprocess.PIPE,
                             stderr = subprocess.STDOUT,
                             cwd = working_directory,
                             universal_newlines = True,
                             shell = True,
                             env = os.environ)

    for record in stdin:
        popen.stdin.write('%s\n' % record)

    popen.stdin.close()

    output = []

    while True:
        record = popen.stdout.readline()
        if not record:
            break

        output.append(record)

    return output

def merge(mtz_file):
    mtz_file_out = '%s_out.mtz' % mtz_file[:-4]
    output = run_job('scala', ['hklin', mtz_file, 'hklout', mtz_file_out],
                     ['run 1 all', 'scales constant', 'anomalous on',
                      'sdcorrection fixsdb noadjust norefine both 1.0 0.0'])
    return mtz_file_out

def rumble(_mtz_files):

    data = []
    remove = []

    mtz_ids = [int(mtz_file.replace('SCALED_SAD_SWEEP', '').split('.')[0]) \
               for mtz_file in _mtz_files]

    for _mtz_file in _mtz_files:
        merged = merge(_mtz_file)
        remove.append(merged)
        m = mtz.object(merged)
        mas = m.as_miller_arrays()

        for ma in mas:
            if not ma.anomalous_flag():
                continue
            data.append(ma.resolution_filter(d_min = 3.0))

    differences = [_data.anomalous_differences() for _data in data]

    cc_matrix = { }
    distances = { }

    for i in range(len(differences) - 1):
        for j in range(i + 1, len(differences)):
            correlation = differences[i].correlation(differences[j])
            cc, n = correlation.coefficient(), correlation.n()

            if cc < 0.01:
                cc = 0.01
            distance = (1.0 / cc) - 1
            distances[(i, j)] = distance
            distances[(j, i)] = distance

    for name in remove:
        os.remove(name)

    data = [_mtz_files[i] for i in range(len(differences))]

    history = ward_cluster(data, distances)

    for target, source, distance in history:
        print 'Cluster: %.4f' % distance
        for t in target:
            print data[t],
        for s in source:
            print data[s],
        print

if __name__ == '__main__':
    rumble(sys.argv[1:])
