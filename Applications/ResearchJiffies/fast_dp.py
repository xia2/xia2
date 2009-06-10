#!/usr/bin/env python
# fast_dp.py
# 
# A *quick* data reduction jiffy, for the purposes of providing an estimate
# of the quality of a data set as fast as possible. This will mainly use
# XDS (in parallel mode) but will build on some of the stuff developed for
# xia2. N.B. the main steps are:
# 
#  - parse command line of fast_dp -beam x,y /my/first/image_001.img
#  - diffdump first frame; generate XDS.INP
#  - run XDS XYCORR INIT COLSPOT IDXREF DEFPIX INTEGRATE CORRECT all in P1
#    N.B. CORRECT will select it's own "correct" solution.
#  - Decide a resolution limit
#  - Rerun CORRECT
#  - Pointless the data to mtz format, merge with Scala
#  - Report the summary data to the user
#
# This will use the Python "subprocess" module, hopefully not a lot else.
# Not sure of the best way to estimate the resolution limit fast, as this
# should be moderately accurate, but fitting to the reflections in
# XDS_ASCII.HKL is rather slow...

import sys
import subprocess
import sys
import re
import os
import string

def run_job(executable, arguments, stdin):
    '''Run a program with some command-line arguments and some input,
    then return the standard output when it is finished.'''


    command_line = '%s' % executable
    for arg in arguments:
        command_line += ' "%s"' % arg

    popen = subprocess.Popen(command_line,
                             bufsize = 1,
                             stdin = subprocess.PIPE,
                             stdout = subprocess.PIPE,
                             stderr = subprocess.STDOUT,
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
    regexp_text = re.escape(template).replace('\\#' * length,
                                              '([0-9]{%d})' % length)
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

def read_command_line():
    '''Read the command line and the image header of the first image found.
    Return a list of matching images (i.e. the start and end of the sweep)
    and if the beam is updated on the command line then include this too.
    N.B. this beam centre is in the Mosflm reference frame.'''

    image = sys.argv[-1]

    dd_output = run_job('diffdump', [image], [])

    # from this output populate the metadata structure

    metadata = { }

    for record in dd_output:
        if 'Wavelength' in record:
            wavelength = float(record.split()[-2])
            metadata['wavelength'] = wavelength
        elif 'Beam center' in record:
            x = float(record.replace('(', ' ').replace(
                'mm', ' ').replace(',', ' ').split()[3])
            y = float(record.replace('(', ' ').replace(
                'mm', ' ').replace(',', ' ').split()[4])
            metadata['beam'] = x, y
        elif 'Image Size' in record:
            x = int(record.replace('(', ' ').replace(
                'px', ' ').replace(',', ' ').split()[3])
            y = int(record.replace('(', ' ').replace(
                'px', ' ').replace(',', ' ').split()[4])
            metadata['size'] = x, y
        elif 'Pixel Size' in record:
            x = float(record.replace('(', ' ').replace(
                'mm', ' ').replace(',', ' ').split()[3])
            y = float(record.replace('(', ' ').replace(
                'mm', ' ').replace(',', ' ').split()[4])
            metadata['pixel'] = x, y
        elif 'Distance' in record:
            distance = float(record.split()[-2])
            metadata['distance'] = distance
        elif 'Oscillation' in record:
            phi_start = float(record.split()[3])
            phi_end = float(record.split()[5])
            phi_width = phi_end - phi_start
            if phi_width > 360.0:
                phi_width -= 360.0
            metadata['oscillation'] = phi_start, phi_width

    # now parse the image filename for the template and so on

    template, directory = image2template_directory(image)
    matching = find_matching_images(template, directory)

    # check that all of the images are present

    for j in range(min(matching), max(matching)):
        if not j in matching:
            raise RuntimeError, 'image %d missing' % j

    metadata['directory'] = directory
    metadata['template'] = template
    metadata['start'] = min(matching)
    metadata['end'] = max(matching)

    for token in metadata:
        print token, metadata[token]

if __name__ == '__main__':
    read_command_line()
           
