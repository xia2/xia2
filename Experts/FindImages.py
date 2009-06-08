#!/usr/bin/env python
# FindImages.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 9th June 2006
# 
# A set of routines for finding images and the like based on file names.
# This includes all of the appropriate handling for templates, directories
# and the like.
#
# 15/JUN/06 
# 
# Also routines for grouping sets of images together into sweeps based on 
# the file names and the information in image headers.
# 
# FIXME 24/AUG/06 this needs to renamed to something a little more obvious
#                 than FindImages - perhaps ImageExpert?
# FIXME 04/OCT/06 when the image name is all numbers like 999_1_001 need to 
#                 assume that the extension is the number, BEFORE testing any
#                 of the ther possibilities...
# 
# 
# 

import sys
import os
import re
import string
import math
import copy

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Handlers.Streams import Debug

def image2template(filename):
    '''Return a template to match this filename.'''

    # check that the file name doesn't contain anything mysterious
    if filename.count('#'):
        raise RuntimeError, '# characters in filename'

    # the patterns in the order I want to test them

    pattern_keys = [r'([^\.]*)\.([0-9]+)',
                    r'(.*)_([0-9]*)\.(.*)',
                    r'(.*?)([0-9]*)\.(.*)']

    # patterns is a dictionary of possible regular expressions with
    # the format strings to put the file name back together

    patterns = {r'([^\.]*)\.([0-9]+)':'%s.%s%s',
                r'(.*)_([0-9]*)\.(.*)':'%s_%s.%s',
                r'(.*?)([0-9]*)\.(.*)':'%s%s.%s'}

    for pattern in pattern_keys:
        match = re.compile(pattern).match(filename)

        if match:
            prefix = match.group(1)
            number = match.group(2)
            try:
                exten = match.group(3)
            except:
                exten = ''

            for digit in string.digits:
                number = number.replace(digit, '#')
                
            return patterns[pattern] % (prefix, number, exten)

    raise RuntimeError, 'filename %s not understood as a template' % \
          filename

def image2image(filename):
    '''Return an integer for the template to match this filename.'''

    # check that the file name doesn't contain anything mysterious
    if filename.count('#'):
        raise RuntimeError, '# characters in filename'

    # the patterns in the order I want to test them

    pattern_keys = [r'([^\.]*)\.([0-9]+)',
                    r'(.*)_([0-9]*)\.(.*)',
                    r'(.*?)([0-9]*)\.(.*)']

    for pattern in pattern_keys:
        match = re.compile(pattern).match(filename)

        if match:
            prefix = match.group(1)
            number = match.group(2)
            try:
                exten = match.group(3)
            except:
                exten = ''

            return int(number)

    raise RuntimeError, 'filename %s not understood as a template' % \
          filename

def image2template_directory(filename):
    '''Separate out the template and directory from an image name.'''

    directory = os.path.dirname(filename)

    if not directory:
        
        # then it should be the current working directory
        directory = os.getcwd()
        
    image = os.path.split(filename)[-1]
    template = image2template(image)

    return template, directory

def find_matching_images(template, directory):
    '''Find images which match the input template in the directory
    provided.'''

    files = os.listdir(directory)

    # to turn the template to a regular expression want to replace
    # however many #'s with EXACTLY the same number of [0-9] tokens,
    # e.g. ### -> ([0-9]{3})

    # change 30/may/2008 - now escape the template in this search to cope with
    # file templates with special characters in them, such as "+" -
    # fix to a problem reported by Joel B.
    
    length = template.count('#')
    regexp_text = re.escape(template).replace('\\#' * length, '([0-9]{%d})' % length)
    regexp = re.compile(regexp_text)

    images = []

    for f in files:
        match = regexp.match(f)

        if match:
            images.append(int(match.group(1)))

    images.sort()

    return images

def template_directory_number2image(template, directory, number):
    '''Construct the full path to an image from the template, directory
    and image number.'''

    length = template.count('#')

    # check that the number will fit in the template

    if (math.pow(10, length) - 1) < number:
        raise RuntimeError, 'number too big for template'

    # construct a format statement to give the number part of the
    # template
    format = '%%0%dd' % length

    # construct the full image name
    image = os.path.join(directory,
                         template.replace('#' * length,
                                          format % number))

    return image

def headers2sweep_ids(header_dict):
    '''Get a list of sweep ids (first images) from the header list.'''

    sweeps = headers2sweeps(header_dict)

    ids = []

    for s in sweeps:
        ids.append(min(s['images']))

    return ids

def headers2sweeps(header_dict):
    '''Parse a dictionary of headers to produce a list of summaries.'''

    images = header_dict.keys()
    images.sort()

    if len(images) == 0:
        return []

    sweeps = []

    current_sweep = copy.deepcopy(header_dict[images[0]])
    
    current_sweep['images'] = [images[0]]
    current_sweep['collect_start'] = current_sweep['epoch']
    current_sweep['collect_end'] = current_sweep['epoch']

    for i in images[1:]:
        header = header_dict[i]

        # if wavelength the same and distance the same and this image
        # follows in phi from the previous chappie then this is the
        # next frame in the sweep. otherwise it is the first frame in
        # a new sweep.

        delta_lambda = math.fabs(
            header['wavelength'] - current_sweep['wavelength'])
        delta_distance = math.fabs(
            header['distance'] - current_sweep['distance'])
        delta_phi = math.fabs(
            header['phi_start'] - current_sweep['phi_end']) % 360.0

        # Debug.write('Image %d %f %f %f' % \
        # (i, delta_lambda, delta_distance,
        # min(delta_phi, 360.0 - delta_phi)))

        if delta_lambda < 0.0001 and \
               delta_distance < 0.01 and \
               min(delta_phi, 360.0 - delta_phi) < 0.01:
            # this is another image in the sweep
            # Debug.write('Image %d belongs to the sweep' % i)
            current_sweep['images'].append(i)
            current_sweep['phi_end'] = header['phi_end']
            current_sweep['collect_end'] = header['epoch']
        else:
            Debug.write('Image %d starts a new sweep' % i)
            sweeps.append(current_sweep)
            current_sweep = header_dict[i]
            current_sweep['images'] = [i]
            current_sweep['collect_start'] = current_sweep['epoch']
            current_sweep['collect_end'] = current_sweep['epoch']

    sweeps.append(current_sweep)

    return sweeps

def common_prefix(strings):
    '''Find a common prefix among the list of strings. May return an empty
    string. This is O(n^2).'''

    common = strings[0]
    finished = False

    while not finished:

        finished = True
        for s in strings:
            if not common == s[:len(common)]:
                common = common[:-1]
                finished = False
                continue
            
    return common

def digest_template(template, images):
    '''Digest the template and image numbers to copy as much of the
    common characters in the numbers as possible to the template to
    give smaller image numbers.'''

    length = template.count('#')

    format = '%%0%dd' % length

    strings = [format % i for i in images]

    prefix = common_prefix(strings)
    offset = 0

    if prefix:
        offset = int(prefix + '0' * (length - len(prefix)))
        template = template.replace(len(prefix) * '#', prefix, 1)
        images = [int(s.replace(prefix, '', 1)) for s in strings]

    return template, images, offset
    
if __name__ == '__main__':

    if len(sys.argv) < 2:
        raise RuntimeError, '%s image_001.img' % sys.argv[0]

    head, tail = os.path.split(sys.argv[1])

    if not head:
        head = os.getcwd()

    template = image2template(tail)

    print 'template: %s' % template

    images = find_matching_images(template, head)

    print 'images:   %d to %d' % (min(images), max(images))

    template, images, offset = digest_template(template, images)
    
    print 'offset:   %d' % offset
