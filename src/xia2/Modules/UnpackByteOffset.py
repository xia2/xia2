import struct


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
