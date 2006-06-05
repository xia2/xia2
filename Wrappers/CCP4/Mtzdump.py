#!/usr/bin/env python
# Mtzdump.py
# Maintained by G.Winter
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
            self.setExecutable('mtzdump')

            self._header = { }
            self._header['datasets'] = []
            self._header['dataset_info'] = { } 

        def dump(self):
            '''Actually print the contents of the mtz file header.'''

            self.checkHklin()

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

            for i in range(length):
                # looking for column labels, cell, spacegroup,
                # pname xname dname - some of this is per dataset
                # so should be recorded as such in a dictionary
                # c.f. the MTZ hierarchy project/crystal/dataset

                line = output[i][:-1]
                
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
                    project = output[i + 2][10:].strip()
                    crystal = output[i + 3][10:].strip()
                    dataset = output[i + 4][10:].strip()
                    cell = map(float, output[i + 5].strip().split())
                    wavelength = float(output[i + 6].strip())

                    dataset_id = '%s/%s/%s' % \
                                 (project, crystal, dataset)

                    self._header['datasets'].append(dataset_id)
                    self._header['dataset_info'][dataset_id] = { }
                    self._header['dataset_info'][dataset_id
                                                 ]['wavelength'] = wavelength
                    self._header['dataset_info'][dataset_id
                                                 ]['cell'] = cell
                    

            print self._header
                    
            # status token has a spare "of mtzdump" to get rid of
            return self.get_ccp4_status().replace('of mtzdump', '').strip()
                

    return MtzdumpWrapper()

if __name__ == '__main__':

    # do a quick test

    import os

    if not os.environ.has_key('XIA2CORE_ROOT'):
        raise RuntimeError, 'XIA2CORE_ROOT not defined'

    dpa = os.environ['DPA_ROOT']

    hklin = os.path.join(dpa,
                         'Data', 'Test', 'Mtz', '12287_1_E1_1_10.mtz')


    m = Mtzdump()
    m.setHklin(hklin)
    print m.dump()

    
