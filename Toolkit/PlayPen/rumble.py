import sys
import os
import math
import subprocess
from iotbx import mtz
from cctbx.array_family import flex

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

def new_cc(a, b):
    '''Compute CC between miller arrays a and b.'''

    assert a.is_real_array()
    assert b.is_real_array()

    _a, _b = a.common_sets(other = b, assert_is_similar_symmetry = True)
    return flex.linear_correlation(_a.data(), _b.data())

def paired_t(ma, mb):
    assert ma.is_real_array()
    assert mb.is_real_array()

    _a, _b = ma.common_sets(other = mb, assert_is_similar_symmetry = True)

    da = _a.data()
    db = _b.data()

    mean_a = sum(da) / len(da)
    mean_b = sum(db) / len(db)

    hat_a = [a - mean_a for a in da]
    hat_b = [b - mean_b for b in db]

    # from http://mathworld.wolfram.com/Pairedt-Test.html

    t = (mean_a - mean_b) * math.sqrt((len(hat_a) * (len(hat_a) - 1)) /
                                      (sum([(a - b) * (a - b) for a, b in
                                            zip(hat_a, hat_b)])))
    
    return t, len(da)
    
def rumble(_mtz_files):

    data = []
    remove = []

    mtz_ids = [int(mtz_file.replace('AUTOMATIC_DEFAULT_scaled_SAD', '').split('.')[0]) \
               for mtz_file in _mtz_files]

    for _mtz_file in _mtz_files:
        # this step is because input data are unmerged - however this may not be
        # needed?
        
        # merged = merge(_mtz_file)
        merged = _mtz_file
        # remove.append(merged)
        m = mtz.object(merged)
        mas = m.as_miller_arrays()

        for ma in mas:
            if not ma.anomalous_flag():
                continue
            data.append(ma)

    if True:
        differences = [_data.anomalous_differences() for _data in data]
    else:
        differences = [_data.anomalous_differences().sigma_filter(
            cutoff_factor = 2.0) for _data in data]

    # differences = data

    for i in range(len(differences)):
        signal_to_noise = sum(abs(differences[i].data())) / \
            sum(differences[i].sigmas())
        # print '%02d %.2f' % (mtz_ids[i], signal_to_noise)

    cc_matrix = { }
    distances = { }

    for i in range(len(differences) - 1):
        for j in range(i + 1, len(differences)):
            correlation = differences[i].correlation(differences[j])
            cc, n = correlation.coefficient(), correlation.n()

            t, nt = paired_t(differences[i], differences[j])
 
            print '%2d %2d %.4f %5d %.4f %5d' % (mtz_ids[i], mtz_ids[j],
                                                 cc, n, t, nt)
            
    for name in remove:
        os.remove(name)

    if True:
        return

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
