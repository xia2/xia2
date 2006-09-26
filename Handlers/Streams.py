#!/usr/bin/env python
# Streams.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
#
# Maintained by Graeme Winter
# 15th August 2006
# 
# "Standard" output streams for the output of xia2dpa - these will allow 
# filtering of the output to files, the standard output, a GUI, none of 
# the above, all of the above.
# 
# The idea of this is to separate the "administrative", "status" and 
# "scientific" output of the program. Finally I also decided (5/SEP/06)
# to add a stream for "chatter", that is the odds and ends which are 
# going on inside the program which tells you it's doing things.
#
# FIXME 05/SEP/06 wouldn't it be nice to split the output to fit well on 
#                 an 80 character terminal display?
# 
# 

import sys

class _Stream:
    '''A class to represent an output stream. This will be used as a number
    of static instances - Science, Admin, Status.'''

    def __init__(self, streamname, prefix):
        '''Create a new stream.'''

        # FIXME would rather this goes to a file...
        # unless this is impossible

        try:
            if streamname == None:
                raise RuntimeError, 'want this to go to stdout'
            self._file = open('%s.txt' % streamname, 'w')
        except:
            self._file = sys.stdout
            
        self._streamname = streamname
        self._prefix = prefix

        self._otherstream = None

        return

    def write(self, record):
        for r in record.split('\n'):
            result = self._file.write('[%s]  %s\n' % (self._prefix, r.strip()))
        self._file.flush()

        if self._otherstream:
            self._otherstream.write(record)
        
        return result

    def join(self, otherstream):
        '''Join another stream so that all output from this stream goes also
        to that one.'''

        self._otherstream = otherstream

Science = _Stream('xia-science', 'SCI-')
Admin = _Stream('xia-admin', 'ADMN')
Status = _Stream('xia-status', 'STAT')
Chatter = _Stream(None, 'XIA2')
Science.join(Chatter)
Admin.join(Chatter)
Status.join(Chatter)

if __name__ == '__main__':
    Science.write('Hello from Science')
    Admin.write('Hello from Admin')
    Status.write('All finished now...')
    Chatter.write('nothing much, really')
