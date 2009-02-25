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

def calculate_images(images, phi, spacing):

    if (images[-1] - images[0] + 1) * phi < 90.0:
        raise RuntimeError, 'less than 90 degrees of data'

    result = [images[0]]

    offset = nint(spacing / phi)

    result.append((offset + images[0] - 1))
    result.append((2 * offset + images[0] - 1))

    return result

def phi_spacing(labelit_log):

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
    fout.write('wedgelimit = 3\n')
    fout.write('beam_search_scope = 1.0\n')
    fout.close()

    # generate the list of phi values...

    phis = [float(j + 1) for j in range(5, 45)]

    image_numbers = []

    for p in phis:
        result = calculate_images(images, phi, p)
        if not result in image_numbers:
            image_numbers.append(result)

    # now run labelit with phi spacing 6-45

    metrics = []
    spacings = []

    for i_n in image_numbers:
        spacing = phi * (i_n[2] - i_n[1])
        image_names = [rj_image_name(template, directory, i) for i in i_n]
        output = rj_run_job('labelit.screen --index_only',
                            image_names, [])
        b, l, m, c, i = rj_parse_labelit_log(output)

        if l != lattice:
            raise RuntimeError, 'incorrect result with %d images' % (count + 1)

        metrics.append(m)
        spacings.append(spacing)

    if os.path.exists('dataset_preferences.bak'):
        shutil.copyfile('dataset_preferences.bak', 'dataset_preferences.py')

    return metrics, spacings
    

if __name__ == '__main__':

    import sys

    metrics, spacings = phi_spacing(sys.argv[1])

    c = 1.0 / (max(metrics) - min(metrics))
    m = min(metrics)

    for j in range(len(metrics)):
        print '%5.2f %5.3f' % (spacings[j], c * (metrics[j] - m))
