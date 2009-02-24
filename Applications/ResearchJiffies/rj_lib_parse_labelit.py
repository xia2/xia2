# odds and sods to parse labelit stuff

def rj_parse_labelit_log(labelit_log):
    beam = None
    lattice = None
    metric = None
    cell = None

    for record in open(labelit_log, 'r').readlines():
        if 'Beam center x' in record:
            tokens = record.replace('mm', ' ').split()
            beam = float(tokens[3]), float(tokens[6])

        if ':)' in record and not lattice:
            tokens = record.split()
            metric = float(tokens[2])
            lattice = tokens[7]
            cell = tuple(map(float, tokens[8:14]))

    if not beam:
        raise RuntimeError, 'beam centre not found'

    if not lattice:
        raise RuntimeError, 'lattice not found'

    return beam, lattice, metric, cell

if __name__ == '__main__':

    import sys
    
    beam, lattice, metric, cell = rj_parse_labelit_log(sys.argv[1])

    print 'Beam centre: %.2f %.2f' % beam
    print 'Lattice / metric: %s / %.3f' % (lattice, metric)
    print 'Cell: %.2f %.2f %.2f %.2f %.2f %.2f' % cell

    
