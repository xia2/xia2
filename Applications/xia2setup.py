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

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'
if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

from Schema.Sweep import SweepFactory
from Experts.FindImages import image2template_directory
from Handlers.CommandLine import CommandLine
from Wrappers.CCP4.Chooch import Chooch

known_image_extensions = ['img', 'mccd', 'mar2300', 'osc', 'cbf']
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
            
def print_sweeps():

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

            if len(s.get_images()) < 25:
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

    print 'BEGIN PROJECT %s' % project
    print 'BEGIN CRYSTAL %s' % crystal

    print ''

    if latest_sequence:
        print 'BEGIN AA_SEQUENCE'
        print ''
        for sequence_chunk in [latest_sequence[i:i + 60] \
                               for i in range(0, len(latest_sequence), 60)]:
            print sequence_chunk
        print ''
        print 'END AA_SEQUENCE'        
        print ''

    if CommandLine.get_atom_name():
        print 'BEGIN HA_INFO'
        print 'ATOM %s' % CommandLine.get_atom_name().lower()
        if CommandLine.get_atom_name().lower() == 'se' and latest_sequence:
            # assume that this is selenomethionine
            print '! If this is SeMet uncomment next line...'
            print '!NUMBER_PER_MONOMER %d' % latest_sequence.count('M')
            print '!NUMBER_TOTAL M'
        else:
            print '!NUMBER_PER_MONOMER N'
            print '!NUMBER_TOTAL M'
        print 'END HA_INFO'
        print ''
    
    for j in range(len(wavelengths)):

        global latest_chooch

        if latest_chooch:
            name = latest_chooch.id_wavelength(wavelengths[j])
        else:
            if len(wavelengths) == 1 and CommandLine.get_atom_name():
                name = 'SAD'
            elif len(wavelengths) == 1:
                name = 'NATIVE'
            else:
                name = 'WAVE%d' % (j + 1)
                
        wavelength_map[wavelengths[j]] = name
        
        print 'BEGIN WAVELENGTH %s' % name
        print 'WAVELENGTH %f' % wavelengths[j]
        print 'END WAVELENGTH %s' % name
        print ''

    j = 0
    for sweep in sweeplists:
        sweeps = known_sweeps[sweep]
        # this should sort on exposure epoch ...?
        sweeps.sort()
        for s in sweeps:
            if len(s.get_images()) < 25:
                continue

            j += 1
            name = 'SWEEP%d' % j

            print 'BEGIN SWEEP %s' % name
            print 'WAVELENGTH %s' % wavelength_map[s.get_wavelength()]
            
            print 'DIRECTORY %s' % s.get_directory()
            print 'IMAGE %s' % os.path.split(s.imagename(min(
                s.get_images())))[-1]
            print 'EPOCH %d' % int(s.get_collect()[0])
            cl_beam = CommandLine.get_beam()
            if cl_beam[0] or cl_beam[1]:
                print 'BEAM %f %f' % cl_beam
            else:
                print 'BEAM %f %f' % tuple(s.get_beam())
            print 'END SWEEP %s' % name

            print ''

    print 'END CRYSTAL %s' % crystal
    print 'END PROJECT %s' % project

if __name__ == '__main__':

    argv = sys.argv

    # test to see if sys.argv[-2] + path is a valid path - to work around
    # spaced command lines

    path = argv.pop()

    # perhaps move to a new directory...

    crystal = CommandLine.get_crystal_name()

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

    os.path.walk(path, visit, os.getcwd())

    print_sweeps()




