# code to figure out the best number of wedges to use for cell refinement
# with Mosflm, assuming (i) 3 images per wedge and (ii) that the images
# are spaced over the first 90 degrees of data pseudo uniformly

from rj_lib_parse_labelit import rj_parse_labelit_log_file, \
     rj_parse_labelit_log

from rj_lib_parse_mosflm_cr import rj_parse_mosflm_cr_log

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

def calculate_images(images, phi, spacing):
    
    # first check we have 90 degrees or more of data

    if (images[-1] - images[0] + 1) * phi < 90.0:
        raise RuntimeError, 'less than 90 degrees of data'

    # then figure out how to lay out the images

    n = 2
    offset = nint(spacing / phi)
    
    result = [(images[0], images[0] + n)]
    result.append((nint(images[0] + offset - n),
                   nint(images[0] + offset)))
    result.append((nint(images[0] + 2 * offset - n),
                   nint(images[0] + 2 * offset)))

    return result

def phi_spacing(labelit_log):

    # 3 images per wedge, maximum of 30 => 1 to 10 wedges.

    beam, lattice, metric, cell, image = rj_parse_labelit_log_file(labelit_log)
    template, directory = rj_get_template_directory(image)
    images = rj_find_matching_images(image)
    phi = rj_get_phi(image)

    if lattice == 'aP':
        raise RuntimeError, 'triclinic lattices useless'

    # right, what I want to do is autoindex with images at 0, 45, 90 or
    # thereabouts (in P1), then do the cell refinement, then score the
    # resulting cell constants

    ai_images = calculate_images_ai(images, phi, 3)

    metrics = []
    spacings = []

    phis = [float(j + 1) for j in range(10, 45)]

    image_numbers = []

    for p in phis:
        result = calculate_images(images, phi, p)
        if phi * (result[-1][-1] - result[0][0] + 1) > 90.0:
            continue
        if not result in image_numbers:
            image_numbers.append(result)

    for result in image_numbers:
        # first autoindex commands

        spacing = nint(phi * (result[1][0] - result[0][0]))
        spacings.append(spacing)

        commands = [
            'template %s' % template,
            'directory %s' % directory,
            'beam %f %f' % beam]

        commands.append('symm P1')

        for image in ai_images:
            commands.append('autoindex dps refine image %d' % image)

        commands.append('mosaic estimate')
        commands.append('go')

        # the cell refinement commands

        commands.append('postref multi segments 3')

        for pair in result:
            commands.append('process %d %d' % pair)
            commands.append('go')

        output = rj_run_job('ipmosflm-7.0.3', [], commands)

        try:
            cell, mosaic = rj_parse_mosflm_cr_log(output)
        except RuntimeError, e:
            for record in output:
                print record[:-1]
            raise e
        result = lattice_symmetry(cell)
        
        l = sort_lattices(result.keys())[-1]
        
        if l != lattice:
            raise RuntimeError, 'cell refinement gave wrong lattice'
        
        metrics.append(result[l]['penalty'])

    return metrics, spacings

if __name__ == '__main__':

    metrics, spacings = phi_spacing(sys.argv[1])

    c = 1.0 / (max(metrics) - min(metrics))
    m = min(metrics)

    for j in range(len(metrics)):
        print '%5.2f %.3f' % (spacings[j], c * (metrics[j] - m))
