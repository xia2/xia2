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

            self._batch_header = { }

            self._batches = None
            self._reflections = 0
            self._resolution_range = (0, 0)

            self._column_ranges = { }

            self._intensities = { }

            return

        def dump_mosflm_intensities(self):
            '''Dump the intensities from a mosflm reflection file as a
            list - this will include the positions of the reflections
            in detector coordinates.'''

            self.check_hklin()

            self.start()
            self.input('nref -1')
            self.close_wait()

            intensities = [ ]

            output = self.get_all_output()

            j = 0

            while j < len(output):

                if 'LIST OF REFLECTIONS' in output[j]:

                    j += 3

                    while not '<B>' in output[j]:

                        record = output[j].split()
                        for o in output[j + 1].split():
                            record.append(o)
                        for o in output[j + 2].split():
                            record.append(o)

                        h, k, l = tuple(map(int, record[:3]))
                        batch = int(record[4])
                        I, sig_I = tuple(map(float, record[5:7]))
                        xdet, ydet = tuple(map(float, record[8:10]))

                        intensities.append((h, k, l, I, sig_I,
                                            batch, xdet, ydet))

                        j += 3
                j += 1


            return intensities

        def dump_scala_intensities(self):
            '''Dump the intensities from a scala reflection file as a
            list - this will not include the positions of the reflections
            in detector coordinates.'''

            self.check_hklin()

            self.start()
            self.input('nref -1')
            self.close_wait()

            intensities = [ ]

            output = self.get_all_output()

            j = 0

            while j < len(output):

                if 'LIST OF REFLECTIONS' in output[j]:

                    j += 3

                    while not '<B>' in output[j]:

                        record = output[j].split()

                        if record:

                            h, k, l = tuple(
                                map(int, [output[j][4 * k + 1:4 * (k + 1) + 1]
                                          for k in range(3)]))
                            
                            I, sig_I = tuple(map(float, record[3:5]))
                            
                            intensities.append((h, k, l, I, sig_I))
                        
                        j += 1
                j += 1

            return intensities

        def dump_intensities(self):
            '''Actually dump the intensities from the reflection file -
            useful for reading values from unmerged intensity files.'''

            self.check_hklin()

            self.start()
            self.input('nref -1')
            self.close_wait()

            self._intensities = { }

            output = self.get_all_output()

            j = 0

            while j < len(output):

                if 'LIST OF REFLECTIONS' in output[j]:

                    j += 3

                    while not '<B>' in output[j]:

                        record = output[j].split()
                        for o in output[j + 1].split():
                            record.append(o)
                        for o in output[j + 2].split():
                            record.append(o)

                        pm = int(record[3])

                        J = pm % 2

                        h, k, l = map(int, record[:3])

                        batch = int(record[4])

                        I, sig_I = map(float, record[5:7])

                        key = ((h, k, l), J)

                        if not self._intensities.has_key(key):
                            self._intensities[key] = []

                        self._intensities[key].append(
                            ((h, k, l), batch, I, sig_I))

                        j += 3
                j += 1


            return self._intensities

        def dump(self):
            '''Actually print the contents of the mtz file header.'''

            self._column_ranges = { }

            self.check_hklin()
            self.start()
            self.close_wait()

            # general errors - SEGV and the like
            self.check_for_errors()
            
            # ccp4 specific errors
            self.check_ccp4_errors()
            
            # if we got this far then everything is probably peachy
            # so look for interesting information - resetting before we
            # start

            self._header['datasets'] = []
            self._header['dataset_info'] = { } 

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
                    batch = int(output[i + 1].split()[0])
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

                if 'Resolution Range' in line:
                    self._resolution_range = tuple(
                        map(float, output[i + 2].replace('-', ' ').split(
                        '(')[1].split()[:2]))

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

                        if not dataset_id in self._header['datasets']:
                        
                            self._header['datasets'].append(dataset_id)
                            self._header['dataset_info'][dataset_id] = { }
                            self._header['dataset_info'][
                                dataset_id]['wavelength'] = wavelength
                            self._header['dataset_info'][
                                dataset_id]['cell'] = cell
                            self._header['dataset_info'][
                                dataset_id]['id'] = dataset_number
                            
                        block += 1

                if 'No. of reflections used in FILE STATISTICS' in line:
                    self._reflections = int(line.split()[-1])

                if 'OVERALL FILE STATISTICS' in line:
                    j = i + 6

                    line = output[j][:-1]
                    
                    while not 'No. of reflections' in line:
                        if not line.strip() or '*****' in line:
                            j += 1
                            line = output[j][:-1]
                            continue

                        # cut out the right tokens from the text
                        mn = float(line[9:16].strip())
                        mx = float(line[16:24].strip())
                        dmax = float(line.split()[-4])
                        dmin = float(line.split()[-3])
                        col = line.split()[-1]
                        line = output[j][:-1]
                        j += 1
                        
                        self._column_ranges[col] = (mn, mx, dmin, dmax)
                                    
            self._batches = batches
                    
            # status token has a spare "of mtzdump" to get rid of
            return self.get_ccp4_status().replace('of mtzdump', '').strip()

        def dump_batch_headers(self):
            '''Actually print the contents of the mtz file batch headers.'''

            self.check_hklin()
            self.start()
            self.input('batch')
            self.close_wait()

            # general errors - SEGV and the like
            self.check_for_errors()
            
            # ccp4 specific errors
            self.check_ccp4_errors()
            
            output = self.get_all_output()

            length = len(output)

            current_batch = None
            umat = None

            for j in range(length):
                if 'Batch number:' in output[j]:
                    current_batch = int(output[j + 1].strip())
                if 'Standard orientation matrix U' in output[j]:
                    umat = map(float, output[j][38:].split()) + \
                           map(float, output[j + 1][38:].split()) + \
                           map(float, output[j + 2][38:].split())

                    self._batch_header[current_batch] = {'umat': umat}

            return self.get_ccp4_status().replace('of mtzdump', '').strip()

        def get_batch_header(self, batch):
            return copy.deepcopy(self._batch_header[batch])

        def get_columns(self):
            '''Get a list of the columns and their types as tuples
            (label, type) in a list.'''

            results = []
            for i in range(len(self._header['column_labels'])):
                results.append((self._header['column_labels'][i],
                                self._header['column_types'][i]))
            return results

        def get_resolution_range(self):
            return self._resolution_range
                
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

        def get_column_range(self, column):
            '''Get the value ranges for this column.'''
            return self._column_ranges.get(column, (0.0, 0.0))

        def get_reflections(self):
            '''Return the number of reflections found in the reflection
            file.'''

            return self._reflections

    return MtzdumpWrapper()

if __name__ == '__main1__':

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
    print m.get_resolution_range()

if __name__ == '__main__':
    m = Mtzdump()

    hklin = os.path.join(os.environ['X2TD_ROOT'],
                         'XIA2', 'Mtz', '12287_1_E1_1_10.mtz')

    if len(sys.argv) > 1:
        m.set_hklin(sys.argv[1])
    else:
        m.set_hklin(hklin)

    m.dump()
    m.dump_batch_headers()

    for batch in m.get_batches():
        print '=== batch %4d ===' % batch
        print '%.4f %.4f %.4f \n%.4f %.4f %.4f \n%.4f %.4f %.4f ' % \
              tuple(m.get_batch_header(batch)['umat'])

    
