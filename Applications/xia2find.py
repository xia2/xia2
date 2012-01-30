#!/usr/bin/env python
# xia2find.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 12th July 2006
#
# A small program to find diffraction data sets as "sweeps" and print
# out the results.
#
# 13/JUL/06 Change: Is it better to compile a list of files first, then
# sort this into templates &c; then compile this into sweeps? Could then
# also decide how much time to devote to the accurate identification of
# sweeps... FIXME this needs to be thought about/implemented.
#
# 23/AUG/06 FIXED (1) need to print out the exposure time
#                 (2) need to print out the exposure epoch in a human
#                     readable way - this is done with time.ctime()
#
# 25/SEP/06 FIXED also need to be able to handle images like blah_foo.0001
#                 since this is a reasonably common way of collecting frames.

import sys
import os
import exceptions
import time

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'
if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

from Schema.Sweep import SweepFactory
from Experts.FindImages import image2template_directory

known_image_extensions = ['img', 'mccd', 'mar2300', 'mar1200', 'mar3450',
                          'osc', 'cbf', 'mar2000']]
known_sweeps = { }

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
    for f in files:
        get_sweep(os.path.join(directory, f))

def print_sweeps():

    global known_sweeps

    sweeplists = known_sweeps.keys()
    sweeplists.sort()

    for sweep in sweeplists:
        sweeps = known_sweeps[sweep]
        # this should sort on exposure epoch ...?
        sweeps.sort()
        for s in sweeps:
            print 'Sweep: %s' % os.path.join(s.get_directory(),
                                             s.get_template())
            print 'Images: %d to %d' % (min(s.get_images()),
                                        max(s.get_images()))
            print 'Detector class: %s' % s.get_detector_class()
            print 'Epoch from/to: %d %d' % tuple(map(int,
                                                     s.get_collect()))
            collect_time = map(time.ctime, s.get_collect())
            print 'Collected from: %s' % collect_time[0]
            print '            to: %s' % collect_time[1]
            print 'Wavelength: %f' % s.get_wavelength()
            print 'Distance: %f' % s.get_distance()
            print 'Exposure time: %f' % s.get_exposure_time()
            print 'Beam: %f %f' % tuple(s.get_beam())
            print 'Oscillations: %f to %f (%f)' % tuple(s.get_phi())
            print ''

if __name__ == '__main__':

    if len(sys.argv) < 2:
        os.path.walk(os.getcwd(), visit, os.getcwd())
    else:
        os.path.walk(sys.argv[1], visit, os.getcwd())

    print_sweeps()
