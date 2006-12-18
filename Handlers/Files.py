#!/usr/bin/env python
# Files.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# A manager for files - this will record temporary and output files from 
# xia2, which can be used for composing a dump of "useful" files at the end
# if processing.

import os
import sys
import exceptions

from Streams import Admin

class _FileHandler:
    '''A singleton class to manage files.'''

    def __init__(self):
        self._temporary_files = []
        self._output_files = []

    def __del__(self):
        for f in self._temporary_files:
            try:
                os.remove(f)
                Admin.write('Deleted: %s' % f, forward = False)
            except exceptions.Exception, e:
                Admin.write('Failed to delete: %s (%s)' % \
                            (f, str(e)), forward = False)

        for f in self._output_files:
            Admin.write('Output file (%s): %s' % f, forward = False)

        return

    def record_output_file(self, filename, type):
        self._output_files.append((type, filename))
        return

    def record_temporary_file(self, filename):
        self._temporary_files.append(filename)
        return

FileHandler = _FileHandler()

if __name__ == '__main__':
    FileHandler.record_temporary_file('noexist.txt')
    open('junk.txt', 'w').write('junk!')
    FileHandler.record_temporary_file('junk.txt')
    

