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

def calculate_images(images, phi, width):
    # first check we have 90 degrees or more of data

    if (images[-1] - images[0] + 1) * phi < 90.0:
        raise RuntimeError, 'less than 90 degrees of data'

    # then figure out how to lay out the images

    number = 3

    n = nint(width / phi) - 1
    
    result = [(images[0], images[0] + n)]

    if number == 1:
        return result

    step = 90.0 / (phi * (number - 1))

    for j in range(1, number):
        result.append(((images[0] + nint(step * j) - 1 - n),
                       (images[0] + nint(step * j) - 1)))

    return result

def no_images(xds_inp):

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

    for count in range(10):
        result = calculate_images(images, phi, count + 1)

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
            
    return metrics, score

if __name__ == '__main__':

    metrics, score = no_images(sys.argv[1])

    c = 1.0 / (max(metrics) - min(metrics))
    m = min(metrics)

    for j in range(10):
        print '%2d %.3f' % (j + 1, c * (metrics[j] - m))

    print ' 0 %.3f' % (c * (score - m))
