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
import time
import tempfile
import shutil

def run_job(executable, arguments = [], stdin = []):
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
    # FIXME there are probably several other tokens I should
    # check for in here
    
    if filename.count('#'):
        raise RuntimeError, '# characters in filename'

    # the patterns in the order I want to test them, for
    # future reference, these are RAW strings (hence "r")
    # which preserves the "\" &c.

    pattern_keys = [r'([^\.]*)\.([0-9]+)',
                    r'(.*)_([0-9]*)\.(.*)',
                    r'(.*?)([0-9]*)\.(.*)']

    # patterns is a dictionary of possible regular expressions with 
    # the format strings to put the file name back together
    # this would perhaps be better expressed as a list of
    # tuples (inc. above?)

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

    # perhaps this should be back-to-front i.e.
    # directory, template? Also rename the
    # method.

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

    return sorted(images)

# this should be called directory, template, number to image

def template_directory_number2image(template, directory, number):
    '''Construct the full path to an image from the template, directory
    and image number.'''

    length = template.count('#')

    # check that the number will fit in the template

    if number > (math.pow(10, length) - 1):
        raise RuntimeError, 'number too big for template'

    # construct a format statement to give the number part of the
    # template
    format = '%%0%dd' % length

    # construct the full image name
    image = os.path.join(directory,
                         template.replace('#' * length,
                                          format % number))

    return image

def get_number_cpus():
    '''Portably get the number of processor cores available.'''

    # Windows NT derived platforms

    if os.name == 'nt':
        return int(os.environ['NUMBER_OF_PROCESSORS'])
    
    # linux

    if os.path.exists('/proc/cpuinfo'):
        n_cpu = 0

        for record in open('/proc/cpuinfo', 'r').readlines():
            if not record.strip():
                continue
            if 'processor' in record.split()[0]:
                n_cpu += 1

        return n_cpu

    # os X

    output = subprocess.Popen(['system_profiler', 'SPHardwareDataType'],
                              stdout = subprocess.PIPE).communicate()[0]
    for record in output.split('\n'):
        if 'Total Number Of Cores' in record:
            return int(record.split()[-1])

    return -1

def spacegroup_number_to_name(spg_num):
    '''Convert a spacegroup number to a more readable name.'''

    database = { }

    assert('CLIBD' in os.environ)

    symop_lib = os.path.join(os.environ['CLIBD'], 'symop.lib')

    # The CCP4 (old style) symop.lib contains the
    # spacegroup information on the first line then
    # the corresponding symmetry operators preceeded
    # by spaces in subsequent lines

    for record in open(symop_lib, 'r').readlines():
        if ' ' in record[:1]:
            continue
        number = int(record.split()[0])
        name = record.split('\'')[1].strip()
        database[number] = name

    return database[spg_num]

def read_command_line():
    '''Read the command line and the image header of the first image found.
    Return a list of matching images (i.e. the start and end of the sweep)
    and if the beam is updated on the command line then include this too.
    N.B. this beam centre is in the Mosflm reference frame.'''

    image = sys.argv[-1]

    dd_output = run_job('diffdump', arguments = [image])

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
        elif 'Manufacturer' in record or 'Image type' in record:
            detector = record.split()[-1]
            if detector == 'ADSC':
                metadata['detector'] = detector
            elif detector == 'MAR':
                metadata['detector'] = 'CCDCHESS'
            else:
                raise RuntimeError, 'detector %s not yet supported' % detector

    # verify I have everything I expect (or need)

    assert('wavelength' in metadata)
    assert('beam' in metadata)
    assert('size' in metadata)
    assert('pixel' in metadata)
    assert('distance' in metadata)
    assert('oscillation' in metadata)
    assert('detector' in metadata) 

    # now parse the image filename for the template and so on

    template, directory = image2template_directory(image)
    matching = find_matching_images(template, directory)

    # check that all of the images are present

    missing = []
    for j in range(min(matching), max(matching)):
        if not j in matching:
            missing.append(j)

    if missing:
        raise RuntimeError, 'missing images: %s' % str(missing)

    metadata['directory'] = directory
    metadata['template'] = template
    metadata['start'] = min(matching)
    metadata['end'] = max(matching)

    # now check what is on the command-line

    if '-beam' in sys.argv:
        index = sys.argv.index('-beam') + 1
        x, y = tuple(map(float, sys.argv[index].split(',')))
        metadata['beam'] = x, y

    return metadata

# FIXME explain in here why there are two separate
# write_xds_inp_??? functions - autoindex, integrate
# two steps cos XDS is fussy.

def write_xds_inp_index(metadata):
    '''Write an XDS.INP file from the metadata obtained already. N.B. this
    will assume that the beam direction and rotation axis correspond to the
    usual definitions for ADSC images on beamlines.'''

    fout = open('XDS.INP', 'w')

    fout.write('JOB=XYCORR INIT COLSPOT IDXREF\n')
        
    fout.write('DETECTOR=%s MINIMUM_VALID_PIXEL_VALUE=1 OVERLOAD=65000\n' %
               metadata['detector'])
    fout.write('DIRECTION_OF_DETECTOR_X-AXIS= 1.0 0.0 0.0\n')
    fout.write('DIRECTION_OF_DETECTOR_Y-AXIS= 0.0 1.0 0.0\n')
    fout.write('TRUSTED_REGION=0.0 1.41\n')
    fout.write('MAXIMUM_NUMBER_OF_PROCESSORS=%d\n' % get_number_cpus())
    fout.write('NX=%d NY=%d QX=%.5f QY=%.5f\n' % \
               (metadata['size'][0], metadata['size'][1],
                metadata['pixel'][0], metadata['pixel'][1]))
     
    # N.B. assuming that the direct beam for XDS is the same as Mosflm,
    # with X, Y swapped and converted to pixels from mm.

    orgx = metadata['beam'][1] / metadata['pixel'][1]
    orgy = metadata['beam'][0] / metadata['pixel'][0]

    fout.write('ORGX=%.1f ORGY=%.1f\n' % (orgx, orgy))
    fout.write('ROTATION_AXIS= 1.0 0.0 0.0\n')
    fout.write('DETECTOR_DISTANCE=%.2f\n' % metadata['distance'])
    fout.write('X-RAY_WAVELENGTH=%.5f\n' % metadata['wavelength'])
    fout.write('OSCILLATION_RANGE=%.3f\n' % metadata['oscillation'][1])
    fout.write('INCIDENT_BEAM_DIRECTION=0.0 0.0 1.0\n')
    fout.write('FRACTION_OF_POLARIZATION=0.95\n')
    fout.write('POLARIZATION_PLANE_NORMAL=0.0 1.0 0.0\n')
    fout.write('FRIEDEL\'S_LAW=FALSE\n')
    fout.write('NAME_TEMPLATE_OF_DATA_FRAMES=%s\n' % \
               os.path.join(metadata['directory'],
                            metadata['template'].replace('#', '?')))
    fout.write('STARTING_ANGLE=%.3f STARTING_FRAME=%d\n' % \
               (metadata['oscillation'][0], metadata['start']))
    fout.write('DATA_RANGE=%d %d\n' % (metadata['start'],
                                       metadata['end']))

    # compute the background range as min(all, 5)

    if metadata['end'] - metadata['start'] > 5:
        fout.write('BACKGROUND_RANGE=%d %d\n' % (metadata['start'],
                                                 metadata['start'] + 5))
    else:
        fout.write('BACKGROUND_RANGE=%d %d\n' % (metadata['start'],
                                                 metadata['end']))

    # Three wedges, as per xia2... that would be 5 images per wedge, then.

    images = range(metadata['start'], metadata['end'] + 1)

    wedge = (images[0], images[0] + 4)
    fout.write('SPOT_RANGE=%d %d\n' % wedge)

    # if we have more than 90 degrees of data, use wedges at the start,
    # 45 degrees in and 90 degrees in, else use a wedge at the start,
    # one in the middle and one at the end.

    if int(90.0 / metadata['oscillation'][1]) + 4 in images:
        wedge = (int(45.0 / metadata['oscillation'][1]), 
                 int(45.0 / metadata['oscillation'][1]) + 4)
        fout.write('SPOT_RANGE=%d %d\n' % wedge)
        wedge = (int(90.0 / metadata['oscillation'][1]), 
                 int(90.0 / metadata['oscillation'][1]) + 4)
        fout.write('SPOT_RANGE=%d %d\n' % wedge)
    else:
        mid = (len(images) / 2) - 4 + (images[0] - 1)
        wedge = (mid, mid + 4)
        fout.write('SPOT_RANGE=%d %d\n' % wedge)
        wedge = (images[-5], images[-1])
        fout.write('SPOT_RANGE=%d %d\n' % wedge)
        
    fout.close()

    return

def write_xds_inp_integrate(metadata, resolution = None):
    '''Write an XDS.INP file from the metadata obtained already. N.B. this
    will assume that the beam direction and rotation axis correspond to the
    usual definitions for ADSC images on beamlines.'''

    fout = open('XDS.INP', 'w')

    # at the end I rerun CORRECT to trim back the resolution
    # limit - ergo if I know the resolution limit I only
    # want to run CORRECT.

    if not resolution is None:
        fout.write('JOB=CORRECT\n')
    else:
        fout.write('JOB=DEFPIX INTEGRATE CORRECT\n')
        
    fout.write('DETECTOR=%s MINIMUM_VALID_PIXEL_VALUE=1 OVERLOAD=65000\n' %
               metadata['detector'])
    fout.write('DIRECTION_OF_DETECTOR_X-AXIS= 1.0 0.0 0.0\n')
    fout.write('DIRECTION_OF_DETECTOR_Y-AXIS= 0.0 1.0 0.0\n')
    fout.write('TRUSTED_REGION=0.0 1.41\n')
    fout.write('MAXIMUM_NUMBER_OF_PROCESSORS=%d\n' % get_number_cpus())
    fout.write('NX=%d NY=%d QX=%.5f QY=%.5f\n' % \
               (metadata['size'][0], metadata['size'][1],
                metadata['pixel'][0], metadata['pixel'][1]))
     
    # N.B. assuming that the direct beam for XDS is the same as Mosflm,
    # with X, Y swapped and converted to pixels from mm.

    orgx = metadata['beam'][1] / metadata['pixel'][1]
    orgy = metadata['beam'][0] / metadata['pixel'][0]

    fout.write('ORGX=%.1f ORGY=%.1f\n' % (orgx, orgy))
    fout.write('ROTATION_AXIS= 1.0 0.0 0.0\n')
    fout.write('DETECTOR_DISTANCE=%.2f\n' % metadata['distance'])
    fout.write('X-RAY_WAVELENGTH=%.5f\n' % metadata['wavelength'])
    fout.write('OSCILLATION_RANGE=%.3f\n' % metadata['oscillation'][1])
    fout.write('INCIDENT_BEAM_DIRECTION=0.0 0.0 1.0\n')
    fout.write('FRACTION_OF_POLARIZATION=0.95\n')
    fout.write('POLARIZATION_PLANE_NORMAL=0.0 1.0 0.0\n')
    fout.write('FRIEDEL\'S_LAW=FALSE\n')
    fout.write('NAME_TEMPLATE_OF_DATA_FRAMES=%s\n' % \
               os.path.join(metadata['directory'],
                            metadata['template'].replace('#', '?')))
    fout.write('STARTING_ANGLE=%.3f STARTING_FRAME=%d\n' % \
               (metadata['oscillation'][0], metadata['start']))
    fout.write('DATA_RANGE=%d %d\n' % (metadata['start'],
                                       metadata['end']))

    # compute the background range as min(all, 5)

    if metadata['end'] - metadata['start'] > 5:
        fout.write('BACKGROUND_RANGE=%d %d\n' % (metadata['start'],
                                                 metadata['start'] + 5))
    else:
        fout.write('BACKGROUND_RANGE=%d %d\n' % (metadata['start'],
                                                 metadata['end']))

    if not resolution is None:
        fout.write('INCLUDE_RESOLUTION_RANGE=30.0 %.2f\n' % resolution)
    else:
        fout.write('INCLUDE_RESOLUTION_RANGE=30.0 0.0\n')

    fout.close()

    return

def read_correct_lp_get_resolution():
    '''Read the CORRECT.LP file and get an estimate of the resolution limit.
    This should then be recycled to a rerun of CORRECT, from which the
    reflections will be merged to get the statistics.'''

    correct_lp = open('CORRECT.LP', 'r').readlines()

    rec = -1

    # FIXME explain what is happening here...

    for j, record in enumerate(correct_lp):

        if 'RESOLUTION RANGE  I/Sigma  Chi^2  R-FACTOR  R-FACTOR' in record:
            rec = j + 3
            break

    if rec < 0:
        raise RuntimeError, 'resolution information not found'

    j = rec

    while not '--------' in correct_lp[j]:
        isigma = float(correct_lp[j].split()[2])
        if isigma < 1:
            return float(correct_lp[j].split()[1])
        j += 1

    # this will assume that strong reflections go to the edge of the detector
    # => do not need to feed back a resolution limit...

    return None

def merge():
    '''Merge the symmetry related reflections from XDS_ASCII.HKL
    to get some statistics - this will use pointless for the reflection file
    format mashing.'''

    # first convert the file format - this could be recoded with CCTBX
    # python code I guess...

    run_job('pointless-1.2.23',
            ['-c', 'xdsin', 'XDS_ASCII.HKL', 'hklout', 'xds_sorted.mtz'])

    # then merge - N.B. the scaling commands are version specific, and
    # what is coded below corresponds to the 6.0.2 version of Scala...

    log = run_job('scala',
                  ['hklin', 'xds_sorted.mtz', 'hklout', 'fast_dp.mtz'],
                  ['bins 20', 'run 1 all', 'scales constant', 'anomalous on',
                   'sdcorrection both 1.0 0.0 0.0'])

    # now write out the full log file from the merging

    fout = open('scala.log', 'w')
    for record in log:
        fout.write(record)
    fout.close()

    do_print = False

    result_records = []

    for record in log:
        
        if 'Summary data for' in record:
            do_print = True
            continue

        if do_print:
            result_records.append(record[:-1])

        if 'Average mosaicity' in record:
            do_print = False

        if '==========' in record:
            do_print = False
            
    return result_records

def help():
    '''Some help for the user.'''

    sys.stderr.write('%s [-beam x,y] /first/image/in/sweep_001.img\n' % \
                     sys.argv[0])
    sys.exit(0)

def main():
    '''Main program - chain together all of the above steps.'''

    starting_directory = os.getcwd()
    
    start_time = time.time()
    step_time = time.time()

    print os.environ['CCP4']

    print 'Generating metadata'
    metadata = read_command_line()

    # FIXME this *could* be less ugly...
    # run in /tmp, then zip to foo_.dir below
    # => have a record but it wasn't really
    # running in a data directory honest gov.

    # working_directory = tempfile.mkdtemp()
    working_directory = os.path.join(
        metadata['directory'], '%s.dir' % metadata['template'].split('#')[0])

    # check if the directory exists first, perhaps,
    # then don't pass the exception.
    
    try:
        os.makedirs(working_directory)
    except OSError, e:
        pass

    print 'Running in %s' % working_directory
    
    os.chdir(working_directory)

    print 'Indexing...'
    write_xds_inp_index(metadata)
    xds_output = run_job('xds_par')

    duration = time.time() - step_time

    print 'Processing took %s' % time.strftime('%Hh %Mm %Ss',
                                               time.gmtime(duration))
    
    step_time = time.time()

    print 'Integrating...'
    write_xds_inp_integrate(metadata)
    xds_output = run_job('xds_par')
    resolution = read_correct_lp_get_resolution()

    duration = time.time() - step_time

    print 'Processing took %s' % time.strftime('%Hh %Mm %Ss',
                                               time.gmtime(duration))
    
    if not resolution is None:
        print 'Rescaling to %.2fA...' % resolution
        step_time = time.time()
        
        write_xds_inp_integrate(metadata, resolution = resolution)
        xds_output = run_job('xds_par')
        
        duration = time.time() - step_time
        
        print 'Processing took %s' % time.strftime('%Hh %Mm %Ss',
                                                   time.gmtime(duration))

    print 'Merging...'
    result_records = merge()

    # write these out as a log from the program
    # perhaps should be a write_log_file method?

    fout = open('fast_dp.log', 'w')
    
    for record in result_records:
        print record
        fout.write('%s\n' % record)

    duration = time.time() - start_time

    # pull some more results to put in the log file

    gxparm = open('GXPARM.XDS', 'r').readlines()
    spacegroup = spacegroup_number_to_name(int(gxparm[7].split()[0]))
    cell = tuple(map(float, gxparm[7].split()[1:]))

    print 'Pointgroup: %s' % spacegroup
    print 'Cell: %9.3f%9.3f%9.3f%9.3f%9.3f%9.3f' % cell

    print 'Processed %d images' % (metadata['end'] - metadata['start'] + 1)
    print 'All processing took %d (%s)' % \
          (int(duration), time.strftime('%Hh %Mm %Ss', time.gmtime(duration)))

    fout.write('Pointgroup: %s\n' % spacegroup)
    fout.write('Cell: %9.3f%9.3f%9.3f%9.3f%9.3f%9.3f\n' % cell)

    fout.write('Processed %d images in %d (%s)\n' % \
               (metadata['end'] - metadata['start'] + 1,
                int(duration), time.strftime('%Hh %Mm %Ss',
                                             time.gmtime(duration))))
    
    fout.close()

    # FIXME in here check that these files EXIST before copying -
    # sometimes they don't which indicates that something
    # went wrong... that said, I should have trapped that
    # earlier on.

    for filename in ['fast_dp.log', 'scala.log',
                     'CORRECT.LP', 'fast_dp.mtz']:

        shutil.copyfile(filename, os.path.join(starting_directory,
                                               filename))

    os.chdir(starting_directory)
    
if __name__ == '__main__':

    if len(sys.argv) < 2:
        help()
    else:
        main()
