import math
import sys
import os
import re
import subprocess
import shutil

def get_rmerge():
    records = open('CORRECT.LP', 'r').readlines()

    for index in range(len(records)):
        if '------------------------------------------' in records[index]:
            break

    return float(records[index + 1].split()[4])

def run_xds_xycorr(commands):

    fout = open('XDS.INP', 'w')
    for record in commands:
        fout.write('%s\n' % record)
    fout.write('JOB=XYCORR\n')
    fout.close()

    subprocess.call('xds_par')

    return

def run_xds_init(commands):

    fout = open('XDS.INP', 'w')
    for record in commands:
        fout.write('%s\n' % record)
    fout.write('JOB=INIT\n')
    fout.close()

    subprocess.call('xds_par')

    return

def run_xds_colspot(commands):

    fout = open('XDS.INP', 'w')
    for record in commands:
        fout.write('%s\n' % record)
    fout.write('JOB=COLSPOT\n')
    fout.close()

    subprocess.call('xds_par')

    return

def run_xds_idxref(commands, cell = None, spacegroup = None):

    fout = open('XDS.INP', 'w')
    for record in commands:
        fout.write('%s\n' % record)
    if cell:
        fout.write(
            'UNIT_CELL_CONSTANTS=%.2f %.2f %.2f %.2f %.2f %.2f\n' % cell)
        fout.write(
            'SPACE_GROUP_NUMBER=%d\n' % spacegroup)
    fout.write('JOB=IDXREF\n')
    fout.close()

    subprocess.call('xds_par')

    return

def run_xds_defpix(commands):

    fout = open('XDS.INP', 'w')
    for record in commands:
        fout.write('%s\n' % record)
    fout.write('JOB=DEFPIX\n')
    fout.close()

    subprocess.call('xds_par')

    return

def run_xds_integrate(commands):

    fout = open('XDS.INP', 'w')
    for record in commands:
        fout.write('%s\n' % record)
    fout.write('JOB=INTEGRATE\n')
    fout.close()

    subprocess.call('xds_par')

    return

def run_xds_correct(commands, cell = None, spacegroup = None):

    fout = open('XDS.INP', 'w')
    for record in commands:
        fout.write('%s\n' % record)
    if cell:
        fout.write(
            'UNIT_CELL_CONSTANTS=%.2f %.2f %.2f %.2f %.2f %.2f\n' % cell)
        fout.write(
            'SPACE_GROUP_NUMBER=%d\n' % spacegroup)
    fout.write('JOB=CORRECT\n')
    fout.close()

    subprocess.call('xds_par')

    return

def gather_parameters(source_dir):
    # find images - from labelit log file

    labelit_log = None

    for filename in os.listdir(
        os.path.join(source_dir, 'index')):
        if 'labelit.screen.log' in filename:
            labelit_log = os.path.join(
                source_dir, 'index', filename)
            break

    if not labelit_log:
        raise RuntimeError, 'labelit log file not found'

    directory_image = open(labelit_log, 'r').readlines()[0].strip()

    if not os.path.exists(directory_image):
        raise RuntimeError, 'error reading file %s' % labelit_log

    directory = os.path.split(directory_image)[0]

    # now look for all of the *.INP files for XDS - this will be used to
    # build up a database of the necessary commands

    inp_files = { }

    for step in ['XYCORR', 'INIT', 'COLSPOT', 'IDXREF',
                 'DEFPIX', 'INTEGRATE', 'CORRECT']:
        inp_files[step] = []
        for filename in os.listdir(
            os.path.join(source_dir, 'integrate')):
            if ('%s.INP' % step) in filename:
                count = int(filename.split('_')[0])
                inp_files[step].append((count, filename))

        if inp_files[step] == []:
            raise RuntimeError, 'could not find %s.INP' % step

    command_records = [ ]

    for step in ['XYCORR', 'INIT', 'COLSPOT', 'IDXREF',
                 'DEFPIX', 'INTEGRATE', 'CORRECT']:
        inp_files[step].sort()
        for record in open(
            os.path.join(source_dir, 'integrate',
                         inp_files[step][-1][1]), 'r').readlines():
            if not record.strip() in command_records:
                command_records.append(record.strip())

    # now try to 'clean' these...

    new_commands = { }
    keys = []

    for command in command_records:
        key = command.split('=')[0].strip()
        new_commands[key] = command

        if not key in keys:
            keys.append(key)

    # now delete the things I don't want in there

    for key in ['SPOT_RANGE', 'BACKGROUND_RANGE', 'DATA_RANGE',
                'JOB', 'REFINE(IDXREF)', 'REFINE(INTEGRATE)',
                'REFINE(CORRECT)', 'TEST', 'BEAM_DIVERGENCE',
                'REFLECTING_RANGE', 'CORRECTIONS']:
        try:
            del(new_commands[key])
            keys.remove(key)
        except KeyError, e:
            pass

    command_records = []

    for key in keys:
        command_records.append(new_commands[key])

    # now look for other matching images...

    template = os.path.split(
        new_commands['NAME_TEMPLATE_OF_DATA_FRAMES'].split('=')[1])[-1]
    
    regexp = re.compile(template.replace('?', '[0-9]'))

    images = []

    start = template.split('?')[0]
    end = template.split('?')[-1]

    for filename in os.listdir(directory):
        match = regexp.match(filename)
        if match:
            images.append(
                int(match.group(0).replace(start, '').replace(end, '')))

    command_records.sort()

    return directory, command_records, (min(images), max(images))

def main1(source_dir):
    directory, commands, image_range = gather_parameters(source_dir)

    try:
        os.symlink(directory, os.path.join(os.getcwd(), '_images'))
    except OSError, e:
        pass

    commands.append('DATA_RANGE=%d %d' % image_range)

    # filter the commands which we don't want

    new_commands = []
    cell = None
    spacegroup = None

    for command in commands:
        if 'UNIT_CELL_CONSTANTS' in command:
            cell = tuple(map(float, command.split('=')[1].split()))
        elif 'SPACE_GROUP_NUMBER' in command:
            spacegroup = int(command.split('=')[1].strip())
        else:
            new_commands.append(command)

    commands = new_commands

    run_xds_xycorr(commands)
    run_xds_init(commands)
    run_xds_colspot(commands)
    run_xds_idxref(commands)
    run_xds_defpix(commands)
    run_xds_integrate(commands)
    run_xds_correct(commands, cell = cell, spacegroup = spacegroup)

    return get_rmerge()

def main2(source_dir):
    directory, commands, image_range = gather_parameters(source_dir)

    try:
        os.symlink(directory, os.path.join(os.getcwd(), '_images'))
    except OSError, e:
        pass

    commands.append('DATA_RANGE=%d %d' % image_range)

    # filter the commands which we don't want

    new_commands = []
    cell = None
    spacegroup = None

    for command in commands:
        if 'UNIT_CELL_CONSTANTS' in command:
            cell = tuple(map(float, command.split('=')[1].split()))
        elif 'SPACE_GROUP_NUMBER' in command:
            spacegroup = int(command.split('=')[1].strip())
        else:
            new_commands.append(command)

    commands = new_commands

    run_xds_xycorr(commands)
    run_xds_init(commands)
    run_xds_colspot(commands)
    run_xds_idxref(commands)
    run_xds_defpix(commands)
    run_xds_integrate(commands)
    run_xds_correct(commands, cell = cell, spacegroup = spacegroup)
    shutil.copyfile('GXPARM.XDS', 'XPARM.XDS')
    run_xds_defpix(commands)
    run_xds_integrate(commands)
    run_xds_correct(commands, cell = cell, spacegroup = spacegroup)

    return get_rmerge()

def main3(source_dir):
    directory, commands, image_range = gather_parameters(source_dir)

    try:
        os.symlink(directory, os.path.join(os.getcwd(), '_images'))
    except OSError, e:
        pass

    commands.append('DATA_RANGE=%d %d' % image_range)

    # filter the commands which we don't want

    new_commands = []
    cell = None
    spacegroup = None

    for command in commands:
        if 'UNIT_CELL_CONSTANTS' in command:
            cell = tuple(map(float, command.split('=')[1].split()))
        elif 'SPACE_GROUP_NUMBER' in command:
            spacegroup = int(command.split('=')[1].strip())
        else:
            new_commands.append(command)

    commands = new_commands

    run_xds_xycorr(commands)
    run_xds_init(commands)
    run_xds_colspot(commands)
    run_xds_idxref(commands, cell = cell, spacegroup = spacegroup)
    run_xds_defpix(commands)
    run_xds_integrate(commands)
    run_xds_correct(commands, cell = cell, spacegroup = spacegroup)

    return get_rmerge()

def main4(source_dir):
    directory, commands, image_range = gather_parameters(source_dir)

    try:
        os.symlink(directory, os.path.join(os.getcwd(), '_images'))
    except OSError, e:
        pass

    commands.append('DATA_RANGE=%d %d' % image_range)

    # filter the commands which we don't want

    new_commands = []
    cell = None
    spacegroup = None

    for command in commands:
        if 'UNIT_CELL_CONSTANTS' in command:
            cell = tuple(map(float, command.split('=')[1].split()))
        elif 'SPACE_GROUP_NUMBER' in command:
            spacegroup = int(command.split('=')[1].strip())
        else:
            new_commands.append(command)

    commands = new_commands

    run_xds_xycorr(commands)
    run_xds_init(commands)
    run_xds_colspot(commands)
    run_xds_idxref(commands)
    run_xds_defpix(commands)
    run_xds_integrate(commands)

    extra_commands = []

    for record in open('INTEGRATE.LP', 'r').readlines():
        lst = record.split()
        if not lst:
            continue
        if lst[0] == 'BEAM_DIVERGENCE=':
            extra_commands.append(record.strip())
        if lst[0] == 'REFLECTING_RANGE=':
            extra_commands.append(record.strip())
        
    for command in extra_commands:
        commands.append(command)

    run_xds_integrate(commands)
    run_xds_correct(commands, cell = cell, spacegroup = spacegroup)

    return get_rmerge()

def main5(source_dir):
    directory, commands, image_range = gather_parameters(source_dir)

    try:
        os.symlink(directory, os.path.join(os.getcwd(), '_images'))
    except OSError, e:
        pass

    commands.append('DATA_RANGE=%d %d' % image_range)

    # filter the commands which we don't want

    new_commands = []
    cell = None
    spacegroup = None

    for command in commands:
        if 'UNIT_CELL_CONSTANTS' in command:
            cell = tuple(map(float, command.split('=')[1].split()))
        elif 'SPACE_GROUP_NUMBER' in command:
            spacegroup = int(command.split('=')[1].strip())
        else:
            new_commands.append(command)

    commands = new_commands

    run_xds_xycorr(commands)
    run_xds_init(commands)
    run_xds_colspot(commands)
    run_xds_idxref(commands)
    run_xds_defpix(commands)
    run_xds_integrate(commands)
    run_xds_correct(commands, cell = cell, spacegroup = spacegroup)

    shutil.copyfile('GXPARM.XDS', 'XPARM.XDS')
    shutil.copyfile('GX-CORRECTIONS.pck', 'X-CORRECTIONS.pck')
    shutil.copyfile('GY-CORRECTIONS.pck', 'Y-CORRECTIONS.pck')

    run_xds_init(commands)
    run_xds_defpix(commands)
    run_xds_integrate(commands)
    run_xds_correct(commands, cell = cell, spacegroup = spacegroup)

    return get_rmerge()

def clean():
    for f in ['ABS.pck', 'ABSORP.pck', 'BKGINIT.pck', 'BKGPIX.pck',
              'BLANK.pck', 'COLSPOT.LP', 'CORRECT.LP', 'DECAY.pck',
              'DEFPIX.LP', 'DX-CORRECTIONS.pck', 'DY-CORRECTIONS.pck',
              'FRAME.pck', 'GAIN.pck', 'GX-CORRECTIONS.pck', 'GXPARM.XDS',
              'GY-CORRECTIONS.pck', 'IDXREF.LP', 'INIT.LP', 'INTEGRATE.HKL',
              'INTEGRATE.LP', 'MODPIX.pck', 'SPOT.XDS', 'X-CORRECTIONS.pck',
              'XDS.INP', 'XDS_ASCII.HKL', 'XPARM.XDS', 'XYCORR.LP',
              'Y-CORRECTIONS.pck', '_images']:
        try:
            os.remove(os.path.join(os.getcwd(), f))
        except OSError, e:
            pass

if __name__ == '__main__':

    clean()
    r1 = main1(sys.argv[1])
    clean()
    r2 = main2(sys.argv[1])
    clean()
    r3 = main3(sys.argv[1])
    clean()
    r4 = main4(sys.argv[1])
    clean()
    r5 = main5(sys.argv[1])
    
    print 'Rmerge start:      %6.3f' % r1
    print 'Rmerge gxparm:     %6.3f' % r2
    print 'Rmerge set cell:   %6.3f' % r3
    print 'Rmerge phi:        %6.3f' % r4
    print 'Rmerge gxparm etc: %6.3f' % r5
