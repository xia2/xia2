#!/usr/bin/env python
# xia2setup.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# xia2setup.py - an application to generate the .xinfo file for data
# reduction from a directory full of images, optionally with scan and
# sequence files which will be used to add matadata.
#
# 18th December 2006
#


import os
import sys
import exceptions
import time
import traceback

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'
if not 'XIA2CORE_ROOT' in os.environ:
    os.environ['XIA2CORE_ROOT'] = os.path.join(os.environ['XIA2_ROOT'], 'core')

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

from Schema.Sweep import SweepFactory
from Experts.FindImages import image2template_directory
from Handlers.CommandLine import CommandLine
from Handlers.Flags import Flags
from Wrappers.CCP4.Chooch import Chooch
from Modules.LabelitBeamCentre import compute_beam_centre
from Handlers.Streams import streams_off

known_image_extensions = ['img', 'mccd', 'mar2300', 'mar1200', 'mar1600',
                          'mar3450', 'osc', 'cbf', 'mar2000']

xds_file_names = ['ABS', 'ABSORP', 'BKGINIT', 'BKGPIX', 'BLANK', 'DECAY',
                  'X-CORRECTIONS', 'Y-CORRECTIONS', 'MODPIX', 'FRAME',
                  'GX-CORRECTIONS', 'GY-CORRECTIONS', 'DX-CORRECTIONS',
                  'DY-CORRECTIONS', 'GAIN']

known_sweeps = { }

known_scan_extensions = ['scan']

known_sequence_extensions = ['seq']

latest_sequence = None

latest_chooch = None

target_template = None

def is_scan_name(file):
    global known_scan_extensions

    if os.path.isfile(file):
        if file.split('.')[-1] in known_scan_extensions:
            return True

    return False

def is_sequence_name(file):
    global known_sequence_extensions

    if os.path.isfile(file):
        if file.split('.')[-1] in known_sequence_extensions:
            return True

    return False

def is_image_name(file):

    global known_image_extensions

    if os.path.isfile(file):
        exten = file.split('.')[-1]
        if exten in known_image_extensions:
            return True

        # check for files like foo_bar.0001 - c/f FIXME for 25/SEP/06
        end = file.split('.')[-1]
        try:
            j = int(end)
            return True
        except:
            pass

    return False

def is_xds_file(f):
    filename = os.path.split(f)[1]

    xds_files = ['ABS', 'ABSORP', 'BKGINIT', 'BKGPIX', 'BLANK', 'DECAY',
                 'DX-CORRECTIONS', 'DY-CORRECTIONS', 'FRAME', 'GAIN',
                 'GX-CORRECTIONS', 'GY-CORRECTIONS', 'MODPIX',
                 'X-CORRECTIONS', 'Y-CORRECTIONS']

    return (filename.split('.')[0].split('_') in xds_files)

def get_sweep(f):

    global target_template

    global known_sweeps

    if not is_image_name(f):
        return

    if is_xds_file(f):
        return

    # in here, check the permissions on the file...

    if not os.access(f, os.R_OK):
        from Handlers.Streams import Debug
        Debug.write('No read permission for %s' % f)

    try:
        template, directory = image2template_directory(f)

        if target_template:
            if template != target_template:
                return

        key = (directory, template)
        if not known_sweeps.has_key(key):
            sweeplist = SweepFactory(template, directory)
            known_sweeps[key] = sweeplist

    except exceptions.Exception, e:
        from Handlers.Streams import Debug
        Debug.write('Exception: %s (%s)' % (str(e), f))
        # traceback.print_exc(file = sys.stdout)

    return

def parse_sequence(sequence_file):
    sequence = ''

    for record in open(sequence_file).readlines():
        if record[0].upper() in \
           'ABCDEFGHIJKLMNOPQRSTUVWXYZ ':
            sequence += record.strip().upper()

    global latest_sequence
    latest_sequence = sequence
    return

def visit(root, directory, files):
    files.sort()
    for f in files:
        get_sweep(os.path.join(directory, f))

        if is_scan_name(os.path.join(directory, f)):
            global latest_chooch
            try:
                latest_chooch = Chooch()
                if CommandLine.get_atom_name():
                    latest_chooch.set_atom(CommandLine.get_atom_name())
                latest_chooch.set_scan(os.path.join(directory, f))
                latest_chooch.scan()
            except:
                latest_chooch = None
                
        if is_sequence_name(os.path.join(directory, f)):
            parse_sequence(os.path.join(directory, f))

def print_sweeps(out = sys.stdout):

    global known_sweeps, latest_sequence

    sweeplists = known_sweeps.keys()
    sweeplists.sort()

    # analysis pass

    wavelengths = []

    for sweep in sweeplists:
        sweeps = known_sweeps[sweep]
        # this should sort on exposure epoch ...?
        sweeps.sort()
        for s in sweeps:

            if len(s.get_images()) < Flags.get_min_images():
                continue

            wavelength = s.get_wavelength()

            if not wavelength in wavelengths:
                wavelengths.append(wavelength)

    wavelength_map = { }

    project = CommandLine.get_project_name()
    if not project:
        project = 'AUTOMATIC'

    crystal = CommandLine.get_crystal_name()
    if not crystal:
        crystal = 'DEFAULT'

    out.write('BEGIN PROJECT %s\n' % project)
    out.write('BEGIN CRYSTAL %s\n' % crystal)

    out.write('\n')

    # check to see if a user spacegroup has been assigned - if it has,
    # copy it in...

    if Flags.get_spacegroup():
        out.write('USER_SPACEGROUP %s\n' % Flags.get_spacegroup())
        out.write('\n')

    if Flags.get_cell():
        out.write('USER_CELL %.2f %.2f %.2f %.2f %.2f %.2f\n' % \
                  tuple(Flags.get_cell()))
        out.write('\n')

    if Flags.get_freer_file():
        out.write('FREER_FILE %s\n' % Flags.get_freer_file())
        out.write('\n')

    if latest_sequence:
        out.write('BEGIN AA_SEQUENCE\n')
        out.write('\n')
        for sequence_chunk in [latest_sequence[i:i + 60] \
                               for i in range(0, len(latest_sequence), 60)]:
            out.write('%s\n' % sequence_chunk)
        out.write('\n')
        out.write('END AA_SEQUENCE\n')
        out.write('\n')

    if CommandLine.get_atom_name():
        out.write('BEGIN HA_INFO\n')
        out.write('ATOM %s\n' % CommandLine.get_atom_name().lower())
        if CommandLine.get_atom_name().lower() == 'se' and latest_sequence:
            # assume that this is selenomethionine
            out.write('! If this is SeMet uncomment next line...\n')
            out.write('!NUMBER_PER_MONOMER %d\n' % latest_sequence.count('M'))
            out.write('!NUMBER_TOTAL M\n')
        else:
            out.write('!NUMBER_PER_MONOMER N\n')
            out.write('!NUMBER_TOTAL M\n')
        out.write('END HA_INFO\n')
        out.write('\n')

    for j in range(len(wavelengths)):

        global latest_chooch

        if latest_chooch:
            name = latest_chooch.id_wavelength(wavelengths[j])
            first_name = name
            counter = 1

            while name in [wavelength_map[w] for w in wavelength_map]:
                counter += 1
                name = '%s%d' % (first_name, counter)
            
            fp, fpp = latest_chooch.get_fp_fpp(wavelengths[j])
        else:
            fp, fpp = 0.0, 0.0
            if len(wavelengths) == 1 and CommandLine.get_atom_name():
                name = 'SAD'
            elif len(wavelengths) == 1:
                name = 'NATIVE'
            else:
                name = 'WAVE%d' % (j + 1)

        wavelength_map[wavelengths[j]] = name

        out.write('BEGIN WAVELENGTH %s\n' % name)

        dmin = Flags.get_resolution_high()
        dmax = Flags.get_resolution_low()

        if dmin and dmax:
            out.write('RESOLUTION %f %f\n' % (dmin, dmax))
        elif dmin:
            out.write('RESOLUTION %f\n' % dmin)

        out.write('WAVELENGTH %f\n' % wavelengths[j])
        if fp != 0.0 and fpp != 0.0:
            out.write('F\' %5.2f\n' % fp)
            out.write('F\'\' %5.2f\n' % fpp)

        out.write('END WAVELENGTH %s\n' % name)
        out.write('\n')

    j = 0
    for sweep in sweeplists:
        sweeps = known_sweeps[sweep]
        # this should sort on exposure epoch ...?
        sweeps.sort()
        for s in sweeps:

            # require at least n images to represent a sweep...

            if len(s.get_images()) < Flags.get_min_images():
                continue

            j += 1
            name = 'SWEEP%d' % j

            out.write('BEGIN SWEEP %s\n' % name)

            if Flags.get_reversephi():
                out.write('REVERSEPHI\n')

            out.write('WAVELENGTH %s\n' % wavelength_map[s.get_wavelength()])

            out.write('DIRECTORY %s\n' % s.get_directory())
            out.write('IMAGE %s\n' % os.path.split(s.imagename(min(
                s.get_images())))[-1])

            if Flags.get_start_end():
                start, end = Flags.get_start_end()

                if start < min(s.get_images()):
                    raise RuntimeError, 'requested start %d < %d' % \
                          (start, min(s.get_images()))

                if end > max(s.get_images()):
                    raise RuntimeError, 'requested end %d > %d' % \
                          (end, max(s.get_images()))

                out.write('START_END %d %d\n' % (start, end))
            else:
                out.write('START_END %d %d\n' % (min(s.get_images()),
                                                 max(s.get_images())))

            # really don't need to store the epoch in the xinfo file
            # out.write('EPOCH %d\n' % int(s.get_collect()[0]))
            cl_beam = CommandLine.get_beam()
            if cl_beam[0] or cl_beam[1]:
                out.write('BEAM %6.2f %6.2f\n' % cl_beam)
            else:
                beam = compute_beam_centre(s)
                if beam:
                    out.write('BEAM %6.2f %6.2f\n' % tuple(beam))
            out.write('END SWEEP %s\n' % name)

            out.write('\n')

    out.write('END CRYSTAL %s\n' % crystal)
    out.write('END PROJECT %s\n' % project)

def rummage(path):
    '''Walk through the directories looking for sweeps.'''
    os.path.walk(path, visit, os.getcwd())
    return

def write_xinfo(filename, path, template = None):

    global target_template

    target_template = template

    crystal = CommandLine.get_crystal_name()

    if not crystal:
        crystal = 'DEFAULT'

    if not os.path.isabs(filename):
        filename = os.path.abspath(filename)

    directory = os.path.join(os.getcwd(), crystal, 'setup')

    try:
        os.makedirs(directory)
    except OSError, e:
        if not 'File exists' in str(e):
            raise e

    # FIXME should I have some exception handling in here...?

    start = os.getcwd()
    os.chdir(directory)

    # if we have given a template and directory on the command line, just
    # look there (i.e. not in the subdirectories)

    if CommandLine.get_template() and CommandLine.get_directory():
        visit(None, CommandLine.get_directory(),
              os.listdir(CommandLine.get_directory()))
    else:
        rummage(path)

    fout = open(filename, 'w')
    print_sweeps(fout)

    # change back directory c/f bug # 2693 - important for error files...
    os.chdir(start)

if __name__ == '__main__':

    streams_off()

    argv = sys.argv

    # test to see if sys.argv[-2] + path is a valid path - to work around
    # spaced command lines

    path = argv.pop()

    # perhaps move to a new directory...

    crystal = CommandLine.get_crystal_name()

    fout = open(os.path.join(os.getcwd(), 'automatic.xinfo'), 'w')

    if not crystal:
        crystal = 'DEFAULT'

    directory = os.path.join(os.getcwd(), crystal, 'setup')

    try:
        os.makedirs(directory)
    except OSError, e:
        if not 'File exists' in str(e):
            raise e

    os.chdir(directory)

    while not os.path.exists(path):
        path = '%s %s' % (argv.pop(), path)

    if not os.path.isabs(path):
        path = os.path.abspath(path)

    rummage(path)
    print_sweeps(fout)
