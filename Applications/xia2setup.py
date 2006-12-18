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

latest_chooch = None

def is_scan_name(file):
    global known_scan_extensions

    if os.path.isfile(file):
        if file.split('.')[-1] in known_scan_extensions:
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

def visit(root, directory, files):
    files.sort()
    for f in files:
        get_sweep(os.path.join(directory, f))

        if is_scan_file(os.path.join(directory, f)):
            global latest_chooch
            latest_chooch = Chooch()
            latest_chooch.set_scan(os.path.join(directory, f))
            latest_chooch.scan()
        
def print_sweeps():

    global known_sweeps
    
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

    print 'BEGIN PROJECT AUTOMATIC'
    print 'BEGIN CRYSTAL DEFAULT'

    print ''
    
    for j in range(len(wavelengths)):

        global latest_chooch

        if latest_chooch:
            name = chooch.id_wavelength[wavelengths[j]]
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

    print 'END CRYSTAL DEFAULT'
    print 'END PROJECT AUTOMATIC'

if __name__ == '__main__':

    argv = sys.argv

    # test to see if sys.argv[-2] + path is a valid path - to work around
    # spaced command lines

    path = argv.pop()

    while not os.path.exists(path):
        path = '%s %s' % (argv.pop(), path)

    if not os.path.isabs(path):
        path = os.path.abspath(path)

    os.path.walk(path, visit, os.getcwd())

    print_sweeps()




