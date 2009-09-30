import binascii
import struct
import math
import os
import sys

def unpack_values(data, length):
    # unpack data stream

    values = []

    pixel = 0
    ptr = 0

    while len(values) < length:

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

def unpackbyteoffset(filename):

    data = open(filename, 'r').read()

    start_tag = binascii.unhexlify('0c1a04d5')

    data_offset = data.find(start_tag) + 4

    header = data[:data.find(start_tag)].split('\n')

    fast = 0
    slow = 0
    length = 0

    for record in header:
        if 'X-Binary-Size-Fastest-Dimension' in record:
            fast = int(record.split()[-1])
        if 'X-Binary-Size-Second-Dimension' in record:
            slow = int(record.split()[-1])
        if 'X-Binary-Number-of-Elements' in record:
            length = int(record.split()[-1])

    assert(length == fast * slow)

    values = unpack_values(data[data_offset:], length)
    hist = [0 for j in range(min(0, min(values)), max(values) + 1)]

    for i in range(slow):
        for j in range(fast):
            k = i * fast + j
            hist[values[k]] += 1

    return hist, min(values), max(values)

if __name__ == '__main__':

    hist, minimum, maximum = unpackbyteoffset(sys.argv[1])

    for j in range(minimum, maximum + 1):
        print j, hist[j]
