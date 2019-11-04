from __future__ import absolute_import, division, print_function

from builtins import range
import binascii
import random
import struct
import sys


def pack_values(data):
    current = 0
    packed = ""

    for d in data:
        delta = d - current
        if -127 < delta < 127:
            packed += struct.pack("b", delta)
            current = d
            continue

        packed += struct.pack("b", -128)
        if -32767 < delta < 32767:
            packed += struct.pack("<h", delta)
            current = d
            continue

        packed += struct.pack("<h", -32768)
        if -2147483647 < delta < 2147483647:
            packed += struct.pack("<i", delta)
            current = d
            continue

        packed += struct.pack("<i", -2147483648)
        packed += struct.pack("<q", delta)
        current = d

    return packed


def unpack_values(data, length):
    # unpack data stream

    values = []

    pixel = 0
    ptr = 0

    while len(values) < length:

        delta = struct.unpack("b", data[ptr])[0]
        ptr += 1

        if delta != -128:
            pixel += delta
            values.append(pixel)
            continue

        delta = struct.unpack("<h", data[ptr : ptr + 2])[0]
        ptr += 2

        if delta != -32768:
            pixel += delta
            values.append(pixel)
            continue

        delta = struct.unpack("<i", data[ptr : ptr + 4])[0]
        ptr += 4

        if delta != -2147483648:
            pixel += delta
            values.append(pixel)
            continue

        delta = struct.unpack("<q", data[ptr : ptr + 8])[0]
        ptr += 8
        pixel += delta
        values.append(pixel)

    return values


def unpack_tiff(filename):
    data = open(filename, "rb"), read()
    header = data[:4096]
    data = data[4096:]

    values = struct.unpack("<i", data)

    print(min(values), max(values))


def work():
    values = [int(random.random() * 65536) for j in range(1024 * 1024)]

    l = len(values)

    packed = pack_values(values)

    unpacked = unpack_values(packed, l)

    for j in range(l):
        assert unpacked[j] == values[j]

    return


def unpackbyteoffset(filename):

    data = open(filename, "rb").read()

    start_tag = binascii.unhexlify("0c1a04d5")

    data_offset = data.find(start_tag) + 4

    header = data[: data.find(start_tag)].split("\n")

    fast = 0
    slow = 0
    length = 0

    for record in header:
        if "X-Binary-Size-Fastest-Dimension" in record:
            fast = int(record.split()[-1])
        if "X-Binary-Size-Second-Dimension" in record:
            slow = int(record.split()[-1])
        if "X-Binary-Number-of-Elements" in record:
            length = int(record.split()[-1])

    assert length == fast * slow

    values = unpack_values(data[data_offset:], length)
    hist = [0 for j in range(min(0, min(values)), max(values) + 1)]

    for i in range(slow):
        for j in range(fast):
            k = i * fast + j
            hist[values[k]] += 1

    return hist, min(values), max(values)


def sumbyteoffset(filename):

    data = open(filename, "rb").read()

    start_tag = binascii.unhexlify("0c1a04d5")

    data_offset = data.find(start_tag) + 4

    header = data[: data.find(start_tag)].split("\n")

    fast = 0
    slow = 0
    length = 0

    for record in header:
        if "X-Binary-Size-Fastest-Dimension" in record:
            fast = int(record.split()[-1])
        if "X-Binary-Size-Second-Dimension" in record:
            slow = int(record.split()[-1])
        if "X-Binary-Number-of-Elements" in record:
            length = int(record.split()[-1])

    assert length == fast * slow

    values = unpack_values(data[data_offset:], length)

    assert len(values) == length

    return sum(values), length


if __name__ == "__main__":

    for j, image in enumerate(sys.argv[1:]):
        total, pixels = sumbyteoffset(image)
        print(j, total, pixels, image)
        sys.stdout.flush()
