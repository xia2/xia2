from rj_lib_find_images import rj_get_template_directory, \
     rj_find_matching_images, rj_get_phi, rj_image_name

from rj_lib_run_job import rj_run_job

from rj_no_images import calculate_images as calculate_images_ai
from rj_cr_n_wedges import calculate_images as calculate_images_cr

import shutil
import sys
import os
import time

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
            template = value
        elif 'directory' in record:
            directory = value
        elif 'beam' in record:
            values = record.split()[-2:]
            beam = float(values[0]), float(values[1])
        elif 'distance' in record:
            distance = float(value)
        elif 'gain' in record:
            gain = float(value)
        elif 'symmetry' in record:
            spacegroup = int(value)
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

    # ok that's everything which we're sure we need. set up a few odds and
    # sodds which will be useful 
    
    ai_images = calculate_images_ai(images, phi, 3)
    cr_images = calculate_images_cr(images, phi, 3)

    # first test: what andrew says

    

    
