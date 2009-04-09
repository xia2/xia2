
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

def rj_parse_mosflm_cr_log_rmsd(mosflm_cr_log):
    # get the r.m.s. deviations as a function of image number

    collecting = False
    images = []
    rmsds = { }

    for record in mosflm_cr_log:
        if 'Rms positional error (mm)' in record:
            collecting = True

        if 'YSCALE' in record:
            collecting = False

        if collecting and 'Image' in record:
            for token in record.replace('Image', '').split():
                images.append(int(token))

        if collecting and 'Cycle' in record:
            cycle = int(record.split()[1])
            if not cycle in rmsds:
                rmsds[cycle] = []

            for token in record.split()[2:]:
                rmsds[cycle].append(float(token))

    return images, rmsds

if __name__ == '__main__':

    import sys
    
    images, rmsds = rj_parse_mosflm_cr_log_rmsd(open(sys.argv[1]).readlines())

    for i in range(len(images)):
        record = '%3d' % images[i]
        for cycle in sorted(rmsds):
            record += ' %.3f' % (rmsds[cycle][i])

        print record


    
