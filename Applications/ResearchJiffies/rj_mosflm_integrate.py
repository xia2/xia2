from rj_lib_find_images import rj_get_template_directory, \
     rj_find_matching_images, rj_get_phi, rj_image_name

from rj_lib_run_job import rj_run_job

from rj_no_images import calculate_images as calculate_images_ai
from rj_cr_n_wedges import calculate_images as calculate_images_cr

import shutil
import sys
import os
import time

def do_scale_merge(hklin, resolution):
    '''Do the scaling and merging which is needed, return the Rmerge record
    from the end of the log file. And the hklout spacegroup.'''

    output = rj_run_job('pointless',
                        ['hklin', hklin, 'hklout', 'sorted.mtz'],
                        ['systematicabsences off'])

    # get the spacegroup for hklout from this

    spacegroup = None

    for record in output:
        if 'Best Solution' in record and 'point group' in record:
            spacegroup = record.split('group')[1].strip().replace(' ', '')

    assert(spacegroup)

    output = rj_run_job('scala',
                        ['hklin', 'sorted.mtz', 'hklout', 'scaled.mtz'],
                        ['run 1 all',
                         'scales rotation spacing 5 secondary 6 bfactor on',
                         'anomalous on',
                         'resolution %.3f' % resolution,
                         'cycles 10'])

    # now read through this to get the Rmerge out: also check the
    # status at the end of the program

    status = None

    for record in output[-10:]:
        if 'Scala:' in record:
            status = record.replace('Scala:', '').replace('*', '').strip()

    assert(status)

    rmerges = None

    for record in output[-100:]:
        if 'Rmerge' in record and not 'intensity' in record:
            rmerges = map(float, record.split()[-3:])

    assert(rmerges)

    return rmerges, spacegroup

def mosflm_reference(template, directory, beam, distance, start, end,
                     resolution, symmetry, gain, ai_images, cr_images):

    # first test: what andrew says - this should be the reference...

    # first the autoindexing spell

    commands = [
        'directory %s' % directory,
        'template %s' % template,
        'beam %.2f %.2f' % beam,
        'distance %.2f' % distance
        ]

    if gain:
        commands.append('gain %.3f' % gain)

    commands.append('symmetry %d' % symmetry)

    for ai in ai_images:
        commands.append('autoindex dps refine image %d' % ai)

    commands.append('mosaic estimate')
    commands.append('go')

    # then the cell refinement spell

    commands.append('postref multi segments %d' % len(cr_images))

    for cr in cr_images:
        commands.append('process %d %d' % cr)
        commands.append('go')

    # then the integration spell

    commands.append('postref fix all')
    commands.append('hklout integrate.mtz')
    commands.append('process %d %d' % (start, end))
    commands.append('go')

    output = rj_run_job('ipmosflm', [], commands)

    # should check that the status here was correct

    # now merge

    rmerges, spacegroup = do_scale_merge('integrate.mtz', resolution)

    # now print where we're at...

    print 'Reference:  %.3f %.3f %.3f %s' % (rmerges[0], rmerges[1],
                                             rmerges[2], spacegroup)

def mosflm_resolution(template, directory, beam, distance, start, end,
                      resolution, symmetry, gain, ai_images, cr_images):

    # first test: what andrew says - this should be the reference...

    # first the autoindexing spell

    commands = [
        'directory %s' % directory,
        'template %s' % template,
        'beam %.2f %.2f' % beam,
        'distance %.2f' % distance
        ]

    if gain:
        commands.append('gain %.3f' % gain)

    commands.append('symmetry %d' % symmetry)

    for ai in ai_images:
        commands.append('autoindex dps refine image %d' % ai)

    commands.append('mosaic estimate')
    commands.append('go')

    # then the cell refinement spell

    commands.append('postref multi segments %d' % len(cr_images))

    for cr in cr_images:
        commands.append('process %d %d' % cr)
        commands.append('go')

    # then the integration spell

    commands.append('postref fix all')
    commands.append('resolution %.2f' % resolution)
    commands.append('hklout integrate.mtz')
    commands.append('process %d %d' % (start, end))
    commands.append('go')

    output = rj_run_job('ipmosflm', [], commands)

    # should check that the status here was correct

    # now merge

    rmerges, spacegroup = do_scale_merge('integrate.mtz', resolution)

    # now print where we're at...

    print 'Resolution: %.3f %.3f %.3f %s' % (rmerges[0], rmerges[1],
                                             rmerges[2], spacegroup)

def mosflm_dumb(template, directory, beam, distance, start, end,
                resolution, symmetry, gain, ai_images, cr_images):

    # dumb - no cell refinement, let mosflm choose &c.

    # first the autoindexing spell

    commands = [
        'directory %s' % directory,
        'template %s' % template,
        'beam %.2f %.2f' % beam,
        'distance %.2f' % distance
        ]

    if gain:
        commands.append('gain %.3f' % gain)

    for ai in ai_images:
        commands.append('autoindex dps refine image %d' % ai)

    commands.append('mosaic estimate')
    commands.append('go')

    commands.append('hklout integrate.mtz')
    commands.append('process %d %d' % (start, end))
    commands.append('go')

    output = rj_run_job('ipmosflm', [], commands)

    # should check that the status here was correct

    # now merge

    rmerges, spacegroup = do_scale_merge('integrate.mtz', resolution)

    # now print where we're at...

    print 'Dumb:       %.3f %.3f %.3f %s' % (rmerges[0], rmerges[1],
                                             rmerges[2], spacegroup)

def mosflm_p1(template, directory, beam, distance, start, end,
              resolution, symmetry, gain, ai_images, cr_images):

    # first the autoindexing spell
    
    commands = [
        'directory %s' % directory,
        'template %s' % template,
        'beam %.2f %.2f' % beam,
        'distance %.2f' % distance,
        'symmetry p1'
        ]

    if gain:
        commands.append('gain %.3f' % gain)

    for ai in ai_images:
        commands.append('autoindex dps refine image %d' % ai)

    commands.append('mosaic estimate')
    commands.append('go')

    # then the cell refinement spell

    commands.append('postref multi segments %d' % len(cr_images))

    for cr in cr_images:
        commands.append('process %d %d' % cr)
        commands.append('go')

    # then the integration spell

    commands.append('postref fix all')
    commands.append('hklout integrate.mtz')
    commands.append('process %d %d' % (start, end))
    commands.append('go')

    output = rj_run_job('ipmosflm', [], commands)

    # should check that the status here was correct

    # now merge

    rmerges, spacegroup = do_scale_merge('integrate.mtz', resolution)

    # now print where we're at...

    print 'P1:         %.3f %.3f %.3f %s' % (rmerges[0], rmerges[1],
                                             rmerges[2], spacegroup)

def mosflm_nofix(template, directory, beam, distance, start, end,
                 resolution, symmetry, gain, ai_images, cr_images):

    # first the autoindexing spell
    
    commands = [
        'directory %s' % directory,
        'template %s' % template,
        'beam %.2f %.2f' % beam,
        'distance %.2f' % distance
        ]

    if gain:
        commands.append('gain %.3f' % gain)

    commands.append('symmetry %d' % symmetry)

    for ai in ai_images:
        commands.append('autoindex dps refine image %d' % ai)

    commands.append('mosaic estimate')
    commands.append('go')

    # then the cell refinement spell

    commands.append('postref multi segments %d' % len(cr_images))

    for cr in cr_images:
        commands.append('process %d %d' % cr)
        commands.append('go')

    # then the integration spell

    commands.append('hklout integrate.mtz')
    commands.append('process %d %d' % (start, end))
    commands.append('go')

    output = rj_run_job('ipmosflm', [], commands)

    # should check that the status here was correct

    # now merge

    rmerges, spacegroup = do_scale_merge('integrate.mtz', resolution)

    # now print where we're at...

    print 'Nofix:      %.3f %.3f %.3f %s' % (rmerges[0], rmerges[1],
                                             rmerges[2], spacegroup)
    
def mosflm_test_integration(mosflm_log):

    directory = None
    template = None
    beam = None
    distance = None
    symmetry = None
    start = None
    end = None
    resolution = None
    gain = None

    for record in mosflm_log:
        if not '===>' in record:
            continue

        value = record.split()[-1]

        if 'template' in record:
            template = value.replace('"', '')
        elif 'directory' in record:
            directory = value.replace('"', '')
        elif 'beam' in record:
            values = record.split()[-2:]
            beam = float(values[0]), float(values[1])
        elif 'distance' in record:
            distance = float(value)
        elif 'gain' in record:
            gain = float(value)
        elif 'symmetry' in record:
            symmetry = int(value)
        elif 'resolution' in record:
            resolution = float(value)
        elif 'process' in record:
            values = record.split()[-2:]            
            start, end = int(values[0]), int(values[1])

    assert(template)
    assert(directory)
    assert(beam)
    assert(distance)
    assert(start)
    assert(end)
    assert(resolution)
    assert(symmetry)

    # now get header information from the first image, mostly the
    # oscillation width phi

    image = rj_image_name(template, directory, start)
    phi = rj_get_phi(image)

    # ok that's everything which we're sure we need. set up a few odds and
    # sodds which will be useful

    images = range(start, end + 1)
    
    ai_images = calculate_images_ai(images, phi, 3)
    cr_images = calculate_images_cr(images, phi, 3)

    mosflm_reference(template, directory, beam, distance, start, end,
                     resolution, symmetry, gain, ai_images, cr_images)
    mosflm_resolution(template, directory, beam, distance, start, end,
                      resolution, symmetry, gain, ai_images, cr_images)
    mosflm_p1(template, directory, beam, distance, start, end,
              resolution, symmetry, gain, ai_images, cr_images)
    mosflm_nofix(template, directory, beam, distance, start, end,
                 resolution, symmetry, gain, ai_images, cr_images)
    mosflm_dumb(template, directory, beam, distance, start, end,
                resolution, symmetry, gain, ai_images, cr_images)
    
    
    
if __name__ == '__main__':

    mosflm_test_integration(open(sys.argv[1], 'r').readlines())
    
