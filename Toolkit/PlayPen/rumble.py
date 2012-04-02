import sys
import os
import subprocess
from iotbx import mtz

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

    for _mtz_file in _mtz_files:
        merged = merge(_mtz_file)
        remove.append(merged)
        m = mtz.object(merged)
        mas = m.as_miller_arrays()

        for ma in mas:
            if not ma.anomalous_flag():
                continue
            data.append(ma)

    differences = [_data.anomalous_differences() for _data in data]

    cc_matrix = { }

    for i in range(len(differences) - 1):
        for j in range(i + 1, len(differences)):
            correlation = differences[i].correlation(differences[j])
            cc, n = correlation.coefficient(), correlation.n()

            print '%20s %20s %.3f %d' % (_mtz_files[i], _mtz_files[j], cc, n)
            print '%20s %20s %.3f %d' % (_mtz_files[j], _mtz_files[i], cc, n)

    for name in remove:
        os.remove(name)

if __name__ == '__main__':
    rumble(sys.argv[1:])
