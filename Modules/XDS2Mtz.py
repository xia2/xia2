# Scalepack2Mtz.py
# Maintained by G.Winter
# 18th June 2007
# 
# A module to carefully convert XDS reflection files (merged or
# unmerged) into properly structured MTZ files. This is based on 
# Scalepack2Mtz
# 
# This will:
# 
# if (unmerged) combat -> scala for merging (else) convert to mtz
#

import os
import sys
import math

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Wrappers.CCP4.CCP4Factory import CCP4Factory

class XDS2Mtz:
    '''A class to convert XDS reflection files to MTZ format, merging
    if required.'''

    def __init__(self):

        self._working_directory = os.getcwd()
        self._factory = CCP4Factory()
        return
        
    # admin functions

    def set_working_directory(self, working_directory):
        self._working_directory = working_directory
        self._factory.set_working_directory(working_directory)
        return

    def get_working_directory(self):
        return self._working_directory 

    def _decide_is_merged(self, file):
        '''Take a look at file and see if it looks like an XDS merged
        or unmerged intensity file.'''

        first_record = open(file, 'r').readline().split()

        if not '!FORMAT=XDS_ASCII' in first_record[0]:
            raise RuntimeError, 'file "%s" not XDS_ASCII' % file

        for token in file_record:
            if 'MERGED' in token:
                is_merged = token.split('=')[-1].lower()
                if is_merged == 'false':
                    return False
                elif is_merged == 'true':
                    return True
                else:
                    raise RuntimeError, 'unrecognised MERGE token  "%s"' % \
                          token
        

        raise RuntimeError, 'cannot find MERGE token'

    def xds_to_mtz(self, xds, hklout, 
                   anomalous, spacegroup, cell, project_info):
        '''Convert an XDS_ASCII file to MTZ, maybe merging.'''

        merged = self._decide_is_merged(xds)

        if merged:
            
        
        
