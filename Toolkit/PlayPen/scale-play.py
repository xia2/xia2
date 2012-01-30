import math
import os
import sys
import subprocess
import time
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
                             shell = True)

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

def run_scala(scale_model):
    arguments = ['hklin', '../DEFAULT/scale/AUTOMATIC_DEFAULT_sorted.mtz',
                 'hklout', 'scaled.mtz']

    commands = ['bins 20',
                'run 1 batch 1 to 90',
                'run 2 batch 101 to 190',
                'run 3 batch 201 to 290',
                'name run 1 project AUTOMATIC crystal DEFAULT dataset WAVE1',
                'name run 2 project AUTOMATIC crystal DEFAULT dataset WAVE2',
                'name run 3 project AUTOMATIC crystal DEFAULT dataset WAVE3',
                scale_model,
                'cycles 5',
                'sdcorrection uniform',
                'anomalous on']

    batch_ranges = []

    for command in commands:
        if 'run' in command and 'batch' in command:
            tokens = command.split()
            batch_ranges.append((int(tokens[3]), int(tokens[5])))

    resolutions = erzatz_resolution(
        '../DEFAULT/scale/AUTOMATIC_DEFAULT_sorted.mtz', batch_ranges)

    new_commands = []

    for command in commands:
        if 'run' in command and 'batch' in command:
            tokens = command.split()
            resolution = resolutions[(int(tokens[3]), int(tokens[5]))]
            run = int(tokens[1])
            new_commands.append(command)
            new_commands.append('resolution run %d %.2f' % (run, resolution))
        else:
            new_commands.append(command)

    for command in new_commands:
        print command

    log = run_job('scala', arguments, new_commands)

    rfactors = get_out_rfactors(log)
    convergence = get_out_convergence(log)

    return rfactors, convergence

def linear(x, y):

    _x = sum(x) / len(x)
    _y = sum(y) / len(y)

    sumxx = 0.0
    sumxy = 0.0

    for j in range(len(x)):

        sumxx += (x[j] - _x) * (x[j] - _x)
        sumxy += (x[j] - _x) * (y[j] - _y)

    m = sumxy / sumxx

    c = _y - _x * m

    return m, c

def get_out_convergence(records):

    cycles = []
    shifts = []

    cycle = 0.0

    for record in records:
        if 'Mean and maximum shift/sd' in record and '(' in record:
            shifts.append(math.log10(float(record.split()[6])))
            cycle += 1.0
            cycles.append(cycle)

    m, c = linear(cycles, shifts)

    return (math.log10(0.3) - c) / m

def get_out_rfactors(records):
    rfactors = { }

    dataset = None

    for j in range(len(records)):
        record = records[j]

        if 'Summary data for' in record:
            dataset = record.split()[-1]

        if ' Rmerge         ' in record:
            rfactors[dataset] = tuple(map(float, record.split()[1:]))

    return rfactors

def nint(a):
    i = int(a)
    if a - i > 0.5:
        i += 1
    return i

def erzatz_resolution(reflection_file, batch_ranges):

    mtz_obj = mtz.object(reflection_file)

    miller = mtz_obj.extract_miller_indices()
    dmax, dmin = mtz_obj.max_min_resolution()

    ipr_column = None
    sigipr_column = None
    batch_column = None

    uc = None

    for crystal in mtz_obj.crystals():

        if crystal.name() == 'HKL_Base':
            continue

        uc = crystal.unit_cell()

        for dataset in crystal.datasets():
            for column in dataset.columns():

                if column.label() == 'IPR':
                    ipr_column = column
                elif column.label() == 'SIGIPR':
                    sigipr_column = column
                elif column.label() == 'BATCH':
                    batch_column = column

    assert(ipr_column)
    assert(sigipr_column)
    assert(batch_column)

    ipr_values = ipr_column.extract_values()
    sigipr_values = sigipr_column.extract_values()
    batch_values = batch_column.extract_values()

    batches = [nint(b) for b in batch_values]

    resolutions = { }

    for start, end in batch_ranges:

        d = []
        isig = []

        for j in range(miller.size()):

            if batches[j] < start:
                continue
            if batches[j] > end:
                continue

            d.append(uc.d(miller[j]))
            isig.append(ipr_values[j] / sigipr_values[j])

        resolutions[(start, end)] = compute_resolution(dmax, dmin, d, isig)

    return resolutions

def meansd(values):
    mean = sum(values) / len(values)
    var = sum([(v - mean) * (v - mean) for v in values]) / len(values)
    return mean, math.sqrt(var)

def compute_resolution(dmax, dmin, d, isig):
    bins = { }

    smax = 1.0 / (dmax * dmax)
    smin = 1.0 / (dmin * dmin)

    for j in range(len(d)):
        s = 1.0 / (d[j] * d[j])
        n = nint(100.0 * (s - smax) / (smin - smax))
        if not n in bins:
            bins[n] = []
        bins[n].append(isig[j])

    for b in sorted(bins):
        s = smax + b * (smin - smax) / 100.0
        misig = meansd(bins[b])[0]
        if misig < 1.0:
            return 1.0 / math.sqrt(s)

    return dmin

if __name__ == '__test__':

    resolutions = erzatz_resolution(
        '../DEFAULT/scale/AUTOMATIC_DEFAULT_sorted.mtz',
        [(1, 90), (101, 190), (201, 290)])

    for batches in sorted(resolutions):
        print '%3d %3d' % batches, '%.2f' % resolutions[batches]

if __name__ == '__main__':

    for scale_model in [
        'scales rotation spacing 6 bfactor off',
        'scales rotation spacing 6 bfactor on',
        'scales rotation spacing 6 secondary 6 bfactor off',
        'scales rotation spacing 6 secondary 6 bfactor on',
        'scales rotation spacing 6 bfactor off tails',
        'scales rotation spacing 6 bfactor on tails',
        'scales rotation spacing 6 secondary 6 bfactor off tails',
        'scales rotation spacing 6 secondary 6 bfactor on tails']:
        rfactors, convergence = run_scala(scale_model)

        print scale_model

        for name in sorted(rfactors):
            print '%s' % name, '%.3f %.3f %.3f' % rfactors[name]

        print convergence
