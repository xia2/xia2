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
# 17/JAN/07 FIXED need to add a "calculation of beam centre" stage to this 
#                 process.
# 
# 
# 

import os
import sys
import exceptions
import time

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'
if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

from Schema.Sweep import SweepFactory
from Experts.FindImages import image2template_directory
from Handlers.CommandLine import CommandLine
from Wrappers.CCP4.Chooch import Chooch
from Modules.LabelitBeamCentre import compute_beam_centre
from Handlers.Streams import streams_off

known_image_extensions = ['img', 'mccd', 'mar2300', 'mar3450', 'osc', 'cbf']
known_sweeps = { }

known_scan_extensions = ['scan']

known_sequence_extensions = ['seq']

latest_sequence = None

latest_chooch = None

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
        if file.split('.')[-1] in known_image_extensions:
            return True

        # check for files like foo_bar.0001 - c/f FIXME for 25/SEP/06
        end = file.split('.')[-1]
        try:
            j = int(end)
            return True
        except:
            pass

    return False

def get_sweep(file):

    global known_sweeps
    
    if not is_image_name(file):
        return

    try:
        template, directory = image2template_directory(file)
        key = (directory, template)
        if not known_sweeps.has_key(key):
            sweeplist = SweepFactory(template, directory)
            known_sweeps[key] = sweeplist

    except exceptions.Exception, e:
        print 'Exception: %s' % str(e)

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

            if len(s.get_images()) < 5:
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
            if len(s.get_images()) < 5:
                continue

            j += 1
            name = 'SWEEP%d' % j

            out.write('BEGIN SWEEP %s\n' % name)
            out.write('WAVELENGTH %s\n' % wavelength_map[s.get_wavelength()])
            
            out.write('DIRECTORY %s\n' % s.get_directory())
            out.write('IMAGE %s\n' % os.path.split(s.imagename(min(
                s.get_images())))[-1])
            out.write('START_END %d %d\n' % (min(s.get_images()),
                                             max(s.get_images())))
            out.write('EPOCH %d\n' % int(s.get_collect()[0]))
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

def write_xinfo(filename, path):
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
        
    os.chdir(directory)

    rummage(path)
    fout = open(filename, 'w')
    print_sweeps(fout)
    

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




