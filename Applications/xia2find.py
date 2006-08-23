#!/usr/bin/env python
# xia2find.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
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
# 23/AUG/06 FIXME (1) need to print out the exposure time
#                 (2) need to print out the exposure epoch in a human 
#                     readable way - this is done with time.ctime()
# 
# 
# 

import sys
import os
import exceptions
import time

if not os.environ.has_key('DPA_ROOT'):
    raise RuntimeError, 'DPA_ROOT not defined'
if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['DPA_ROOT']))

from Schema.Sweep import SweepFactory
from Experts.FindImages import image2template_directory

known_image_extensions = ['img', 'mccd', 'mar2300', 'osc', 'cbf']
known_sweeps = { }

def is_image_name(file):

    global known_image_extensions
    
    if os.path.isfile(file):
        if file.split('.')[-1] in known_image_extensions:
            return True

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
            print 'Sweep: %s' % os.path.join(s.getDirectory(), s.getTemplate())
            print 'Images: %d to %d' % (min(s.getImages()), max(s.getImages()))
            print 'Detector class: %s' % s.getDetector_class()
            print 'Epoch from/to: %d %d' % tuple(map(int,
                                                     s.getCollect()))
            collect_time = map(time.ctime, s.getCollect())
            print 'Collected from: %s' % collect_time[0]
            print '            to: %s' % collect_time[1]
            print 'Wavelength: %f' % s.getWavelength()
            print 'Distance: %f' % s.getDistance()
            print 'Exposure time: %f' % s.getExposure_time()
            print 'Beam: %f %f' % tuple(s.getBeam())
            print 'Oscillations: %f to %f (%f)' % tuple(s.getPhi())
            print ''

if __name__ == '__main__':

    if len(sys.argv) < 2:
        os.path.walk(os.getcwd(), visit, os.getcwd())
    else:
        os.path.walk(sys.argv[1], visit, os.getcwd())

    print_sweeps()
