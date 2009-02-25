# code to figure out the best number of images to use based on the labelit
# metric penalty

from rj_lib_parse_labelit import rj_parse_labelit_log_file, \
     rj_parse_labelit_log

from rj_lib_find_images import rj_get_template_directory, \
     rj_find_matching_images, rj_get_phi, rj_image_name

from rj_lib_run_job import rj_run_job

import shutil
import os
import time

def nint(a):
    i = int(a)
    if (a - i) > 0.5:
        i += 1
    return i

def calculate_images(images, phi, number):
    # first check we have 90 degrees or more of data

    if (images[-1] - images[0] + 1) * phi < 90.0:
        raise RuntimeError, 'less than 90 degrees of data'

    # then figure out how to lay out the images

    result = [images[0]]

    if number == 1:
        return result

    step = 90.0 / (phi * (number - 1))

    for j in range(1, number):
        result.append((images[0] + nint(step * j) - 1))

    return result

def no_images(labelit_log):
    # first parse this

    beam, lattice, metric, cell, image = rj_parse_labelit_log_file(labelit_log)
    template, directory = rj_get_template_directory(image)
    images = rj_find_matching_images(image)
    phi = rj_get_phi(image)

    if lattice == 'aP':
        raise RuntimeError, 'triclinic lattices useless'

    # then copy the dataset_preferences.py somewhere safe

    if os.path.exists('dataset_preferences.py'):
        shutil.copyfile('dataset_preferences.py',
                        'dataset_preferences.bak')

    # write out a dataset preferences file

    fout = open('dataset_preferences.py', 'w')
    fout.write('beam = (%f, %f)\n' % beam)
    fout.write('wedgelimit = 15\n')
    fout.write('beam_search_scope = 1.0\n')
    fout.close()

    # now run labelit with 1 - 15 images

    metrics = []
    times = []

    for count in range(15):
        result = calculate_images(images, phi, count + 1)
        image_names = [rj_image_name(template, directory, i) for i in result]

        t0 = time.time()
        output = rj_run_job('labelit.screen --index_only',
                            image_names, [])
        t1 = time.time()

        times.append((t1 - t0))
        
        b, l, m, c, i = rj_parse_labelit_log(output)

        if l != lattice:
            raise RuntimeError, 'incorrect result with %d images' % (count + 1)

        metrics.append(m)

    if os.path.exists('dataset_preferences.bak'):
        shutil.copyfile('dataset_preferences.bak', 'dataset_preferences.py')

    return metrics, times

if __name__ == '__main__':

    import sys

    metrics, times = no_images(sys.argv[1])

    c = 1.0 / (max(metrics) - min(metrics))
    m = min(metrics)

    for j in range(15):
        print '%2d %.3f %5.1f' % (j + 1, c * (metrics[j] - m), times[j])
