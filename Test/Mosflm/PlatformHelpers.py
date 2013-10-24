#!/usr/bin/env python
# PlatformHelpers.py
#
#   Copyright (C) 2013 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Test platform helpers for new Mosflm wrapper implementations.

def randomize_spots(spot_file):
    '''Read Mosflm spot file; randomize the spot positions; write new spot 
    file.'''

    import random
    
    spot_records = open(spot_file).readlines()

    nx, ny = map(int, spot_records[0].split()[:2])
    pixel_size = float(spot_records[0].split()[2])

    new_spot_records = []

    for record in spot_records:
        tokens = record.split()
        if len(tokens) != 6:
            new_spot_records.append(record)
            continue

        x, y, img, phi, i, sigi = map(float, tokens)

        if int(x) == int(y) == -999:
            new_spot_records.append(record)
            continue
                    
        new_x = nx * pixel_size * random.random()
        new_y = ny * pixel_size * random.random()
        
        new_spot_records.append(' %10.2f%10.2f%9.3f%9.3f%12.1f%12.1f\n' % \
                                (new_x, new_y, img, phi, i, sigi))

    open(spot_file, 'w').write(''.join(new_spot_records))

    return spot_file
                            
if __name__ == '__main__':
    import sys

    randomize_spots(sys.argv[1])
                                
        
