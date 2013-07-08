#!/usr/bin/env python
# Syminfo.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 13th June 2006
#
# A handler singleton for the information in the CCP4 symmetry library
# syminfo.lib.
#

import sys
import os
import copy
import re

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'
if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

class _Syminfo():
    '''An object to retain symmetry information.'''

    def __init__(self):
        '''Initialise everything.'''

        self._parse_symop()

        self._int_re = re.compile('^[0-9]*$')

        return

    def _generate_lattice(self,
                          lattice_type,
                          shortname):
        '''Generate a lattice name (e.g. tP) from TETRAGONAL and P422.'''

        hash = {'TRICLINIC':'a',
                'MONOCLINIC':'m',
                'ORTHORHOMBIC':'o',
                'TETRAGONAL':'t',
                'TRIGONAL':'h',
                'HEXAGONAL':'h',
                'CUBIC':'c'}

        lattice = '%s%s' % (hash[lattice_type.upper()],
                            shortname[0].upper())

        if lattice[1] != 'H':
            return lattice
        else:
            return '%sR' % lattice[0]

    def _parse_symop(self):
        '''Parse the CCP4 symop library.'''

        self._symop = { }
        self._spacegroup_name_to_lattice = { }
        self._spacegroup_short_to_long = { }
        self._spacegroup_long_to_short = { }
        self._spacegroup_name_to_number = { }
        self._spacegroup_name_to_pointgroup = { }

        current = 0

        for line in open(os.path.join(os.environ['CLIBD'],
                                      'symop.lib')).readlines():
            if line[0] != ' ':
                list = line.split()
                index = int(list[0])
                shortname = list[3]

                lattice_type = list[5].lower()
                longname = line.split('\'')[1]

                lattice = self._generate_lattice(lattice_type,
                                                 shortname)

                pointgroup = ''
                for token in longname.split():
                    if len(longname.split()) <= 2:
                        pointgroup += token[0]
                    elif token[0] != '1':
                        pointgroup += token[0]

                self._symop[index] = {'index':index,
                                      'lattice_type':lattice_type,
                                      'lattice':lattice,
                                      'name':shortname,
                                      'longname':longname,
                                      'pointgroup':pointgroup,
                                      'symops':0,
                                      'operations':[]}

                if not self._spacegroup_name_to_lattice.has_key(shortname):
                    self._spacegroup_name_to_lattice[shortname] = lattice

                if not self._spacegroup_name_to_number.has_key(shortname):
                    self._spacegroup_name_to_number[shortname] = index

                if not self._spacegroup_long_to_short.has_key(longname):
                    self._spacegroup_long_to_short[longname] = shortname

                if not self._spacegroup_short_to_long.has_key(shortname):
                    self._spacegroup_short_to_long[shortname] = longname

                if not self._spacegroup_name_to_pointgroup.has_key(shortname):
                    self._spacegroup_name_to_pointgroup[shortname] = pointgroup

                current = index

            else:

                self._symop[current]['symops'] += 1
                self._symop[current]['operations'].append(line.strip())

        return

    def get_syminfo(self, spacegroup_number):
        '''Return the syminfo for spacegroup number.'''
        return copy.deepcopy(self._symop[spacegroup_number])

    def get_pointgroup(self, name):
        '''Get the pointgroup for this spacegroup, e.g. P422 for P43212.'''

        if self._spacegroup_long_to_short.has_key(name):
            name = self._spacegroup_long_to_short[name]

        return self._spacegroup_name_to_pointgroup[name.replace(' ', '')]

    def get_lattice(self, name):
        '''Get the lattice for a named spacegroup.'''

        # check that this isn't already a lattice name
        if name in ['aP', 'mP', 'mC', 'oP', 'oC', 'oI',
                    'oF', 'tP', 'tI', 'hR', 'hP', 'cP',
                    'cI', 'cF']:
            return name


        # introspect on the input to figure out what to return

        if type(name) == type(1):
            return self.get_syminfo(name)['lattice']

        # check that this isn't a string of an integer - if it is
        # repeat above...

        if self._int_re.match(name):
            name = int(name)
            return self.get_syminfo(name)['lattice']

        # ok this should be a "pure" spacegroup string

        if ':' in name:
            assert(name.startswith('R'))
            name = name.split(':')[0].replace('R', 'H')

        if self._spacegroup_long_to_short.has_key(name):
            name = self._spacegroup_long_to_short[name]

        # The short name should not have a space in, sometimes this may
        # be foxed by someone passing in P 21 - this should fix it...
        return self._spacegroup_name_to_lattice[name.replace(' ', '')]

    def get_spacegroup_numbers(self):
        '''Get a list of all spacegroup numbers.'''

        numbers = self._symop.keys()
        numbers.sort()

        return numbers

    def spacegroup_number_to_name(self, spacegroup_number):
        '''Return the name of this spacegroup.'''

        return self._symop[spacegroup_number]['name']

    def spacegroup_name_to_number(self, spacegroup):
        '''Return the number corresponding to this spacegroup.'''

        # check have not had number passed in

        try:
            number = int(spacegroup)
            return number
        except:
            pass

        spacegroup = spacegroup.strip()

        # check if this is a disputed spacegroup name

        if ':' in spacegroup and 'H' in spacegroup:
            spacegroup = spacegroup.split(':')[0].strip().replace('R', 'H')

        # next check to see if this is the long form

        if self._spacegroup_long_to_short.has_key(spacegroup):
            spacegroup = self._spacegroup_long_to_short[spacegroup]

        return self._spacegroup_name_to_number[spacegroup]

    def get_num_symops(self, spacegroup_number):
        '''Get the number of symmetry operations that spacegroup
        number has.'''

        return self._symop[spacegroup_number]['symops']

    def get_symops(self, spacegroup):
        '''Get the operations for spacegroup number N.'''

        try:
            number = int(spacegroup)
        except ValueError, e:
            number = self.spacegroup_name_to_number(spacegroup)

        return self._symop[number]['operations']

    def get_subgroups(self, spacegroup):
        '''Get the list of spacegroups which are included entirely in this
        spacegroup.'''

        try:
            number = int(spacegroup)
        except ValueError, e:
            number = self.spacegroup_name_to_number(spacegroup)

        symops = self._symop[number]['operations']

        subgroups = []

        for j in range(230):
            sub = True
            for s in self._symop[j + 1]['operations']:
                if not s in symops:
                    sub = False
            if sub:
                subgroups.append(self.spacegroup_number_to_name(j + 1))

        return subgroups

Syminfo = _Syminfo()

if __name__ == '__main__':
    for arg in sys.argv[1:]:
        print Syminfo.get_pointgroup(arg)
        print Syminfo.get_lattice(arg)
