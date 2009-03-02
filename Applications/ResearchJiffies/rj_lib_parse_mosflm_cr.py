
def rj_parse_mosflm_cr_log(mosflm_cr_log):
    # get the cell constants (&c.) from the mosflm log output...

    cell = None
    mosaic = None

    for record in mosflm_cr_log:
        if 'Refined cell' in record:
            if not 'parameters' in record:
                cell = tuple(map(float, record.split()[-6:]))
        if 'Refined mosaic spread' in record:
            mosaic = float(record.split()[-1])

    if not cell:
        raise RuntimeError, 'cell not found'

    if not mosaic:
        raise RuntimeError, 'mosaic not found'
            
    return cell, mosaic
