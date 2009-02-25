# odds and sods to parse labelit stuff

import os

def rj_parse_labelit_log_file(labelit_log):
    return rj_parse_labelit_log(open(labelit_log, 'r').readlines())

def rj_parse_labelit_log(labelit_log_lines):
    beam = None
    lattice = None
    metric = None
    cell = None

    image = labelit_log_lines[0].strip()

    for record in labelit_log_lines:
        if 'Beam center x' in record:
            tokens = record.replace('mm', ' ').split()
            beam = float(tokens[3]), float(tokens[6])

        if ':)' in record and not lattice:
            tokens = record.split()
            metric = float(tokens[2])
            lattice = tokens[7]
            cell = tuple(map(float, tokens[8:14]))

    if not image:
        raise RuntimeError, 'image not found'

    if not os.path.exists(image):
        raise RuntimeError, 'image does not exist'

    if not beam:
        raise RuntimeError, 'beam centre not found'

    if not lattice:
        raise RuntimeError, 'lattice not found'

    return beam, lattice, metric, cell, image

if __name__ == '__main__':

    import sys
    
    beam, lattice, metric, cell, image = rj_parse_labelit_log_file(sys.argv[1])

    print 'Beam centre: %.2f %.2f' % beam
    print 'Lattice / metric: %s / %.3f' % (lattice, metric)
    print 'Cell: %.2f %.2f %.2f %.2f %.2f %.2f' % cell
    print 'Image: %s' % image
    
