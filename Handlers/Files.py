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
#
# This will also be responsible for migrating the data - that is, when
# the .xinfo file is parsed the directories referred to therein may be
# migrated to a local disk. This will use a directory created by
# tempfile.mkdtemp().

import os
import sys
import exceptions
import shutil
import tempfile
import time

from Environment import Environment
from Handlers.Streams import Chatter, Debug
from Handlers.Flags import Flags

def get_mosflm_commands(lines_of_input):
    '''Get the commands which were sent to Mosflm.'''

    result = []

    for line in lines_of_input:
        if '===>' in line:
            result.append(line.replace('===>', '').strip())
        if 'MOSFLM =>' in line:
            result.append(line.replace('MOSFLM =>', '').strip())

    return result

def get_xds_commands(lines_of_input):
    '''Get the command input to XDS - that is, all of the text between
    the line which goes ***** STEP ***** and **********. Love FORTRAN.'''

    collecting = False

    result = []

    for l in lines_of_input:
        if '*****' in l and not collecting:
            collecting = True
            continue

        if '*****' in l:
            break

        if collecting:
            if l.strip():
                result.append(l.strip())

    return result

def get_ccp4_commands(lines_of_input):
    '''Get the commands which were sent to a CCP4 program.'''

    # first look through for hklin / hklout

    logicals = { }

    for line in lines_of_input:
        if 'Logical Name:' in line:
            token = line.split(':')[1].split()[0]
            value = line.split(':')[-1].strip()
            logicals[token] = value

    # then look for standard input commands

    script = []

    for line in lines_of_input:
        if 'Data line---' in line:
            script.append(line.replace('Data line---', '').strip())

    return script, logicals

class _FileHandler:
    '''A singleton class to manage files.'''

    def __init__(self):
        self._temporary_files = []
        self._output_files = []

        self._log_files = { }
        self._log_file_keys = []

        # for putting the reflection files somewhere nice...
        self._data_files = []

        # same mechanism as log files - I want to rename files copied to the
        # DataFiles directory
        self._more_data_files = { }
        self._more_data_file_keys = []

        # for data migration to local disk, bug # 2274
        self._data_migrate = { }

    def migrate(self, directory):
        '''Migrate (or not) data to a local directory.'''

        if not Flags.get_migrate_data():
            # we will not migrate this data
            return directory

        if directory in self._data_migrate.keys():
            # we have already migrated this data
            return self._data_migrate[directory]

        # create a directory to move data to...
        self._data_migrate[directory] = tempfile.mkdtemp()

        # copy all files in source directory to new directory
        # retaining timestamps etc.

        start_time = time.time()

        migrated = 0
        migrated_dir = 0
        for f in os.listdir(directory):
            # copy over only files....
            if os.path.isfile(os.path.join(directory, f)):
                shutil.copy2(os.path.join(directory, f),
                             self._data_migrate[directory])
                migrated += 1
            elif os.path.isdir(os.path.join(directory, f)):
                shutil.copytree(os.path.join(directory, f),
                                os.path.join(self._data_migrate[directory],
                                             f))
                migrated_dir += 1


        Debug.write('Migrated %d files from %s to %s' % \
                    (migrated, directory, self._data_migrate[directory]))

        if migrated_dir > 0:
            Debug.write('Migrated %d directories from %s to %s' % \
                        (migrated_dir, directory,
                         self._data_migrate[directory]))

        end_time = time.time()
        duration = end_time - start_time

        Debug.write('Migration took %s' % \
                    time.strftime("%Hh %Mm %Ss", time.gmtime(duration)))

        return self._data_migrate[directory]

    def generate_bioxhit_xml(self, target_directory):
        '''Write a BioXHit XML tracking file "bioxhit.xml" in the
        target directory.'''

        fout = open(os.path.join(target_directory, 'bioxhit.xml'), 'w')

        fout.write('<?xml version="1.0"?>')
        fout.write('<BioXHIT_data_tracking>')

        # FIXME need to get the project name from someplace
        fout.write('<project_name>%s</project_name>' % 'unknown')

        # now iterate through the "steps"
        for f in self._log_file_keys:

            # ignore the troublesome ones

            if 'postrefinement' in f:
                continue

            filename = os.path.join(target_directory,
                                    '%s.log' % f.replace(' ', '_'))
            original = self._log_files[f]

            step_number = os.path.split(original)[-1].split('_')[0]
            step_title = f

            # This is correct for the scala, mosflm logfiles etc, but not
            # so for XDS files which end in '.LP'

            xds_programs = ['INIT', 'COLSPOT', 'IDXREF', 'DEFPIX',
                            'INTEGRATE', 'CORRECT', 'XSCALE']
            useful_xds_programs = ['IDXREF', 'INTEGRATE', 'CORRECT', 'XSCALE']

            if f.split()[-1] in xds_programs:
                # this is an XDS (or XSCALE) file

                if f.split()[-1] not in useful_xds_programs:
                    continue

                app_name = 'xds'

            else:
                app_name = os.path.split(
                    original)[-1].split('_')[1].replace('.log', '')

            run_date = time.ctime(os.stat(original)[8])

            # generate the control input - read the input files for this

            if 'mosflm' in app_name:
                commands = get_mosflm_commands(
                    open(original, 'r').readlines())
                input_files = []
                output_files = []

            elif 'xds' in app_name:
                commands = get_xds_commands(
                    open(original, 'r').readlines())
                input_files = []
                output_files = []

            elif 'chef' in app_name:
                commands, allfiles = get_ccp4_commands(
                    open(original, 'r').readlines())
                input_files = []
                output_files = []

            elif 'pointless' in app_name:
                commands, allfiles = get_ccp4_commands(
                    open(original, 'r').readlines())
                input_files = []
                output_files = []

            else:
                commands, allfiles = get_ccp4_commands(
                    open(original, 'r').readlines())

                # parse up the files

                input_files = [allfiles['HKLIN']]
                output_files = []

                for k in allfiles.keys():
                    if k == 'HKLIN':
                        continue

                    if 'mtz' in allfiles[k] and not \
                       allfiles[k] in output_files:
                        output_files.append(allfiles[k])

            # ok, write the xml block

            fout.write('<step><step_number>%s</step_number>' % step_number)
            fout.write('<step_title>%s</step_title>' % step_title)
            fout.write('<date>%s</date>' % run_date)
            fout.write('<application_control_text>')
            for record in commands:
                fout.write('%s\n' % record)
            fout.write('</application_control_text>')

            fout.write('<input_files>')
            for f in input_files:
                fout.write('<file><file_ref>%s</file_ref></file>' % f)
            fout.write('</input_files>')

            fout.write('<output_files>')
            for f in output_files:
                fout.write('<file><file_ref>%s</file_ref></file>' % f)
            fout.write('</output_files>')

            fout.write('<log_file>%s</log_file>' % filename)

            fout.write('</step>')

        fout.write('</BioXHIT_data_tracking>')
        fout.close()

        return


    def cleanup(self):
        out = open('xia-files.txt', 'w')
        for f in self._temporary_files:
            try:
                os.remove(f)
                out.write('Deleted: %s\n' % f)
            except exceptions.Exception, e:
                out.write('Failed to delete: %s (%s)\n' % \
                          (f, str(e)))

        for f in self._data_migrate.keys():
            d = self._data_migrate[f]
            shutil.rmtree(d)
            out.write('Removed directory %s' % d)

        for f in self._output_files:
            out.write('Output file (%s): %s\n' % f)

        # copy the log files
        log_directory = Environment.generate_directory('LogFiles')

        # generate bioxhit XML in here...
        try:
            self.generate_bioxhit_xml(log_directory)
        except exceptions.Exception, e:
            out.write('Error generating bioxhit xml')

        for f in self._log_file_keys:
            filename = os.path.join(log_directory,
                                    '%s.log' % f.replace(' ', '_'))
            shutil.copyfile(self._log_files[f],
                            filename)
            out.write('Copied log file %s to %s\n' % \
                      (self._log_files[f],
                       filename))

        # copy the data files
        data_directory = Environment.generate_directory('DataFiles')
        for f in self._data_files:
            filename = os.path.join(data_directory,
                                    os.path.split(f)[-1])
            shutil.copyfile(f, filename)
            out.write('Copied data file %s to %s\n' % \
                      (f, filename))

        if Flags.get_blend():

            data_directory = Environment.generate_directory(
                ('DataFiles', 'Integrate'))

            for f in self._more_data_file_keys:
                exten = self._more_data_files[f].split('.')[-1]
                filename = os.path.join(data_directory,
                                        '%s.%s' % (f.replace(' ', '_'), exten))
                shutil.copyfile(self._more_data_files[f], filename)
                out.write('Copied extra data file %s to %s\n' % \
                          (self._more_data_files[f], filename))

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
        return

    def record_data_file(self, filename):
        '''Record a data file.'''
        if not filename in self._data_files:
            self._data_files.append(filename)
        return

    def record_more_data_file(self, tag, filename):
        '''Record an extra data file.'''
        self._more_data_files[tag] = filename
        if not tag in self._more_data_file_keys:
            self._more_data_file_keys.append(tag)
        return

    def get_data_file(self, filename):
        '''Return the point where this data file will end up!'''

        if not filename in self._data_files:
            return filename

        data_directory = Environment.generate_directory('DataFiles')
        return os.path.join(data_directory, os.path.split(filename)[-1])

    def record_temporary_file(self, filename):
        # allow for file overwrites etc.
        if not filename in self._temporary_files:
            self._temporary_files.append(filename)
        return

FileHandler = _FileHandler()

def cleanup():
    FileHandler.cleanup()

if __name__ == '__main__':
    FileHandler.record_temporary_file('noexist.txt')
    open('junk.txt', 'w').write('junk!')
    FileHandler.record_temporary_file('junk.txt')
