# core for reading XDS input and log files - first IDXREF

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
