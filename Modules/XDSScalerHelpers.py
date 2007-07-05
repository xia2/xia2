#!/usr/bin/env python
# XDSScalerHelpers.py
#   Copyright (C) 2007 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 5th July 2007
#
# Code to help the scaler along - this will basically be a bunch of jiffy 
# functions...
# 

import os
import sys

def parse_xscale_ascii_header(xds_ascii_file):
    '''Parse out the input reflection files which contributed to this
    reflection file.'''

    file_map = { }

    for line in open(xds_ascii_file, 'r').readlines():
        if not line[0] == '!':
            break

        if 'ISET' in line and 'INPUT_FILE' in line:
            set = int(line.split()[2].strip())
            input_file = line.split('=')[2].strip()

            file_map[set] = input_file

    return file_map

def split_xscale_ascii_file(xds_ascii_file, prefix):
    '''Split the output of XSCALE to separate reflection files for
    each run. The output files will be called ${prefix}${input_file}.'''

    file_map = parse_xscale_ascii_header(xds_ascii_file)

    files = { }
    return_map = { }
    
    keys = file_map.keys()

    for k in keys:
        files[k] = open('%s%s' % (prefix, file_map[k]), 'w')

        return_map[file_map[k]] = '%s%s' % (prefix, file_map[k])

    # copy the header to all of the files

    for line in open(xds_ascii_file, 'r').readlines():
        if not line[0] == '!':
            break

        for k in keys:

            # FIXME in here I should check that this line is appropriate
            # for this file, though it probably won't matter too much
            
            files[k].write(line)

    # next copy the appropriate reflections to each file
    
    for line in open(xds_ascii_file, 'r').readlines():
        if line[0] == '!':
            continue

        k = int(line.split()[-1])
        files[k].write(line)

    # then write the tailer

    for k in keys:
        files[k].write('!END_OF_DATA\n')
        files[k].close()

    return return_map


if __name__ == '__main__':

    for f in sys.argv[1:]:
        print split_xscale_ascii_file(f, 'demo')

