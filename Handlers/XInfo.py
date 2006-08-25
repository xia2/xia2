#!/usr/bin/env python
# XInfo.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
# 
# A handler for .xinfo files, an example of which can be found in:
# 
# os.path.join(os.environ['DPA_ROOT'], 'Data', 'Test', 'Xinfo', '1vr9.xinfo')
# 
# This file should record some metadata about the experiment, and contain 
# enough information to solve the structure. A similar .xinfo file
# will be needed & generated in xia2dc.
# 
# FIXME 25/AUG/06 Something similar will be needed by xia2dc, and will 
#                 need to be populated by that program based on 
#                 flourescence scans and so on. xia2dc will, however,
#                 require a minimally populated .xinfo file for input.
# 
# FIXME 25/AUG/06 I need to implement a "wizard" for generating the .xinfo
#                 file because it's not particularly helpful or friendly
#                 in the amount of information it contains.

class XInfo:
    '''A class to represent all of the input to the xia2dpa system, with
    enough information to allow structure solution, as parsed from a
    .xinfo file, an example of which is in the source code.'''

    def __init__(self, xinfo_file):
        '''Initialise myself from an input .xinfo file.'''

        # first initialise all of the data structures which will hold the
        # information...

        self._project = None
        self._crystals = { }

        # read the contents of the xinfo file

        self._parse_project(xinfo_file)

        return

    def __repr__(self):
        '''Generate a string representation of the project.'''

        repr = 'Project %s\n' % self._project
        for crystal in self._crystals.keys():
            repr += 'Crystal %s\n' % crystal
            repr += '%s\n' % str(self._crystals[crystal])
            
        # remove a trailing newline...
        
        return repr[:-1]

    def _parse_project(self, xinfo_file):
        '''Parse & validate the contents of the .xinfo file. This parses the
        project element (i.e. the whole thing..)'''

        project_records = []

        for r in open(xinfo_file, 'r').readlines():
            record = r.strip()
            if len(record) == 0:
                pass
            elif record[0] == '!' or record[0] == '#':
                pass
            else :
                # then it may contain something useful...
                project_records.append(record)

        # so now we have loaded the whole file into memory stripping
        # out the crud... let's look for something useful

        for i in range(len(project_records)):
            record = project_records[i]
            if 'BEGIN PROJECT' in record:
                self._project = record.replace('BEGIN PROJECT', '').strip()
            if 'END PROJECT' in record:
                if not self._project == record.replace(
                    'END PROJECT', '').strip():
                    raise RuntimeError, 'error parsing END PROJECT record'

            # next look for crystals
            if 'BEGIN CRYSTAL' in record:
                crystal_records = [record]
                while True:
                    i += 1
                    record = project_records[i]
                    crystal_records.append(record)
                    if 'END CRYSTAL' in record:
                        break

                self._parse_crystal(crystal_records)
                
            # that's everything, because parse_crystal handles
            # the rest...

        return

    def _parse_crystal(self, crystal_records):
        '''Parse the interesting information out of the crystal
        description.'''

        crystal = ''

        for i in range(len(crystal_records)):
            record = crystal_records[i]
            if 'BEGIN CRYSTAL' in record:
                
                # we should only ever have one of these records in
                # a call to this method
                
                if crystal != '':
                    raise RuntimeError, 'error in BEGIN CRYSTAL record'
                
                crystal = record.replace('BEGIN CRYSTAL', '').strip()
                if self._crystals.has_key(crystal):
                    raise RuntimeError, 'crystal %s already exists' % \
                          crystal

                # cardinality:
                # 
                # sequence - exactly one, a long string
                # wavelengths - a dictionary of data structures keyed by the
                #               wavelength id
                # datasets - a dictionary of data structures keyed by the
                #            dataset id
                # ha_info - exactly one dictionary containing the heavy atom
                #           information

                self._crystals[crystal] = {
                    'sequence':'',
                    'wavelengths':{},
                    'datasets':{},
                    'ha_info':{}
                    }

            # next look for interesting stuff in the data structure...
            # starting with the sequence

            if 'BEGIN AA_SEQUENCE' in record:
                sequence = ''
                i += 1
                record = crystal_records[i]
                while record != 'END AA_SEQUENCE':
                    sequence += record.strip()
                    i += 1
                    record = crystal_records[i]

                if self._crystals[crystal]['sequence'] != '':
                    raise RuntimeError, 'error two SEQUENCE records found'

                self._crystals[crystal]['sequence'] = sequence

            # look for heavy atom information

            if 'BEGIN HA_INFO' in record:
                i += 1
                record = crystal_records[i]
                while record != 'END HA_INFO':
                    key = record.split()[0].lower()
                    value = record.split()[1]
                    # things which are numbers are integers...
                    if 'number' in key:
                        value = int(value)
                    self._crystals[crystal]['ha_info'][key] = value
                    i += 1
                    record = crystal_records[i]

            # look for wavelength definitions
            # FIXME need to check that there are not two wavelength
            # definitions with the same numerical value for the wavelength -
            # unless this is some way of handling RIP? maybe a NOFIXME.

            if 'BEGIN WAVELENGTH' in record:
                wavelength = record.replace('BEGIN WAVELENGTH', '').strip()

                # check that this is a new wavelength definition
                if self._crystals[crystal]['wavelengths'].has_key(wavelength):
                    raise RuntimeError, \
                          'wavelength %s already exists for crystal %s' % \
                          (wavelength, crystal)
                
                self._crystals[crystal]['wavelengths'][wavelength] = { }
                i += 1
                record = crystal_records[i]

                # populate this with interesting things                
                while not 'END WAVELENGTH' in record:
                    key = record.split()[0].lower()
                    value = float(record.split()[1])
                    self._crystals[crystal]['wavelengths'][
                        wavelength][key] = value
                    i += 1
                    record = crystal_records[i]
                
            # next look for datasets, checking that the wavelength
            # definitions match up...

            if 'BEGIN DATASET' in record:
                dataset = record.replace('BEGIN DATASET', '').strip()
                
                if self._crystals[crystal]['datasets'].has_key(dataset):
                    raise RuntimeError, \
                          'dataset %s already exists for crystal %s' % \
                          (dataset, crystal)

                self._crystals[crystal]['datasets'][dataset] = { }

                # in here I expect to find IMAGE, DIRECTORY, WAVELENGTH
                # and optionally BEAM

                i += 1
                record = crystal_records[i]

                # populate this with interesting things                
                while not 'END DATASET' in record:                
                    if 'WAVELENGTH' == record.split()[0]:
                        wavelength = record.replace('WAVELENGTH', '').strip()
                        if not wavelength in self._crystals[crystal][
                            'wavelengths'].keys():
                            raise RuntimeError, \
                                  'wavelength %s unknown for crystal %s' % \
                                  (wavelength, crystal)

                        self._crystals[crystal]['datasets'][dataset][
                            'wavelength'] = wavelength

                    elif 'BEAM' == record.split()[0]:
                        beam = map(float, record.split()[1:])
                        self._crystals[crystal]['datasets'][dataset][
                            'beam'] = beam

                    else:
                        key = record.split()[0]
                        value = record.replace(key, '').strip()
                        self._crystals[crystal]['datasets'][dataset][
                            key] = value

                    i += 1
                    record = crystal_records[i]

                    
                                                                          
            
if __name__ == '__main__':
    import os

    xi = XInfo(os.path.join(os.environ['DPA_ROOT'], 'Data', 'Test', 'Xinfo', '1vr9.xinfo'))

    print xi
                    
