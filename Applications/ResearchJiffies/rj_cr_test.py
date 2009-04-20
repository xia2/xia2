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
     rj_parse_labelit_log, rj_parse_labelit_log_lattices

from rj_lib_parse_mosflm_cr import rj_parse_mosflm_cr_log, \
     rj_parse_mosflm_cr_log_rmsd

from rj_lib_find_images import rj_get_template_directory, \
     rj_find_matching_images, rj_get_phi, rj_image_name

from rj_lib_run_job import rj_run_job

from rj_no_images import calculate_images as calculate_images_ai

from rj_lib_lattice_symmetry import lattice_symmetry, sort_lattices, \
     lattice_spacegroup

import shutil
import sys
import os
import time
import math

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

def meansd(values):
    mean = sum(values) / len(values)
    var = sum([(v - mean) * (v - mean) for v in values]) / len(values)
    return mean, math.sqrt(var)
    
def cr_test(labelit_log):
    
    beam, lattice, metric, cell, image = rj_parse_labelit_log_file(labelit_log)
    lattices, cells = rj_parse_labelit_log_lattices(
        open(labelit_log).readlines())
    template, directory = rj_get_template_directory(image)
    images = rj_find_matching_images(image)
    phi = rj_get_phi(image)

    if lattice == 'aP':
        raise RuntimeError, 'triclinic lattices useless'

    wedges = calculate_images(images, phi)
    
    ai_images = calculate_images_ai(images, phi, 3)

    # run a quick autoindex (or re-read the labelit log file above) to
    # generate the list of possible unit cell etc.

    rmsds_all = { }

    # then loop over these

    for lattice in lattices:
        commands = [
            'template %s' % template,
            'directory %s' % directory,
            'beam %f %f' % beam]

        commands.append('symm %d' % lattice_spacegroup(lattice))
        commands.append('cell %f %f %f %f %f %f' % tuple(cells[lattice]))

        for image in ai_images:
            commands.append('autoindex dps refine image %d' % image)

        commands.append('mosaic estimate')
        commands.append('go')

        # the cell refinement commands

        commands.append('postref multi segments 3')

        for pair in wedges:
            commands.append('process %d %d' % pair)
            commands.append('go')

        for c in commands:
            # print c
            pass

        output = rj_run_job('ipmosflm-7.0.3', [], commands)
        
        images, rmsds = rj_parse_mosflm_cr_log_rmsd(output)

        rmsds_all[lattice] = rmsds

    # and finally calculate the RMSD ratios.

    # break up by lattice, image and cycle

    for lattice in lattices[:-1]:
        print lattice
        values = []
        for cycle in rmsds_all[lattice]:
            if not cycle in rmsds_all['aP']:
                continue
            record = '%3d' % cycle
            for j in range(len(images)):
                record += ' %.3f' % (rmsds_all[lattice][cycle][j] /
                                     rmsds_all['aP'][cycle][j])
                values.append((rmsds_all[lattice][cycle][j] /
                               rmsds_all['aP'][cycle][j]))

            print record

        m, s = meansd(values)
        print ':: %s %.3f %.3f' % (lattice, m, s)

if __name__ == '__main__':
    cr_test(sys.argv[1])
