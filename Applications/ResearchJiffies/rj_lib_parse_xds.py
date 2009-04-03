# core for reading XDS input and log files - first IDXREF

from rj_lib_lattice_symmetry import constrain_lattice

def rj_parse_idxref_xds_inp(xds_inp_lines):
    general_records = []
    images = None
    phi = None

    for record in xds_inp_lines:

        if 'SPOT_RANGE=' in record:
            images = tuple(map(int, record.split('=')[-1].split()))
            continue

        if 'UNIT_CELL_CONSTANTS' in record:
            continue

        if 'SPACE_GROUP_NUMBER' in record:
            continue
        
        if 'OSCILLATION_RANGE' in record:
            phi = float(record.split('=')[-1].strip())

        general_records.append(record.strip())

    return images, phi, general_records

def rj_parse_idxref_lp(xds_lp_lines):
    cell = None

    for record in xds_lp_lines:
        if 'UNIT CELL PARAMETERS' in record:
            cell = tuple(map(float, record.split()[-6:]))

    return cell

def rj_parse_xds_correct_lp(xds_lp_lines):
    '''Parse out the happy cell constant, Bravais lattice classes from
    CORRECT.LP.'''

    # assert: they are in order of increasing penalty, so just take the
    # first from each lattice class. Also map mI to mC.

    j = 0

    while not 'CHARACTER  LATTICE' in xds_lp_lines[j]:
        j += 1

    j += 2

    results = { }

    while '*' in xds_lp_lines[j]:
        lst = xds_lp_lines[j].split()
        bravais = lst[2]
        if bravais == 'mI':
            bravais = 'mC'
        penalty = float(lst[3])
        cell = constrain_lattice(bravais[0],
                                 tuple(map(float, lst[4:10])))

        if not bravais in results:
            results[bravais] = {'cell':cell,
                                'penalty':penalty}
        j += 1

    return results

def rj_parse_integrate_lp(integrate_lp_lines):
    general_records = []
    images = None
    phi = None
    cell = None

    ignore = [
        'MINIMUM_VALID_PIXEL_VALUE',
        'BACKGROUND_PIXEL',
        'MAXIMUM_ERROR_OF_SPOT_POSITION',
        'MINPK'
        ]
        

    for record in integrate_lp_lines:
        if '*********' in record:
            break

        if not '=' in record:
            continue

        if record.split('=')[0].strip() in ignore:
            continue

        if 'DATA_RANGE' in record:
            images = tuple(map(int, record.split('=')[-1].split()))
            continue

        if 'OSCILLATION_RANGE' in record:
            phi = float(record.replace('DEGREES', '').split()[-1])
            continue

        if 'UNIT_CELL_CONSTANTS' in record:
            cell = tuple(map(float, record.split('=')[-1].split()))
            continue

        if 'SPACE_GROUP_NUMBER' in record:
            continue

        if 'STARTING_ANGLE' in record:
            continue

        if 'RESOLUTION RANGE' in record:
            continue

        if 'NUMBER OF TRUSTED' in record:
            continue

        if 'MEAN CONTENTS' in record:
            continue

        if 'MEAN VALUE' in record:
            continue

        if 'NUMBER OF' in record:
            continue

        if 'PIXEL VALUE' in record:
            continue

        if 'X-RAY_WAVELENGTH' in record:
            general_records.append(record.replace('ANGSTROM', '').strip())
            continue

        if record.strip():
            general_records.append(record.replace('-0', ' -0').strip())

    return images, phi, cell, general_records

if __name__ == '__main__':
    import sys

    images, phi, cell, junk = rj_parse_integrate_lp(open(sys.argv[1]).readlines())

    print 'DATA_RANGE= %d %d' % images
    print 'OSCILLATION_RANGE= %.2f' % phi
    print 'UNIT_CELL_CONSTANTS= %.2f %.2f %.2f %.2f %.2f %.2f' % cell
    print 'SPACE_GROUP_NUMBER=1'

    for record in junk:
        print record
        
    standard = [
        'JOB=CORRECT',
        'MAXIMUM_NUMBER_OF_PROCESSORS=4',
        'CORRECTIONS=!',
        'REFINE(CORRECT)=CELL',
        'OVERLOAD=65000',
        'DIRECTION_OF_DETECTOR_X-AXIS=1.0 0.0 0.0',
        'DIRECTION_OF_DETECTOR_Y-AXIS=0.0 1.0 0.0',
        'TRUSTED_REGION=0.0 1.41'
        
        ]

    for record in standard:
        print record
        
        
