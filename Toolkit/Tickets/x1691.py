import os
import sys
import math
import copy
import shutil
import random
import subprocess

from iotbx import mtz

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Applications.get_ccp4_commands import get_ccp4_commands

def run_job(executable, arguments = [], stdin = [], working_directory = None):

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

def get_time(records):
    for record in records:
        if 'Times: User:' in record:
            return float(record.replace('s', '').split()[2]) + \
                   float(record.replace('s', '').split()[4])

    raise RuntimeError, 'time not found'

def random_fraction(fraction, candidates):
    return random_selection(fraction * len(candidates), candidates)

def random_selection(number, candidates):

    assert(number <= len(candidates))
    
    selected = set()

    while len(selected) < number:
        selected.add(random.choice(candidates))

    return selected

def trim_mtz_file(hklin, hklout, nref):

    mtz_obj = mtz.object(hklin)

    mi = mtz_obj.extract_miller_indices()

    included = random_selection(nref, list(set(mi)))

    flag_column = mtz_obj.get_column('FLAG')
    flag_values = flag_column.extract_values()

    for j, hkl in enumerate(mi):
        if not hkl in included:
            flag_values[j] += 50

    flag_column.set_values(flag_values)

    mtz_obj.write(hklout)

    return

def unique_reflections(hklin):

    mtz_obj = mtz.object(hklin)

    return len(set(mtz_obj.extract_miller_indices()))

def test_rerun_scala(scala_log_file):
    commands, logicals = get_ccp4_commands(open(scala_log_file).readlines())

    non_scales_commands = []

    for command in commands:
        if not 'scales' in command[:6]:
            non_scales_commands.append(command)

    hklin = logicals['HKLIN']

    print '%d unique reflections' % unique_reflections(hklin)

    scales_commands = [
        'scales rotation spacing 5 bfactor off',
        'scales rotation spacing 5 bfactor off tails',
        'scales rotation spacing 5 bfactor on',
        'scales rotation spacing 5 bfactor on tails',
        'scales rotation spacing 5 secondary 6 bfactor off',
        'scales rotation spacing 5 secondary 6 bfactor off tails',
        'scales rotation spacing 5 secondary 6 bfactor on',
        'scales rotation spacing 5 secondary 6 bfactor on tails'
        ]

    for scales_command in scales_commands:
        run_commands = [command for command in commands]
        run_commands.append(scales_command)

        log = run_job('scala', ['hklin', hklin, 'hklout', 'temp.mtz'],
                      run_commands)

        rfactors = get_out_rfactors(log)
        time = get_time(log)

        print '%s %.2f' % (scales_command, time)

        for dataset in sorted(rfactors):
            print '%s' % dataset, '%.3f %.3f %.3f' % rfactors[dataset]

    return

if __name__ == '__main__':
    test_rerun_scala(sys.argv[1])

    
    
    
    

