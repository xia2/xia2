#!/usr/bin/env python
# XInfo.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# A handler for .xinfo files, an example of which can be found in:
#
# os.path.join(os.environ['XIA2_ROOT'], 'Data', 'Test', 'Xinfo', '1vr9.xinfo')
#
# This file should record some metadata about the experiment, and contain
# enough information to solve the structure. A similar .xinfo file
# will be needed & generated in xia2dc.
#
# FIXME 25/AUG/06 Something similar will be needed by xia2dc, and will
#                 need to be populated by that program based on
#                 flourescence scans and so on. xia2dc will, however,
#                 require a minimally populated .xinfo file for input.
#                 Comment 27/OCT/06 something like this will also be
#                 needed for the xia2ss phase as well...
#
# FIXME 25/AUG/06 I need to implement a "wizard" for generating the .xinfo
#                 file because it's not particularly helpful or friendly
#                 in the amount of information it contains.
#
# FIXME 25/AUG/06 Need to implement a system to ensure that the datasets
#                 point at different sweeps, not two of them pointing
#                 a the same sweep. Will allow two very similar looking
#                 wavelength definitions (i.e. with the same lambda) for
#                 one crystal because these could pertain to RIP, and may
#                 correspond to different f', f'' values (although, will
#                 these change as a function of radiation damage? unlikely)
#                 FIXME I need to find this out to get a proper structure!
#
# FIXED 30/AUG/06 Probably should redefine DATASET as SWEEP to get a more
#                 accurate mapping to the MTZ hierarchy. For the interim
#                 I could allow either. So, for the moment, we have:
#
#                 WAVELENGTH -> MTZ dataset
#                 PROJECT -> MTZ project
#                 CRYSTAL -> MTZ dataset
#
#                 Fix this... later!
#
# FIXED 05/SEP/06 Need to kill current definition of DATASET so I can use
#                 it when going to xia2ss as a dataset. => sed /dataset/sweep/
#                 for xia2dpa. Done, and documentation, examples are
#                 updated.
#
# FIXED 05/SEP/06 Need to produce an object hierarchy based on Schema/Object
#                 to give object versioning which will represent the contents
#                 of the .xinfo+ file, that is, the representation of this
#                 information during the data reduction process, to make the
#                 join from the input-to-dpa .xinfo file and the xia2ss
#                 .xinfo input file. This will be:
#
#                 XProject
#                 XCrystal
#                 XWavelength
#                 XSweep
#                 XDataset
#
#                 A slightly poor naming convention, but it will do the
#                 job. So - the properties of these are defined in
#                 /Schema. Note well that these have subproperties
#                 (e.g. sweep resolution) which will also have to be
#                 defined as classes...
#
# FIXED 19/SEP/06 also allow the DISTANCE to be provided in the .xinfo
#                 file in the same way as the beam - unfortunately this
#                 is sometimes wrong and very hard to find right ;o(.
#                 See NaI/Lysozyme data collected on 14.1 in /data1/graeme.
#
# FIXED 26/SEP/06 allow for INTEGRATED_REFLECTION_FILE in sweep record in place
#                 of or in addition to the DIRECTORY, TEMPLATE to allow for
#                 development of the scaling independently of the scaling
#                 &c. The same could be applied to the scaled reflections
#                 belonging to a wavelength etc.
#
# FIXED 27/OCT/06 need to be able to override or provide the epoch
#                 information in the .xinfo file to cope with cases
#                 where this information is not in the image headers.
#
# FIXED 15/NOV/06 allow for a role for wavelengths, for example in shelxc/d/e
#                 it would help matters to define peak, inflection, low and
#                 high remote. This should be done automatically in a perfect
#                 world. In fact, this is best done by assigning one of these
#                 names to the wavelength name - job done!
#
# FIXME 04/DEC/06 need to also allow for starting from post-scaled data -
#                 this will make debugging easier and also provide a
#                 xia2ha like functionality.
#

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

        self._validate()

        return

    def __repr__(self):
        '''Generate a string representation of the project.'''

        repr = 'Project %s\n' % self._project
        for crystal in self._crystals.keys():
            repr += 'Crystal %s\n' % crystal
            repr += '%s\n' % str(self._crystals[crystal])

        # remove a trailing newline...

        return repr[:-1]

    def get_project(self):
        return self._project

    def get_crystals(self):
        return self._crystals

    def _validate(self):
        '''Validate the structure of this object, ensuring that
        everything looks right... raise exception if I find something
        wrong.'''

        return True

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
            if 'BEGIN CRYSTAL ' in record:
                crystal_records = [record]
                while True:
                    i += 1
                    record = project_records[i]
                    crystal_records.append(record)
                    if 'END CRYSTAL ' in record:
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
            if 'BEGIN CRYSTAL ' in record:

                # we should only ever have one of these records in
                # a call to this method

                if crystal != '':
                    raise RuntimeError, 'error in BEGIN CRYSTAL record'

                crystal = record.replace('BEGIN CRYSTAL ', '').strip()
                if self._crystals.has_key(crystal):
                    raise RuntimeError, 'crystal %s already exists' % \
                          crystal

                # cardinality:
                #
                # sequence - exactly one, a long string
                # wavelengths - a dictionary of data structures keyed by the
                #               wavelength id
                # sweeps - a dictionary of data structures keyed by the
                #          sweep id
                # ha_info - exactly one dictionary containing the heavy atom
                #           information

                self._crystals[crystal] = {
                    'sequence':'',
                    'wavelengths':{},
                    'sweeps':{},
                    'ha_info':{},
                    'crystal_data':{}
                    }

            # next look for interesting stuff in the data structure...
            # starting with the sequence

            if 'BEGIN AA_SEQUENCE' in record:
                sequence = ''
                i += 1
                record = crystal_records[i]
                while record != 'END AA_SEQUENCE':
                    if not '#' in record or '!' in record:
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

            # look for data blocks

            if 'BEGIN CRYSTAL_DATA' in record:
                i += 1
                record = crystal_records[i]
                while not 'END CRYSTAL_DATA' in record:
                    key = record.split()[0].lower()
                    value = record.replace(record.split()[0], '').strip()
                    self._crystals[crystal]['crystal_data'][key] = value
                    i += 1
                    record = crystal_records[i]

            if 'BEGIN WAVELENGTH ' in record:
                wavelength = record.replace('BEGIN WAVELENGTH ', '').strip()

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

                    # deal with a nested WAVELENGTH_STATISTICS block

                    if 'BEGIN WAVELENGTH_STATISTICS' in record:
                        self._crystals[crystal]['wavelengths'][
                            wavelength]['statistics'] = { }
                        i += 1
                        record = crystal_records[i]
                        while not 'END WAVELENGTH_STATISTICS' in record:
                            key, value = tuple(record.split())
                            self._crystals[crystal]['wavelengths'][
                                wavelength]['statistics'][
                                key.lower()] = float(value)
                            i += 1
                            record = crystal_records[i]

                    # else deal with the usual tokens

                    key = record.split()[0].lower()

                    if key == 'resolution':

                        lst = record.split()

                        if len(lst) < 2 or len(lst) > 3:
                            raise RuntimeError, 'resolution dmin [dmax]'

                        if len(lst) == 2:
                            dmin = float(lst[1])

                            self._crystals[crystal]['wavelengths'][
                                wavelength]['dmin'] = dmin

                        else:
                            dmin = min(map(float, lst[1:]))
                            dmax = max(map(float, lst[1:]))

                            self._crystals[crystal]['wavelengths'][
                                wavelength]['dmin'] = dmin

                            self._crystals[crystal]['wavelengths'][
                                wavelength]['dmax'] = dmax

                        i += 1
                        record = crystal_records[i]
                        continue

                    if len(record.split()) == 1:
                        raise RuntimeError, 'missing value for token %s' % \
                              record.split()[0]

                    try:
                        value = float(record.split()[1])
                    except ValueError, e:
                        value = record.replace(record.split()[0], '').strip()

                    self._crystals[crystal]['wavelengths'][
                        wavelength][key] = value
                    i += 1
                    record = crystal_records[i]

            # next look for sweeps, checking that the wavelength
            # definitions match up...

            if 'BEGIN SWEEP' in record:
                sweep = record.replace('BEGIN SWEEP', '').strip()

                if self._crystals[crystal]['sweeps'].has_key(sweep):
                    raise RuntimeError, \
                          'sweep %s already exists for crystal %s' % \
                          (sweep, crystal)

                self._crystals[crystal]['sweeps'][sweep] = { }
                self._crystals[crystal]['sweeps'][sweep][
                    'excluded_regions'] = []

                # in here I expect to find IMAGE, DIRECTORY, WAVELENGTH
                # and optionally BEAM

                # FIXME 30/OCT/06 this may not be the case, for instance
                # if an INTEGRATED_REFLECTION_FILE record is in there...
                # c/f XProject.py, XSweep.py

                i += 1
                record = crystal_records[i]

                # populate this with interesting things
                while not 'END SWEEP' in record:
                    # allow for WAVELENGTH_ID (bug # 2358)
                    if 'WAVELENGTH_ID' == record.split()[0]:
                        record = record.replace('WAVELENGTH_ID',
                                                'WAVELENGTH')

                    if 'WAVELENGTH' == record.split()[0]:
                        wavelength = record.replace('WAVELENGTH', '').strip()
                        if not wavelength in self._crystals[crystal][
                            'wavelengths'].keys():
                            raise RuntimeError, \
                                  'wavelength %s unknown for crystal %s' % \
                                  (wavelength, crystal)

                        self._crystals[crystal]['sweeps'][sweep][
                            'wavelength'] = wavelength

                    elif 'BEAM' == record.split()[0]:
                        beam = map(float, record.split()[1:])
                        self._crystals[crystal]['sweeps'][sweep][
                            'beam'] = beam

                    elif 'DISTANCE' == record.split()[0]:
                        distance = float(record.split()[1])
                        self._crystals[crystal]['sweeps'][sweep][
                            'distance'] = distance

                    elif 'EPOCH' == record.split()[0]:
                        epoch = int(record.split()[1])
                        self._crystals[crystal]['sweeps'][sweep][
                            'epoch'] = epoch

                    elif 'REVERSEPHI' == record.split()[0]:
                        self._crystals[crystal]['sweeps'][sweep][
                            'reversephi'] = True

                    elif 'START_END' == record.split()[0]:
                        start_end = map(int, record.split()[1:])
                        if len(start_end) != 2:
                            raise RuntimeError, \
                                  'START_END start end, not "%s"' % record
                        self._crystals[crystal]['sweeps'][sweep][
                            'start_end'] = start_end

                    elif 'EXCLUDE' == record.split()[0]:
                        if record.split()[1].upper() == 'ICE':
                            self._crystals[crystal]['sweeps'][sweep][
                                'ice'] = True 
                        else:
                            excluded_region = map(float, record.split()[1:])
                            if len(excluded_region) != 2:
                                raise RuntimeError, \
                                      'EXCLUDE upper lower, not "%s". \
                                       eg. EXCLUDE 2.28 2.22' % record
                            if excluded_region[0] <= excluded_region[1]:
                                raise RuntimeError, \
                                      'EXCLUDE upper lower, where upper \
                                       must be greater than lower (not "%s").\n\
                                       eg. EXCLUDE 2.28 2.22' % record
                            self._crystals[crystal]['sweeps'][sweep][
                                'excluded_regions'].append(excluded_region)

                    else:
                        key = record.split()[0]
                        value = record.replace(key, '').strip()
                        self._crystals[crystal]['sweeps'][sweep][
                            key] = value

                    i += 1
                    record = crystal_records[i]

            # now look for one-record things

            if 'SCALED_MERGED_REFLECTION_FILE' in record:
                self._crystals[crystal][
                    'scaled_merged_reflection_file'] = \
                    record.replace('SCALED_MERGED_REFLECTION_FILE',
                                   '').strip()

            if 'REFERENCE_REFLECTION_FILE' in record:
                self._crystals[crystal][
                    'reference_reflection_file'] = \
                    record.replace('REFERENCE_REFLECTION_FILE',
                                   '').strip()

            if 'FREER_FILE' in record:

                # free file also needs to be used for indexing reference to
                # make any sense at all...

                self._crystals[crystal][
                    'freer_file'] = record.replace('FREER_FILE', '').strip()
                self._crystals[crystal][
                    'reference_reflection_file'] = \
                    record.replace('FREER_FILE', '').strip()

            # user assigned spacegroup and cell constants
            if 'USER_SPACEGROUP' in record:
                self._crystals[crystal][
                    'user_spacegroup'] = record.replace(
                    'USER_SPACEGROUP', '').strip()

            if 'USER_CELL' in record:
                self._crystals[crystal][
                    'user_cell'] = tuple(map(float, record.split()[1:]))




if __name__ == '__main__':
    import os

    xi = XInfo(os.path.join(os.environ['XIA2_ROOT'], 'Data', 'Test', 'Xinfo', '1vrm-post-scale.xinfo'))

    print xi
