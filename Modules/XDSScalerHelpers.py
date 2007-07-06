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

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Handlers.Streams import Chatter, Debug
from lib.Guff import auto_logfiler
from Wrappers.CCP4.Combat import Combat as _Combat

class XDSScalerHelper:
    '''A class which contains functions which will help the XDS Scaler
    with its work. This is implemented as a class to allow properties
    like working directories and so on to be maintained.'''

    def __init__(self):
        self._working_directory = os.getcwd()

        return

    def Combat(self):
        '''Create a Combat wrapper from _Combat - set the working directory
        and log file stuff as a part of this...'''
        combat = _Combat()
        combat.set_working_directory(self.get_working_directory())
        auto_logfiler(combat)
        return combat

    def set_working_directory(self, working_directory):
        self._working_directory = working_directory
        return

    def get_working_directory(self):
        return self._working_directory 

    def parse_xscale_ascii_header(self, xds_ascii_file):
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

                Debug.write('Set %d is from data %s' % (set, input_file))

        return file_map

    def split_xscale_ascii_file(self, xds_ascii_file, prefix):
        '''Split the output of XSCALE to separate reflection files for
        each run. The output files will be called ${prefix}${input_file}.'''
        
        file_map = self.parse_xscale_ascii_header(xds_ascii_file)

        files = { }
        return_map = { }
    
        keys = file_map.keys()

        for k in keys:
            files[k] = open(os.path.join(
                self.get_working_directory(),
                '%s%s' % (prefix, file_map[k])), 'w')

            return_map[file_map[k]] = '%s%s' % (prefix, file_map[k])

        # copy the header to all of the files

        for line in open(xds_ascii_file, 'r').readlines():
            if not line[0] == '!':
                break

            for k in keys:

                if 'ISET' in line and \
                       int(line.split('ISET=')[1].split()[0]) != k:
                    continue

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

    xsh = XDSScalerHelper()

    input_file = os.path.join(
        os.environ['X2TD_ROOT'], 'Test', 'UnitTest',
        'Modules', 'XDSScalerHelpers', '1VR9_NAT.HKL')
    xsh.split_xscale_ascii_file(input_file, 'SCALED_')


