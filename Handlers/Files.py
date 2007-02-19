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
import shutil

from Environment import Environment

class _FileHandler:
    '''A singleton class to manage files.'''

    def __init__(self):
        self._temporary_files = []
        self._output_files = []

        self._log_files = { }
        self._log_file_keys = []

    def cleanup(self):
        out = open('xia-files.txt', 'w')
        for f in self._temporary_files:
            try:
                os.remove(f)
                out.write('Deleted: %s\n' % f)
            except exceptions.Exception, e:
                out.write('Failed to delete: %s (%s)\n' % \
                          (f, str(e)))

        for f in self._output_files:
            out.write('Output file (%s): %s\n' % f)

        # copy the log files
        log_directory = Environment.generate_directory('LogFiles')
        for f in self._log_file_keys:
            filename = os.path.join(log_directory,
                                    '%s.log' % f.replace(' ', '_'))
            shutil.copyfile(self._log_files[f],
                            filename)
            out.write('Copied log file %s to %s' % \
                      (self._log_files[f],
                       filename))

        out.close()
        return

    def record_output_file(self, filename, type):
        self._output_files.append((type, filename))
        return

    def record_log_file(self, tag, filename):
        '''Record a log file.'''
        self._log_files[tag] = filename
        if not tag in self._log_file_keys:
            self._log_file_keys.append(tag)

    def record_temporary_file(self, filename):
        self._temporary_files.append(filename)
        return

FileHandler = _FileHandler()

def cleanup():
    FileHandler.cleanup()

if __name__ == '__main__':
    FileHandler.record_temporary_file('noexist.txt')
    open('junk.txt', 'w').write('junk!')
    FileHandler.record_temporary_file('junk.txt')
    

