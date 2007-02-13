#!/usr/bin/env python
# Mtzdump.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 5th June 2006
# 
# A wrapper for the CCP4 program mtzdump, for displaying the header
# information from an MTZ file.
# 
# Provides:
# 
# The content of the MTZ file header, as a dictionary.
# 

import os
import sys
import copy

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                             'Python'))

from Driver.DriverFactory import DriverFactory
from Decorators.DecoratorFactory import DecoratorFactory

def Mtzdump(DriverType = None):
    '''A factory for MtzdumpWrapper classes.'''

    DriverInstance = DriverFactory.Driver(DriverType)
    CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, 'ccp4')

    class MtzdumpWrapper(CCP4DriverInstance.__class__):
        '''A wrapper for Mtzdump, using the CCP4-ified Driver.'''

        def __init__(self):
            # generic things
            CCP4DriverInstance.__class__.__init__(self)
            self.set_executable('mtzdump')

            self._header = { }
            self._header['datasets'] = []
            self._header['dataset_info'] = { } 

            self._batches = None
            self._reflections = 0

        def dump(self):
            '''Actually print the contents of the mtz file header.'''

            self.check_hklin()

            self.start()
            self.close_wait()

            # general errors - SEGV and the like
            self.check_for_errors()
            
            # ccp4 specific errors
            self.check_ccp4_errors()
            
            # if we got this far then everything is probably peachy
            # so look for interesting information

            output = self.get_all_output()

            length = len(output)

            batches = []

            for i in range(length):
                # looking for column labels, cell, spacegroup,
                # pname xname dname - some of this is per dataset
                # so should be recorded as such in a dictionary
                # c.f. the MTZ hierarchy project/crystal/dataset

                line = output[i][:-1]

                if 'Batch number:' in line:
                    batch = int(output[i + 1])
                    if not batch in batches:
                        batches.append(batch)
                
                if 'Column Labels' in line:
                    # then the column labels are in two lines time...
                    labels = output[i + 2].strip().split()
                    self._header['column_labels'] = labels
                    
                if 'Column Types' in line:
                    # then the column types are in two lines time...
                    types = output[i + 2].strip().split()
                    self._header['column_types'] = types

                if 'Space group' in line:
                    self._header['spacegroup'] = line.split('\'')[1].strip()
                    
                if 'Dataset ID, ' in line:
                    # then the project/crystal/dataset hierarchy
                    # follows with some cell/wavelength information
                    # FIXME this only reads the first set of information...

                    block = 0
                    while output[block * 5 + i + 2].strip():
                        dataset_number = int(
                            output[5 * block + i + 2].split()[0])
                        project = output[5 * block + i + 2][10:].strip()
                        crystal = output[5 * block + i + 3][10:].strip()
                        dataset = output[5 * block + i + 4][10:].strip()
                        cell = map(float, output[5 * block + i + 5].strip(
                            ).split())
                        wavelength = float(output[5 * block + i + 6].strip())
                        
                        dataset_id = '%s/%s/%s' % \
                                     (project, crystal, dataset)
                        
                        self._header['datasets'].append(dataset_id)
                        self._header['dataset_info'][dataset_id] = { }
                        self._header['dataset_info'][
                            dataset_id]['wavelength'] = wavelength
                        self._header['dataset_info'][dataset_id
                                                     ]['cell'] = cell
                        self._header['dataset_info'][dataset_id
                                                     ]['id'] = dataset_number
                        block += 1

                if 'No. of reflections used in FILE STATISTICS' in line:
                    self._reflections = int(line.split()[-1])

            self._batches = batches
                    
            # status token has a spare "of mtzdump" to get rid of
            return self.get_ccp4_status().replace('of mtzdump', '').strip()

        def get_columns(self):
            '''Get a list of the columns and their types as tuples
            (label, type) in a list.'''

            results = []
            for i in range(len(self._header['column_labels'])):
                results.append((self._header['column_labels'][i],
                                self._header['column_types'][i]))
            return results
                
        def get_datasets(self):
            '''Return a list of available datasets.'''
            return self._header['datasets']

        def get_dataset_info(self, dataset):
            '''Get the cell, spacegroup & wavelength associated with
            a dataset. The dataset is specified by pname/xname/dname.'''
            
            result = copy.deepcopy(self._header['dataset_info'][dataset])
            result['spacegroup'] = self._header['spacegroup']
            return result

        def get_spacegroup(self):
            '''Get the spacegroup recorded for this reflection file.'''
            return self._header['spacegroup']

        def get_batches(self):
            '''Get a list of batches found in this reflection file.'''
            return self._batches

        def get_reflections(self):
            '''Return the number of reflections found in the reflection
            file.'''

            return self._reflections

    return MtzdumpWrapper()

if __name__ == '__main__':

    # do a quick test

    if not os.environ.has_key('XIA2CORE_ROOT'):
        raise RuntimeError, 'XIA2CORE_ROOT not defined'

    dpa = os.environ['XIA2_ROOT']

    hklin = os.path.join(dpa,
                         'Data', 'Test', 'Mtz', '12287_1_E1_1_10.mtz')

    hklin = os.path.join(os.environ['X2TD_ROOT'],
                         'Test', 'UnitTest', 'Interfaces',
                         'Scaler', 'Merged', 'TS00_13185_merged_free.mtz')

    if len(sys.argv) > 1:
        hklin = sys.argv[1]

    m = Mtzdump()
    m.write_log_file('mtzdump.log')
    m.set_hklin(hklin)
    print m.dump()

    columns = m.get_columns()

    for c in columns:
        print '%s (%s)' % c

    datasets = m.get_datasets()
    
    for d in datasets:
        print '%s' % d
        info = m.get_dataset_info(d)
        print '%s (%6.4fA) %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % \
              (info['spacegroup'], info['wavelength'],
               info['cell'][0], info['cell'][1], info['cell'][2],
               info['cell'][1], info['cell'][4], info['cell'][5])


