# Code to calibrate for the cell refinement test in 2D. This will (in it's 
# first incarnation) run a Labelit autoindex (equivalent: autoindex then 
# transform to a list of solutions to be used as targets for Mosflm)
# then run cell refinement in each of these, dividing the per-image results
# by the P1 value. May need to perform the autoindex then transform this
# to P1 to get more comparable. Discuss. Also show that cell refinement in
# P1 does not always give the best results when transformed to lattice
# options.

# this will run with 3 x 4 image wedges at 0, 45, 90 or thereabouts.

from rj_lib_parse_labelit import rj_parse_labelit_log_file, \
     rj_parse_labelit_log

from rj_lib_parse_mosflm_cr import rj_parse_mosflm_cr_log, \
     rj_parse_mosflm_cr_log_rmsd

from rj_lib_find_images import rj_get_template_directory, \
     rj_find_matching_images, rj_get_phi, rj_image_name

from rj_lib_run_job import rj_run_job

from rj_no_images import calculate_images as calculate_images_ai

from rj_lib_lattice_symmetry import lattice_symmetry, sort_lattices

import shutil
import sys
import os
import time

def nint(a):
    i = int(a)
    if (a - i) > 0.5:
        i += 1
    return i

def calculate_images(images, phi):
    spacing = 44.0

    if (images[-1] - images[0] + 1) * phi < 90.0:
        raise RuntimeError, 'less than 90 degrees of data'

    # then figure out how to lay out the images

    n = 3
    offset = nint(spacing / phi)

    result = [(images[0], images[0] + n)]
    result.append((nint(images[0] + offset - n),
                   nint(images[0] + offset)))
    result.append((nint(images[0] + 2 * offset - n),
                   nint(images[0] + 2 * offset)))

    return result
    
def cr_test(labelit_log):
    
    beam, lattice, metric, cell, image = rj_parse_labelit_log_file(labelit_log)
    template, directory = rj_get_template_directory(image)
    images = rj_find_matching_images(image)
    phi = rj_get_phi(image)

    if lattice == 'aP':
        raise RuntimeError, 'triclinic lattices useless'
    
    ai_images = calculate_images_ai(images, phi, 3)

    # run a quick autoindex (or re-read the labelit log file above) to
    # generate the list of possible unit cell etc.


    # then loop over these


    # and finally calculate the RMSD ratios.

