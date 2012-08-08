# convert correct.lp to shelx / bruker .p4p file

def compute_volume_esd(unit_cell, unit_cell_esd, volume):
    '''From http://journals.iucr.org/services/cif/checking/CELLV_02.html.'''

    # see also Fundamentals of Crystallography p 135.

    import math

    d2r = math.pi / 180.0

    csa = math.cos(unit_cell[3] * d2r)
    csb = math.cos(unit_cell[4] * d2r)
    csg = math.cos(unit_cell[5] * d2r)

    sa = math.sin(unit_cell[3] * d2r)
    sb = math.sin(unit_cell[4] * d2r)
    sg = math.sin(unit_cell[5] * d2r)

    a = [unit_cell_esd[j] / unit_cell[j] for j in range(3)]

    b1 = sa * (csa - csb * csg) * unit_cell_esd[3] * d2r
    b2 = sb * (csb - csg * csa) * unit_cell_esd[4] * d2r
    b3 = sg * (csg - csa * csb) * unit_cell_esd[5] * d2r

    cv = math.pow(unit_cell[0] * unit_cell[1] * unit_cell[2], 4) / \
        math.pow(volume, 2)

    suvol = math.sqrt(volume * volume * 
                      (a[0] * a[0] + a[1] * a[1] + a[2] * a[2]) + \
                      cv * (b1 * b1 + b2 * b2 + b3 * b3))

    return suvol

def test():

    from cctbx.uctbx import unit_cell as uc

    unit_cell = 5.960224, 9.036922, 18.390999, 90.0, 90.0, 90.0
    unit_cell_esd = 5.6e-05, 7.7e-05, 0.000157, 0.0, 0.0, 0.0
    volume = 990.5776
    volume_esd = 0.0695

    print volume_esd, compute_volume_esd(unit_cell, unit_cell_esd, volume)

def correct_lp2p4p(correct_lp, p4p):

    from cctbx.uctbx import unit_cell as uc

    # gather required information

    unit_cell = None
    unit_cell_esd = None
    wavelength = None

    for record in open(correct_lp):
        if 'UNIT CELL PARAMETERS' in record:
            unit_cell = map(float, record.split()[-6:])
            volume = uc(unit_cell).volume()
        if 'E.S.D. OF CELL PARAMETERS' in record:
            unit_cell_esd = map(float, record.split()[-6:])
            volume_esd = compute_volume_esd(unit_cell, unit_cell_esd, volume)
        if 'X-RAY_WAVELENGTH=' in record:
            wavelength = float(record.split()[-1])

    # now write p4p file

    open(p4p, 'w').write('\n'.join([
        'TITLE    Auto-generated .p4p file',
        'CELL     %.4f %.4f %.4f %.4f %.4f %.4f %.4f' % tuple(
            unit_cell + [volume]),
        'CELLSD   %.4f %.4f %.4f %.4f %.4f %.4f %.4f' % tuple(
            unit_cell_esd + [volume_esd]),
        'SOURCE   SYNCH   %.6f' % wavelength, '']))

    return
        
if __name__ == '__main__':
    
    import sys
    
    correct_lp2p4p(sys.argv[1], sys.argv[2])
    
