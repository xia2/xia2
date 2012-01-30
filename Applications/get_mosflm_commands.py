#!/usr/bin/env python

import sys
import exceptions

def get_mosflm_commands(lines_of_input):
    '''Get the commands which were sent to Mosflm.'''

    result = []

    for line in lines_of_input:
        if '===>' in line:
            result.append(line.replace('===>', '').strip())
        if 'MOSFLM =>' in line:
            result.append(line.replace('MOSFLM =>', '').strip())

    return result

def get_orientation_matrix(lines_of_output):
    '''Get mosflm orientation matrix from terminal output.'''

    cell = None
    amat = None
    umat = None
    misset = None

    for j, record in enumerate(lines_of_output):
        if ' Real cell parameters (CELL)' in record:
            cell = map(float, lines_of_output[j + 1].split())
        if ' Rotation matrix U defining standard setting' in record:
            umat = map(float, lines_of_output[j + 1].split()) + \
                   map(float, lines_of_output[j + 2].split()) + \
                   map(float, lines_of_output[j + 3].split())
        if ' Orientation Matrix [A], Components of A*,B*,C*' in record:
            amat = map(float, lines_of_output[j + 1].split()[-3:]) + \
                   map(float, lines_of_output[j + 2].split()[-3:]) + \
                   map(float, lines_of_output[j + 3].split()[-3:])
        if '           Misorientation Angles' in record:
            misset = map(float, lines_of_output[j + 1].split())

    return format_matrix(cell, amat, umat, misset)

def format_matrix(cell, a, u, misset):
    matrix_format = ' %11.8f %11.8f %11.8f\n' + \
                    ' %11.8f %11.8f %11.8f\n' + \
                    ' %11.8f %11.8f %11.8f\n'

    cell_format = ' %11.4f %11.4f %11.4f %11.4f %11.4f %11.4f\n'

    misset_format = ' %11.4f %11.4f %11.4f\n'

    return matrix_format % tuple(a) + \
           misset_format % tuple(misset) + \
           matrix_format % tuple(u) + \
           cell_format % tuple(cell) + \
           misset_format % tuple(misset)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise RuntimeError, '%s mosflm.lp' % sys.argv[0]

    for line in get_mosflm_commands(open(sys.argv[1], 'r').readlines()):
        print line

    try:
        get_orientation_matrix(open(sys.argv[1], 'r').readlines())
    except exceptions.Exception, e:
        pass
