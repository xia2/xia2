#!/usr/bin/env python
# CommandLine.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 12th June 2006
# 
# A handler for all of the information which may be passed in on the command
# line. This singleton object should be able to handle the input, structure
# it and make it available in a useful fashion.
# 
# This is a hook into a global data repository.
# 
# Modification log:
# 
# 21/JUN/06 - Added in parsing of image (passed in on -image token, or
#             last token) to template & directory to work with. Note 
#             well - I need to think more carefully about this in the
#             future, though this solution may scale...
# 
# 16/AUG/06 - FIXED - need to be able to handle a resolution limit in here 
#             as well as any other information our user may wish to pass
#             in on the comand line, for example a lattice or a spacegroup.
#             See 04/SEP/06 below.
# 
# 23/AUG/06 - FIXME - need to add handling of the lattice input in particular,
#             since this is directly supported by Mosflm.py...
#
# 04/SEP/06 - FIXED - need to be able to pass in a resolution limit to
#             work to, for development purposes (this should become
#             automatic in the future.)
#
# 07/FEB/07 - FIXME need flags to control "experimental" functionality
#             e.g. the phasing pipeline - for instance this could
#             be -phase to perform phasing on the scaled data.
# 
#             At the moment the amount of feedback between the phasing
#             and the rest of the data reduction is non existent.

import sys
import os
import exceptions

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'
if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

from Schema.Object import Object
from Experts.FindImages import image2template_directory
from Schema.XProject import XProject

class _CommandLine(Object):
    '''A class to represent the command line input.'''

    def __init__(self):
        '''Initialise all of the information from the command line.'''

        Object.__init__(self)

        return

    def setup(self):
        '''Set everything up...'''

        # things which are single token flags...

        self._read_trust_timestamps()
        self._read_quick()
        self._read_migrate_data()

        try:
            self._read_beam()
        except:
            raise RuntimeError, self._help_beam()

        try:
            self._read_first_last()
        except:
            raise RuntimeError, self._help_first_last()

        try:
            self._read_image()
        except exceptions.Exception, e:
            raise RuntimeError, '%s (%s)' % \
                  (self._help_image(), str(e))

        try:
            self._read_project_name()
        except exceptions.Exception, e:
            raise RuntimeError, '%s (%s)' % \
                  (self._help_project_name(), str(e))

        try:
            self._read_atom_name()
        except exceptions.Exception, e:
            raise RuntimeError, '%s (%s)' % \
                  (self._help_atom_name(), str(e))

        try:
            self._read_crystal_name()
        except exceptions.Exception, e:
            raise RuntimeError, '%s (%s)' % \
                  (self._help_crystal_name(), str(e))
        
        try:
            self._read_lattice_spacegroup()
        except exceptions.Exception, e:
            raise RuntimeError, '%s (%s)' % \
                  (self._help_lattice_spacegroup(), str(e))

        try:
            self._read_resolution_limit()
        except exceptions.Exception, e:
            raise RuntimeError, '%s (%s)' % \
                  (self._help_resolution_limit(), str(e))

        # FIXME why is this commented out??! - uncomment this though may
        # want to explain exactly what is wrong...

        try:
            self._read_xinfo()
        except exceptions.Exception, e:
            raise RuntimeError, '%s (%s)' % \
                  (self._help_xinfo(), str(e))

        return

    # command line parsers, getters and help functions.

    def _read_beam(self):
        '''Read the beam centre from the command line.'''

        index = -1

        try:
            index = sys.argv.index('-beam')
        except ValueError, e:
            # the token is not on the command line
            self.write('No beam passed in on the command line')
            self._beam = (0.0, 0.0)
            return

        if index < 0:
            raise RuntimeError, 'negative index'

        try:
            beam = sys.argv[index + 1].split(',')
        except IndexError, e:
            raise RuntimeError, '-beam correct use "-beam x,y"'

        if len(beam) != 2:
            raise RuntimeError, '-beam correct use "-beam x,y"'

        self.write('Beam passed on the command line: %7.2f %7.2f' % \
                   (float(beam[0]), float(beam[1])))

        self._beam = (float(beam[0]), float(beam[1]))

        return

    def _help_beam(self):
        '''Return a help string for the read beam method.'''
        return '-beam x,y'

    def get_beam(self):
        return self._beam

    def _read_first_last(self):
        '''Read first, last images from the command line.'''

        index = -1

        try:
            index = sys.argv.index('-first_last')
        except ValueError, e:
            self.write('No first_last passed in on command line')
            self._first_last = (-1, -1)
            return

        if index < 0:
            raise RuntimeError, 'negative index'

        try:
            first, last = tuple(map(int, sys.argv[index + 1].split(',')))
        except IndexError, e:
            raise RuntimeError, '-first_last first,last'

        self._first_last = first, last

        self.write('first_last passed in on command line as %d, %d' % \
                   self._first_last)

        return

    def _help_first_last(self):
        return '-first_last first,last'

    def get_first_last(self):
        return self._first_last

    def _help_image(self):
        '''Return a string for explaining the -image method.'''
        return '-image /path/to/an/image_001.img'

    def _read_image(self):
        '''Read image information from the command line.'''

        index = -1

        try:
            index = sys.argv.index('-image')
        except ValueError, e:
            # the token is not on the command line
            self._default_template = None
            self._default_directory = None
            self._default_image = None
            self.write('No image passed in on the command line')
            return

        image = sys.argv[index + 1]

        # check if there is a space in the image name - this happens and it
        # looks like the python input parser will split it even if the
        # space is escaped or it is quoted

        if image[-1] == '\\':
            try:
                image = '%s %s' % (sys.argv[index + 1][:-1],
                                   sys.argv[index + 2])
            except:
                raise RuntimeError, 'image name ends in \\'

        template, directory = image2template_directory(image)
        self._default_template = template
        self._default_directory = directory
        self._default_image = image
        return

    def _read_lattice_spacegroup(self):
        '''Check for -lattice or -spacegroup tokens on the command
        line.'''

        # have to enforce not making both selections...

        index_lattice = -1

        try:
            index_lattice = sys.argv.index('-lattice')

            # FIXME need to check that this token exists on the
            # command line and that the value is a meaningful
            # crystallographic lattice...
            
            self._default_lattice = sys.argv[index_lattice + 1]

        except ValueError, e:
            # this token is not on the command line
            self._default_lattice = None

        # FIXME need to check for the spacegroup and do something
        # sensible with it... but this will require implementing
        # this for all of the interfaces, which is not yet done...

        return

    def _help_lattice_spacegroup(self):
        '''Help for the lattice/spacegroup options.'''
        return '(-lattice mP|-spacegroup p2)'

    def _read_resolution_limit(self):
        '''Search for resolution limit on the command line - at the
        moment just the high resolution limit.'''

        try:
            index = sys.argv.index('-resolution')

        except ValueError, e:
            self._default_resolution_limit = 0.0
            return

        self._default_resolution_limit = float(sys.argv[index + 1])
        
        return

    def _help_resolution_limit(self):
        return '-resolution 1.6'

    def get_resolution_limit(self):
        return self._default_resolution_limit

    def _read_atom_name(self):
        try:
            index = sys.argv.index('-atom')

        except ValueError, e:
            self._default_atom_name = None
            return

        self._default_atom_name = sys.argv[index + 1]
        
        return

    def _help_atom_name(self):
        return '-atom se'

    def get_atom_name(self):
        return self._default_atom_name

    def _read_project_name(self):
        try:
            index = sys.argv.index('-project')

        except ValueError, e:
            self._default_project_name = None
            return

        self._default_project_name = sys.argv[index + 1]
        
        return

    def _help_project_name(self):
        return '-project foo'

    def get_project_name(self):
        return self._default_project_name

    def _read_crystal_name(self):
        try:
            index = sys.argv.index('-crystal')

        except ValueError, e:
            self._default_crystal_name = None
            return

        self._default_crystal_name = sys.argv[index + 1]
        
        return

    def _help_crystal_name(self):
        return '-crystal foo'

    def get_crystal_name(self):
        return self._default_crystal_name

    def _read_xinfo(self):
        try:
            index = sys.argv.index('-xinfo')
        except ValueError, e:
            self.write('No .xinfo passed in on command line')
            self._xinfo = None
            return

        if index < 0:
            raise RuntimeError, 'negative index'

        self._xinfo = XProject(sys.argv[index + 1])
            
        return

    def _help_xinfo(self):
        return '-xinfo example.xinfo'

    def get_xinfo(self):
        '''Return the XProject.'''
        return self._xinfo
    
    def get_template(self):
        return self._default_template

    def get_directory(self):
        return self._default_directory

    def get_image(self):
        return self._default_image

    def get_lattice(self):
        return self._default_lattice

    def get_spacegroup(self):
        raise RuntimeError, 'this needs to be implemented'

    def _read_trust_timestamps(self):

        if '-trust_timestamps' in sys.argv:
            self._trust_timestamps = True
        else:
            self._trust_timestamps = False

        return

    def get_trust_timestamps(self):
        return self._trust_timestamps

    def _read_quick(self):

        if '-quick' in sys.argv:
            self._quick = True
        else:
            self._quick = False

        return

    def get_trust_timestamps(self):
        return self._trust_timestamps

    def _read_migrate_data(self):

        if '-migrate_data' in sys.argv:
            self._migrate_data = True
        else:
            self._migrate_data = False

        return

    def get_migrate_data(self):
        return self._migrate_data

CommandLine = _CommandLine()
CommandLine.setup()

if __name__ == '__main__':
    print CommandLine.get_beam()
    print CommandLine.get_resolution_limit()
    print CommandLine.get_xinfo()
