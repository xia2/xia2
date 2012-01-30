import os
import sys
import math
import shutil

def split_spot_file(j):
    '''Split the spot file into those which have been indexed (goes to SPOT.j)
    and those which have not, which gets returned to SPOT.XDS. Returns number
    of unindexed reflections.'''

    spot_j = open('SPOT.%d' % j, 'w')
    spot_0 = open('SPOT.0', 'w')
    spot = open('SPOT.XDS', 'r')

    n_j = 0
    n_0 = 0

    for record in spot:
        if '     0       0       0' in record:
            spot_0.write(record)
            n_0 += 1
        else:
            spot_j.write(record)
            n_j += 1

    spot_j.close()
    spot_0.close()
    spot.close()

    shutil.move('SPOT.0', 'SPOT.XDS')

    return n_0, n_j

def prepare_xds_inp():

    xds_inp = open('XDS.0', 'w')

    for record in open('XDS.INP'):
        if 'SPACE_GROUP_NUMBER' in record:
            continue
        if 'UNIT_CELL_CONSTANTS' in record:
            continue
        xds_inp.write(record)

    xds_inp.close()

    shutil.move('XDS.0', 'XDS.INP')

    return

def run_xds(j):

    os.system('xds_par > /dev/null')

    shutil.copyfile('IDXREF.LP', 'IDXREF.%d' % j)
    shutil.copyfile('XPARM.XDS', 'XPARM.%d' % j)

    n_unindexed, n_indexed = split_spot_file(j)

    return n_unindexed, n_indexed

def get_unit_cell():
    unit_cell = map(float, open('XPARM.XDS', 'r').read().split()[27:33])
    return tuple(unit_cell)

def num_spots():
    j = 0

    for record in open('SPOT.XDS', 'r'):
        if record.strip():
            j += 1

    return j

def main():

    prepare_xds_inp()

    n_unindexed = num_spots()

    j = 0

    while n_unindexed > 100:
        j += 1
        n_unindexed, n_indexed = run_xds(j)
        if n_indexed == 0:
            break
        unit_cell = get_unit_cell()
        print '%3d %5d %5d' % (j, n_indexed, n_unindexed), \
              '%6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % unit_cell



if __name__ == '__main__':
    main()
