#!/usr/bin/env python
# Cad.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
#
# 26th October 2006
# 
# A wrapper for the CCP4 program Cad, for merging multiple reflection files
# into a single reflection file, e.g. in preparation for phasing.
# 
# This will take a single HKLOUT file and a list of HKLIN files, c/f the
# Sortmtz wrapper implementation.
# 
# Ok, this Cad wrapper will handle two cases. The first is relabeling all
# columns by e.g. appending a new suffix to the name (this should default
# to the dname I guess) and setting the unit cell to some sanctioned value.
#
# The second aspect to this is the merging of the reflection files into
# on big one.
#
# This should almost be implemented as two wrappers - oh well! Aha - implement
# two methods - merge & update - this can handle the two distinct use cases.

import os
import sys

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                                 'Python'))

from Driver.DriverFactory import DriverFactory
from Decorators.DecoratorFactory import DecoratorFactory

# locally required wrappers

from Mtzdump import Mtzdump

def Cad(DriverType = None):
    '''A factory for CadWrapper classes.'''

    DriverInstance = DriverFactory.Driver(DriverType)
    CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, 'ccp4')

    class CadWrapper(CCP4DriverInstance.__class__):
        '''A wrapper for Cad, using the CCP4-ified Driver.'''

        def __init__(self):
            # generic things
            CCP4DriverInstance.__class__.__init__(self)
            self.set_executable('cad')

            self._hklin_files = []

            self._new_cell_parameters = None
            self._new_column_suffix = None

            return

        def add_hklin(self, hklin):
            '''Add a reflection file to the list to be sorted together.'''
            self._hklin_files.append(hklin)
            return

        def set_new_suffix(self, suffix):
            '''Set a column suffix for this dataset.'''
            self._new_column_suffix = suffix
            return

        def set_new_cell(self, cell):
            '''Set a new unit cell for this dataset.'''
            self._new_cell_parameters = cell
            return

        def merge(self):
            '''Merge multiple reflection files into one file.'''

            if not self._hklin_files:
                raise RuntimeError, 'no hklin files defined'
            
            self.check_hklout()
            
            hklin_counter = 0

            # for each reflection file, need to gather the column names
            # and so on, to put in the cad input here - also check to see
            # if the column names clash... check also that the spacegroups
            # match up...

            spacegroup = None
            column_names = []
            column_names_by_file = { }

            for hklin in self._hklin_files:
                md = Mtzdump()
                md.set_hklin(hklin)
                md.dump()
                columns = md.get_columns()
                spag = md.get_spacegroup()

                if spacegroup is None:
                    spacegroup = spag

                if spag != spacegroup:
                    raise RuntimeError, 'spacegroups do not match'

                column_names_by_file[hklin] = []

                for c in columns:
                    name = c[0]
                    if name in ['H', 'K', 'L']:
                        continue
                    if name in column_names:
                        raise RuntimeError, 'duplicate column names'
                    column_names.append(name)
                    column_names_by_file[hklin].append(name)

            # if we get to here then this is a good set up...

            # create the command line

            hklin_counter = 0
            for hklin in self._hklin_files:
                hklin_counter += 1
                self.add_command_line('hklin%d' % hklin_counter)
                self.add_command_line(hklin)

            self.start()

            hklin_counter = 0

            for hklin in self._hklin_files:
                column_counter = 0
                hklin_counter += 1
                labin_command = 'labin file_number %d' % hklin_counter
                for column in column_names_by_file[hklin]:
                    column_counter += 1
                    labin_command += ' E%d=%s' % (column_counter, column)

                self.input(labin_command)

            self.close_wait()

            try:
                self.check_for_errors()
                self.check_ccp4_errors()

            except RuntimeError, e:
                # something went wrong; remove the output file
                try:
                    os.remove(self.get_hklout())
                except:
                    pass
                raise e
                
            return self.get_ccp4_status()

        def update(self):
            '''Update the information for one reflection file.'''

            if not self._hklin_files:
                raise RuntimeError, 'no hklin files defined'

            if len(self._hklin_files) > 1:
                raise RuntimeError, 'can have only one hklin to update'
            
            hklin = self._hklin_files[0]

            self.check_hklout()

            column_names_by_file = { }
            dataset_names_by_file = { }

            md = Mtzdump()
            md.set_hklin(hklin)
            md.dump()
            columns = md.get_columns()
            
            column_names_by_file[hklin] = []
            dataset_names_by_file[hklin] = md.get_datasets()

            for c in columns:
                name = c[0]
                if name in ['H', 'K', 'L']:
                    continue
                                          
                column_names_by_file[hklin].append(name)

            self.add_command_line('hklin1')
            self.add_command_line(hklin)
            self.start()
            
            column_counter = 0
            labin_command = 'labin file_number 1' 
            for column in column_names_by_file[hklin]:
                column_counter += 1
                labin_command += ' E%d=%s' % (column_counter, column)

            self.input(labin_command)            

            pname, xname, dname = dataset_names_by_file[hklin][0].split('/')

            if self._new_cell_parameters:
                a, b, c, alpha, beta, gamma = self._new_cell_parameters
                self.input('dcell file_number 1 %s %s %f %f %f %f %f %f' % \
                           (xname, dname, a, b, c, alpha, beta, gamma))

            if self._new_column_suffix:
                suffix = self._new_column_suffix
                column_counter = 0
                labout_command = 'labout file_number 1' 
                for column in column_names_by_file[hklin]:
                    column_counter += 1
                    labin_command += ' E%d=%s_%s' % \
                                     (column_counter, column, suffix)

                self.input(labout_command)
                
            self.close_wait()

            try:
                self.check_for_errors()
                self.check_ccp4_errors()

            except RuntimeError, e:
                # something went wrong; remove the output file
                try:
                    os.remove(self.get_hklout())
                except:
                    pass
                raise e
                
            return self.get_ccp4_status()

    return CadWrapper()
