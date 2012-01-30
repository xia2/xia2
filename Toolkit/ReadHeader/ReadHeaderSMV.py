#!/usr/bin/env cctbx.python
# ReadHeaderSMV.py
#
#   Copyright (C) 2010 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Some code to implement header reading for SMV format image headers, which
# will return a dictionary of the tokens found therein.

def ReadHeaderSMV(image):
    '''Some code to read an SMV format image header, and return a dictionary
    containing all of the header contents.'''

    fin = open(image)
    assert(fin.readline().strip()) == '{'
    header_size = int(fin.readline().replace(';', '').split('=')[-1].strip())
    fin.close()

    header_bytes = open(image).read(header_size).replace(
        '{', '').replace('}', '').strip()

    header = { }

    for record in header_bytes.split(';'):

        if not record.strip():
            continue

        token, value = record.split('=')
        header[token.strip()] = value.strip()

    return header_size, header

if __name__ == '__main__':

    import sys

    size, header = ReadHeaderSMV(sys.argv[1])

    for token in sorted(header):
        print '%s = \t%s' % (token, header[token])

    print 'header was %d bytes' % size
