#!/usr/bin/env python

import binascii
import struct
import math
import os
import sys
import random
import time

def pack_values(data):
    current = 0
    packed = ''

    for d in data:
        delta = d - current
        if -127 < delta < 127:
            packed += struct.pack('b', delta)
            current = d
            continue

        packed += struct.pack('b', -128)
        if -32767 < delta < 32767:
            packed += struct.pack('<h', delta)
            current = d
            continue

        packed += struct.pack('<h', -32768)
        if -2147483647 < delta < 2147483647:
            packed += struct.pack('<i', delta)
            current = d
            continue

        packed += struct.pack('<h', -2147483648)
        packed += struct.pack('<q', delta)
        current = d

    return packed

def unpack_values(data):
    values = []

    pixel = 0
    ptr = 0

    while ptr < len(data):

        delta = struct.unpack('b', data[ptr])[0]
        ptr += 1

        if delta != -128:
            pixel += delta
            values.append(pixel)
            continue

        delta = struct.unpack('<h', data[ptr:ptr + 2])[0]
        ptr += 2

        if delta != -32768:
            pixel += delta
            values.append(pixel)
            continue

        delta = struct.unpack('<i', data[ptr:ptr + 4])[0]
        ptr += 4

        if delta != -2147483648:
            pixel += delta
            values.append(pixel)
            continue

        delta = struct.unpack('<q', data[ptr:ptr + 8])[0]
        ptr += 8
        pixel += delta
        values.append(pixel)

    return values

def unpack_tiff(filename):
    data = open(filename, 'r').read()
    header = data[:4096]
    data = data[4096:]

    l = len(data) / 4

    values = [struct.unpack('<i', data[4 * j: 4 * (j + 1)])[0] \
              for j in range(l)]

    return values

def read_cbf(filename):

    data = open(filename, 'r').read()

    start_tag = binascii.unhexlify('0c1a04d5')

    data_offset = data.find(start_tag) + 4

    header = data[:data_offset]
    data = data[data_offset:]

    return header, data

def fix_6m(bad_mask, images):
    bad = unpack_tiff(bad_mask)
    nbad = bad.count(1)

    duff = []

    for j in range(len(bad)):
        if bad[j]:
            duff.append(j)

    out_dir = os.path.join(os.getcwd(), 'fixed')

    if not os.path.exists(out_dir):
        os.mkdir(out_dir)

    for image in images:
        start = time.time()

        out = os.path.join(out_dir, os.path.split(image)[-1])
        header, data = read_cbf(image)

        values = unpack_values(data)

        new_header = ''
        for h in header.split('\n'):
            if 'X-Binary-Size:' in h:
                continue
            if 'Content-MD5:' in h:
                continue
            new_header += '%s\n' % h

        total_bad = sum([values[j] for j in duff])

        for j in duff:
            values[j] = -2

        packed = pack_values(values)
        result = new_header + packed

        print out
        print 'Average duff value: %f' % (total_bad / nbad)
        print 'Processing time: %.1fs' % (time.time() - start)

        open(out, 'w').write(result)

    return

if __name__ == '__main__':
    fix_6m(sys.argv[1], sys.argv[2:])
