#!/usr/bin/env python
# DoseAccumulate.py
#   Copyright (C) 2007 STFC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# A module to determine the accumulated dose as a function of exposure epoch
# for a given set of images, assuming:
# 
# (i)  the set is complete
# (ii) the set come from a single (logical) crystal
#
# This is to work with fortran program "doser" and also to help fix 
# Bug # 2798.
#

import os, sys

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT undefined'

if not os.environ['XIA2_ROOT'] is sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Wrappers.XIA.Diffdump import Diffdump

def accumulate(images):
    '''Accumulate dose as a function of image epoch.'''

    dose = { }
    integrated_dose = { }

    for i in images:
        dd = Diffdump()
        dd.set_image(i)
        header = dd.readheader()

        d = header['exposure_time']
        e = header['epoch']

        dose[e] = d

    keys = dose.keys()

    keys.sort()

    accum = 0.0

    for k in keys:
        integrated_dose[k] = accum + 0.5 * dose[k]
        accum += dose[k]

    return integrated_dose

if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise RuntimeError, '%s /path/to/image' % sys.argv[0]

    from Experts.FindImages import find_matching_images, \
         template_directory_number2image, image2template_directory

    image = sys.argv[1]

    template, directory = image2template_directory(image)
    images = find_matching_images(template, directory)
    image_names = []
    for i in images:
        image_names.append(template_directory_number2image(
            template, directory, i))

    dose = accumulate(image_names)
    epochs = dose.keys()
    epochs.sort()

    for e in epochs:
        print e, dose[e]
    

                   
