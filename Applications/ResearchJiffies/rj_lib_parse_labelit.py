# odds and sods to parse labelit stuff

import os

def rj_parse_labelit_log_file(labelit_log):
    return rj_parse_labelit_log(open(labelit_log, 'r').readlines())

def rj_parse_labelit_log(labelit_log_lines):
    beam = None
    lattice = None
    metric = None
    cell = None

    j = 0

    while 'Non-zero two-theta' in labelit_log_lines[j].strip():
        j += 1
    
    image = labelit_log_lines[j].strip()

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

def rj_parse_labelit_log_lattices(labelit_log_lines):
    lattices = []
    cells = { }

    j = 0

    for record in labelit_log_lines:
        if ':)' in record:
            tokens = record.split()
            lattice = tokens[7]
            cell = tuple(map(float, tokens[8:14]))
            if not lattice in lattices:
                lattices.append(lattice)
            cells[lattice] = cell

    return lattices, cells

if __name__ == '__main__':

    import sys
    
    beam, lattice, metric, cell, image = rj_parse_labelit_log_file(sys.argv[1])

    print 'Beam centre: %.2f %.2f' % beam
    print 'Lattice / metric: %s / %.3f' % (lattice, metric)
    print 'Cell: %.2f %.2f %.2f %.2f %.2f %.2f' % cell
    print 'Image: %s' % image
    
