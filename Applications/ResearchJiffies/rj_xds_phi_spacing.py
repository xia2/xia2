# code to figure out the best number of wedges to use for cell refinement
# with Mosflm, assuming (i) 3 images per wedge and (ii) that the images
# are spaced over the first 90 degrees of data pseudo uniformly

from rj_lib_parse_xds import rj_parse_idxref_xds_inp, rj_parse_idxref_lp

from rj_lib_run_job import rj_run_job

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

    if phi > 1.01:
        raise RuntimeError, 'images too wide'

    # then figure out how to lay out the images

    n = nint(6.0 / phi) - 1
    offset = nint(spacing / phi)
    
    result = [(images[0], images[0] + n)]
    result.append((nint(images[0] + offset - n),
                   nint(images[0] + offset)))
    result.append((nint(images[0] + 2 * offset - n),
                   nint(images[0] + 2 * offset)))

    return result

def phi_spacing(xds_inp):

    firstlast, phi, records = rj_parse_idxref_xds_inp(
        open(xds_inp, 'r').readlines())

    images = [j for j in range(firstlast[0], firstlast[1] + 1)]

    # first run with all images, then define the 'correct' lattice
    # as the one which results from this autoindex step.

    xds_inp = open('XDS.INP', 'w')
    for record in records:
        xds_inp.write('%s\n' % record)
    xds_inp.write('SPOT_RANGE= %d %d\n' % firstlast)
    xds_inp.close()
    output = rj_run_job('xds', [], [])
    cell = rj_parse_idxref_lp(open('IDXREF.LP', 'r').readlines())
    result = lattice_symmetry(cell)

    lattice = sort_lattices(result.keys())[-1]
    score = result[lattice]['penalty']

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

        spacing = nint(phi * (result[1][0] - result[0][0]))
        spacings.append(spacing)

        xds_inp = open('XDS.INP', 'w')
        for record in records:
            xds_inp.write('%s\n' % record)
        for pair in result:
            xds_inp.write('SPOT_RANGE= %d %d\n' % pair)
        xds_inp.close()
        output = rj_run_job('xds', [], [])

        cell = rj_parse_idxref_lp(open('IDXREF.LP', 'r').readlines())
    
        result = lattice_symmetry(cell)
                
        l = sort_lattices(result.keys())[-1]
                
        if l != lattice:
            raise RuntimeError, 'cell refinement gave wrong lattice'

        metrics.append(result[l]['penalty'])
            
    return metrics, spacings, score

if __name__ == '__main__':

    metrics, spacings, score = phi_spacing(sys.argv[1])

    c = 1.0 / (max(metrics) - min(metrics))
    m = min(metrics)

    for j in range(len(spacings)):
        print '%2d %.3f' % (nint(spacings[j]), c * (metrics[j] - m))

    print ' 0 %.3f' % (c * (score - m))
