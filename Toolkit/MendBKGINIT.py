#!/usr/bin/env cctbx.python

# code to mend BKGINIT.py under special circumstances

import os
import sys
import binascii
import copy

from scitbx.array_family import flex
from cbflib_adaptbx import uncompress, compress

def recompute_BKGINIT(bkginit_in, init_lp, bkginit_out):

    start_tag = binascii.unhexlify('0c1a04d5')

    data = open(bkginit_in, 'rb').read()
    data_offset = data.find(start_tag) + 4
    cbf_header = data[:data_offset - 4]

    fast = 0
    slow = 0
    length = 0

    for record in cbf_header.split('\n'):
        if 'X-Binary-Size-Fastest-Dimension' in record:
            fast = int(record.split()[-1])
        elif 'X-Binary-Size-Second-Dimension' in record:
            slow = int(record.split()[-1])
        elif 'X-Binary-Number-of-Elements' in record:
            length = int(record.split()[-1])

    assert(length == fast * slow)

    pixel_values = uncompress(packed = data[data_offset:],
                              fast = fast, slow = slow)

    untrusted = []

    for record in open(init_lp):
        if 'UNTRUSTED_RECTANGLE=' in record:
            untrusted.append(map(int, record.replace('.', ' ').split()[1:5]))

    modified_pixel_values = copy.deepcopy(pixel_values)

    for s in range(5, slow - 5):
        y = s + 1
        for f in range(5, fast - 5):
            x = f + 1
            trusted = True
            for x0, x1, y0, y1 in untrusted:
                if (x >= x0) and (x <= x1) and (y >= y0) and (y <= y1):
                    trusted = False
                    break

            if trusted:
                pixel = pixel_values[s * fast + f]
                if pixel < 0:
                    pixels = []
                    for j in range(-2, 3):
                        for i in range(-2, 3):
                            p = pixel_values[(s + j) * fast + f + i]
                            if p > 0:
                                pixels.append(p)
                    modified_pixel_values[s * fast + f] = int(
                                            sum(pixels) / len(pixels))

    open(bkginit_out, 'wb').write(cbf_header + start_tag +
                                  compress(modified_pixel_values))

    return

if __name__ == '__main__':

    recompute_BKGINIT('BKGINIT.cbf', 'INIT.LP', sys.argv[1])
