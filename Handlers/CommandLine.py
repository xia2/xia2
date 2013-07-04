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
# This is a hook into a global data repository, should mostly be replaced with
# a Phil interface.

import sys
import os
import exceptions
import copy
import traceback

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'
if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

from Experts.FindImages import image2template_directory
from Schema.XProject import XProject
from Handlers.Flags import Flags
from Handlers.Phil import PhilIndex
from Handlers.Streams import Chatter, Debug
from Handlers.PipelineSelection import add_preference
from Handlers.Executables import Executables

class _CommandLine():
    '''A class to represent the command line input.'''

    def __init__(self):
        '''Initialise all of the information from the command line.'''

        self._argv = []
        self._understood = []

        return

    def print_command_line(self):
        cl = self.get_command_line()
        Chatter.write('Command line: %s' % cl)
        return

    def get_command_line(self):
        cl = 'xia2'
        for arg in self._argv[1:]:
            cl += ' %s' % arg

        return cl

    def setup(self):
        '''Set everything up...'''

        # things which are single token flags...

        self._argv = copy.deepcopy(sys.argv)

        self._read_debug()
        self._read_interactive()
        self._read_ice()
        self._read_egg()
        self._read_uniform_sd()
        self._read_trust_timestamps()
        self._read_batch_scale()
        self._read_small_molecule()
        self._read_quick()
        self._read_chef()
        self._read_mask()
        self._read_reversephi()
        self._read_no_lattice_test()
        self._read_no_relax()
        self._read_no_profile()
        self._read_norefine()
        self._read_noremove()
        self._read_2dr()
        self._read_2da()
        self._read_2dir()
        self._read_2dia()
        self._read_3dr()
        self._read_3dir()
        self._read_3diir()
        self._read_3ds()

        # FIXME really need to fix how this works out...

        self._read_3dar()
        self._read_3dair()
        self._read_3daiir()
        self._read_migrate_data()
        self._read_zero_dose()
        self._read_free_fraction()
        self._read_free_total()

        # finer grained control over the selection of indexer, integrater
        # and scaler to use.

        self._read_indexer()
        self._read_integrater()
        self._read_scaler()
        self._read_executables()

        # flags relating to unfixed bugs...
        self._read_fixed_628()

        try:
            self._read_beam()
        except:
            raise RuntimeError, self._help_beam()

        try:
            self._read_cell()
        except:
            raise RuntimeError, self._help_cell()

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
            self._read_phil()
        except exceptions.Exception, e:
            raise RuntimeError, '%s (%s)' % \
                  (self._help_phil(), str(e))

        try:
            self._read_crystal_name()
        except exceptions.Exception, e:
            raise RuntimeError, '%s (%s)' % \
                  (self._help_crystal_name(), str(e))

        try:
            self._read_ispyb_xml_out()
        except exceptions.Exception, e:
            raise RuntimeError, '%s (%s)' % \
                  (self._help_ispyb_xml_out(), str(e))

        try:
            self._read_hdr_in()
        except exceptions.Exception, e:
            raise RuntimeError, '%s (%s)' % \
                  (self._help_hdr_in(), str(e))

        try:
            self._read_hdr_out()
        except exceptions.Exception, e:
            raise RuntimeError, '%s (%s)' % \
                  (self._help_hdr_out(), str(e))

        try:
            self._read_parallel()
        except exceptions.Exception, e:
            raise RuntimeError, '%s (%s)' % \
                  (self._help_parallel(), str(e))

        try:
            self._read_serial()
        except exceptions.Exception, e:
            raise RuntimeError, '%s (%s)' % \
                  (self._help_serial(), str(e))

        try:
            self._read_xparm()
        except exceptions.Exception, e:
            raise RuntimeError, '%s (%s)' % \
                  (self._help_xparm(), str(e))

        try:
            self._read_xparm_ub()
        except exceptions.Exception, e:
            raise RuntimeError, '%s (%s)' % \
                  (self._help_xparm_ub(), str(e))

        try:
            self._read_min_images()
        except exceptions.Exception, e:
            raise RuntimeError, '%s (%s)' % \
                  (self._help_min_images(), str(e))

        try:
            self._read_start_end()
        except exceptions.Exception, e:
            raise RuntimeError, '%s (%s)' % \
                  (self._help_start_end(), str(e))

        try:
            self._read_xparallel()
        except exceptions.Exception, e:
            raise RuntimeError, '%s (%s)' % \
                  (self._help_xparallel(), str(e))

        try:
            self._read_spacegroup()
        except exceptions.Exception, e:
            raise RuntimeError, '%s (%s)' % \
                  (self._help_spacegroup(), str(e))

        try:
            self._read_resolution()
        except exceptions.Exception, e:
            raise RuntimeError, '%s (%s)' % \
                  (self._help_resolution(), str(e))

        try:
            self._read_z_min()
        except exceptions.Exception, e:
            raise RuntimeError, '%s (%s)' % \
                  (self._help_z_min(), str(e))

        try:
            self._read_scala_secondary()
        except exceptions.Exception, e:
            raise RuntimeError, '%s (%s)' % \
                  (self._help_scala_secondary(), str(e))

        try:
            self._read_freer_file()
        except exceptions.Exception, e:
            raise RuntimeError, '%s (%s)' % \
                  (self._help_freer_file(), str(e))

        try:
            self._read_reference_reflection_file()
        except exceptions.Exception, e:
            raise RuntimeError, '%s (%s)' % \
                  (self._help_reference_reflection_file(), str(e))

        try:
            self._read_rejection_threshold()
        except exceptions.Exception, e:
            raise RuntimeError, '%s (%s)' % \
                  (self._help_rejection_threshold(), str(e))

        try:
            self._read_isigma()
        except exceptions.Exception, e:
            raise RuntimeError, '%s (%s)' % \
                  (self._help_isigma(), str(e))

        try:
            self._read_misigma()
        except exceptions.Exception, e:
            raise RuntimeError, '%s (%s)' % \
                  (self._help_misigma(), str(e))

        try:
            self._read_rmerge()
        except exceptions.Exception, e:
            raise RuntimeError, '%s (%s)' % \
                  (self._help_rmerge(), str(e))

        try:
            self._read_microcrystal()
        except exceptions.Exception, e:
            raise RuntimeError, '%s (%s)' % \
                  (self._help_microcrystal(), str(e))

        try:
            self._read_failover()
        except exceptions.Exception, e:
            raise RuntimeError, '%s (%s)' % \
                  (self._help_failover(), str(e))

        try:
            self._read_blend()
        except exceptions.Exception, e:
            raise RuntimeError, '%s (%s)' % \
                  (self._help_blend(), str(e))

        try:
            self._read_completeness()
        except exceptions.Exception, e:
            raise RuntimeError, '%s (%s)' % \
                  (self._help_completeness(), str(e))

        try:
            self._read_scale_model()
        except exceptions.Exception, e:
            raise RuntimeError, '%s (%s)' % \
                  (self._help_scale_model(), str(e))

        # FIXME add some consistency checks in here e.g. that there are
        # images assigned, there is a lattice assigned if cell constants
        # are given and so on

        try:
            self._read_xinfo()
        except exceptions.Exception, e:
            traceback.print_exc(file = open('xia2-xinfo.error', 'w'))
            raise RuntimeError, '%s (%s)' % \
                  (self._help_xinfo(), str(e))


        # finally, check that all arguments were read and raise an exception
        # if any of them were nonsense.

        nonsense = 'Unknown command-line options:'
        was_nonsense = False

        for j, argv in enumerate(sys.argv):
            if j == 0:
                continue
            if argv[0] != '-':
                continue
            if not j in self._understood:
                nonsense += ' %s' % argv
                was_nonsense = True

        if was_nonsense:
            raise RuntimeError, nonsense

        return

    # command line parsers, getters and help functions.

    def _read_beam(self):
        '''Read the beam centre from the command line.'''

        index = -1

        try:
            index = sys.argv.index('-beam')
        except ValueError, e:
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

        self._beam = (float(beam[0]), float(beam[1]))

        self._understood.append(index)
        self._understood.append(index + 1)

        Debug.write('Beam read from command line as %f %f' % \
                    self._beam)

        return

    def _help_beam(self):
        '''Return a help string for the read beam method.'''
        return '-beam x,y'

    def get_beam(self):
        return self._beam

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

        self._understood.append(index)
        self._understood.append(index + 1)

        Debug.write('Interpreted from image %s:' % image)
        Debug.write('Template %s' % template)
        Debug.write('Directory %s' % directory)

        return

    def _read_atom_name(self):
        try:
            index = sys.argv.index('-atom')

        except ValueError, e:
            self._default_atom_name = None
            return

        self._default_atom_name = sys.argv[index + 1]

        self._understood.append(index)
        self._understood.append(index + 1)

        Debug.write('Heavy atom: %s' % \
                    self._default_atom_name)

        return

    def _help_atom_name(self):
        return '-atom se'

    def get_atom_name(self):
        return self._default_atom_name

    def _read_phil(self):
        try:
            index = sys.argv.index('-phil')

        except ValueError, e:
            return

        PhilIndex.merge_param_file(sys.argv[index + 1])
        PhilIndex.get_python_object()

        self._understood.append(index)
        self._understood.append(index + 1)

        Debug.write('Phil file: %s' % sys.argv[index + 1])

        return

    def _help_phil(self):
        return '-phil parameters.phil'

    def _read_project_name(self):
        try:
            index = sys.argv.index('-project')

        except ValueError, e:
            self._default_project_name = None
            return

        self._default_project_name = sys.argv[index + 1]

        self._understood.append(index)
        self._understood.append(index + 1)
        Debug.write('Project: %s' % self._default_project_name)

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

        self._understood.append(index)
        self._understood.append(index + 1)
        Debug.write('Crystal: %s' % self._default_crystal_name)

        return

    def _help_crystal_name(self):
        return '-crystal foo'

    def get_crystal_name(self):
        return self._default_crystal_name

    def _read_xinfo(self):
        try:
            index = sys.argv.index('-xinfo')
        except ValueError, e:
            self._xinfo = None
            return

        if index < 0:
            raise RuntimeError, 'negative index (no xinfo file name given)'

        self._understood.append(index)
        self._understood.append(index + 1)

        self._xinfo = XProject(sys.argv[index + 1])

        Debug.write(60 * '-')
        Debug.write('XINFO file: %s' % sys.argv[index + 1])
        for record in open(sys.argv[index + 1], 'r').readlines():
            # don't want \n on the end...
            Debug.write(record[:-1])
        Debug.write(60 * '-')

        return

    def _help_xinfo(self):
        return '-xinfo example.xinfo'

    def set_xinfo(self, xinfo):
        self._xinfo = XProject(xinfo)

    def get_xinfo(self):
        '''Return the XProject.'''
        return self._xinfo

    def _read_xparm(self):
        try:
            index = sys.argv.index('-xparm')
        except ValueError, e:
            return

        if index < 0:
            raise RuntimeError, 'negative index'

        Flags.set_xparm(sys.argv[index + 1])

        self._understood.append(index)
        self._understood.append(index + 1)

        Debug.write('Rotation axis: %.6f %.6f %.6f' % \
            Flags.get_xparm_rotation_axis())
        Debug.write('Beam vector: %.6f %.6f %.6f' % \
            Flags.get_xparm_beam_vector())
        Debug.write('Origin: %.2f %.2f' % \
            Flags.get_xparm_origin())

        return

    def _help_xparm(self):
        return '-xparm GXPARM.XDS'

    def _read_xparm_ub(self):
        try:
            index = sys.argv.index('-xparm_ub')
        except ValueError, e:
            return

        if index < 0:
            raise RuntimeError, 'negative index'

        Flags.set_xparm_ub(sys.argv[index + 1])

        self._understood.append(index)
        self._understood.append(index + 1)

        Debug.write('Real Space A: %.2f %.2f %.2f' % \
                    tuple(Flags.get_xparm_a()))
        Debug.write('Real Space B: %.2f %.2f %.2f' % \
                    tuple(Flags.get_xparm_b()))
        Debug.write('Real Space C: %.2f %.2f %.2f' % \
                    tuple(Flags.get_xparm_c()))

        return

    def _help_xparm_ub(self):
        return '-xparm_ub GXPARM.XDS'

    def _read_parallel(self):
        try:
            index = sys.argv.index('-parallel')
        except ValueError, e:
            return

        if index < 0:
            raise RuntimeError, 'negative index'

        if int(sys.argv[index + 1]) < 0:
            raise RuntimeError, 'negative number of processors: %s' % \
                  sys.argv[index + 1]

        self._understood.append(index)
        self._understood.append(index + 1)

        Flags.set_parallel(int(sys.argv[index + 1]))
        Debug.write('Parallel set to %d' % Flags.get_parallel())

        return

    def _help_parallel(self):
        return '-parallel N'

    def _read_serial(self):
        try:
            index = sys.argv.index('-serial')
        except ValueError, e:
            return

        if index < 0:
            raise RuntimeError, 'negative index'

        self._understood.append(index)

        Flags.set_parallel(1)
        Debug.write('Serial set (i.e. 1 CPU)')

        return

    def _help_serial(self):
        return '-serial N'

    def _read_min_images(self):
        try:
            index = sys.argv.index('-min_images')
        except ValueError, e:
            return

        if index < 0:
            raise RuntimeError, 'negative index'

        self._understood.append(index)
        self._understood.append(index + 1)

        Flags.set_min_images(int(sys.argv[index + 1]))
        Debug.write('Min No. images / sweep set to %d' % \
                    Flags.get_min_images())

        return

    def _help_min_images(self):
        return '-min_images N'

    def _read_start_end(self):
        try:
            index = sys.argv.index('-start_end')
        except ValueError, e:
            return

        if index < 0:
            raise RuntimeError, 'negative index'

        if not '-image' in sys.argv:
            raise RuntimeError, 'do not use start_end without -image'

        self._understood.append(index)
        self._understood.append(index + 1)

        start, end = tuple(map(int, sys.argv[index + 1].split(',')))

        Flags.set_start_end(start, end)
        Debug.write('Start, end set to %d %d' % Flags.get_start_end())

        return

    def _help_start_end(self):
        return '-start_end start,end'

    def _read_xparallel(self):
        try:
            index = sys.argv.index('-xparallel')
        except ValueError, e:
            return

        if index < 0:
            raise RuntimeError, 'negative index'

        self._understood.append(index)
        self._understood.append(index + 1)

        Flags.set_xparallel(int(sys.argv[index + 1]))
        Debug.write('XParallel set to %d' % Flags.get_xparallel())

        return

    def _help_xparallel(self):
        return '-xparallel N'

    def _read_spacegroup(self):
        try:
            index = sys.argv.index('-spacegroup')
        except ValueError, e:
            return

        if index < 0:
            raise RuntimeError, 'negative index'

        self._understood.append(index)
        self._understood.append(index + 1)

        Flags.set_spacegroup(sys.argv[index + 1])
        Debug.write('Spacegroup set to %s' % sys.argv[index + 1])

        return

    def _help_spacegroup(self):
        return '-spacegroup P43212'

    def _read_resolution(self):
        try:
            index = sys.argv.index('-resolution')
        except ValueError, e:
            return

        if index < 0:
            raise RuntimeError, 'negative index'

        resolution = sys.argv[index + 1]
        if ',' in resolution:
            a, b = map(float, resolution.split(','))
            dmin = min(a, b)
            dmax = max(a, b)
        else:
            dmin = float(resolution)
            dmax = None

        self._understood.append(index)
        self._understood.append(index + 1)

        Flags.set_resolution_high(dmin)
        Flags.set_resolution_low(dmax)

        if dmax:
            Debug.write('Resolution set to %.3f %.3f' % (dmin, dmax))
        else:
            Debug.write('Resolution set to %.3f' % dmin)

        return

    def _help_resolution(self):
        return '-resolution high[,low]'

    def _read_z_min(self):
        try:
            index = sys.argv.index('-z_min')
        except ValueError, e:
            return

        if index < 0:
            raise RuntimeError, 'negative index'

        self._understood.append(index)
        self._understood.append(index + 1)

        Flags.set_z_min(float(sys.argv[index + 1]))
        Debug.write('Z min set to %f' % Flags.get_z_min())

        return

    def _help_z_min(self):
        return '-z_min N'

    def _read_scala_secondary(self):
        try:
            index = sys.argv.index('-scala_secondary')
        except ValueError, e:
            return

        if index < 0:
            raise RuntimeError, 'negative index'

        self._understood.append(index)
        self._understood.append(index + 1)

        Flags.set_scala_secondary(float(sys.argv[index + 1]))
        Debug.write('Scala secondary set to %f' % Flags.get_scala_secondary())

        return

    def _help_scala_secondary(self):
        return '-scala_secondary N'

    def _read_freer_file(self):
        try:
            index = sys.argv.index('-freer_file')
        except ValueError, e:
            return

        if index < 0:
            raise RuntimeError, 'negative index'

        Flags.set_freer_file(sys.argv[index + 1])

        self._understood.append(index)
        self._understood.append(index + 1)

        Debug.write('FreeR_flag column taken from %s' %
                    Flags.get_freer_file())

        # this should also be used as an indexing reference to make
        # sense...

        Flags.set_reference_reflection_file(sys.argv[index + 1])
        Debug.write('Reference reflection file: %s' %
                    Flags.get_reference_reflection_file())

        # and also the spacegroup copied out?! ok - this is done
        # "by magic" in the scaler.

        return

    def _help_freer_file(self):
        return '-freer_file my_freer_file.mtz'

    def _read_reference_reflection_file(self):
        try:
            index = sys.argv.index('-reference_reflection_file')
        except ValueError, e:
            return

        if index < 0:
            raise RuntimeError, 'negative index'

        Flags.set_reference_reflection_file(sys.argv[index + 1])

        self._understood.append(index)
        self._understood.append(index + 1)

        Debug.write('Reference reflection file: %s' %
                    Flags.get_reference_reflection_file())

        return

    def _help_reference_reflection_file(self):
        return '-reference_reflection_file my_reference_reflection_file.mtz'

    def _read_rejection_threshold(self):
        try:
            index = sys.argv.index('-rejection_threshold')
        except ValueError, e:
            return

        if index < 0:
            raise RuntimeError, 'negative index'

        self._understood.append(index)
        self._understood.append(index + 1)

        Flags.set_rejection_threshold(float(sys.argv[index + 1]))
        Debug.write('Rejection threshold set to %f' % \
                    Flags.get_rejection_threshold())

        return

    def _help_rejection_threshold(self):
        return '-rejection_threshold N'

    def _read_isigma(self):
        try:
            index = sys.argv.index('-isigma')
        except ValueError, e:
            return

        if index < 0:
            raise RuntimeError, 'negative index'

        self._understood.append(index)
        self._understood.append(index + 1)

        Flags.set_isigma(float(sys.argv[index + 1]))
        Debug.write('I/sigma limit set to %f' % \
                    Flags.get_isigma())

        return

    def _help_isigma(self):
        return '-isigma N'

    def _read_misigma(self):
        try:
            index = sys.argv.index('-misigma')
        except ValueError, e:
            return

        if index < 0:
            raise RuntimeError, 'negative index'

        self._understood.append(index)
        self._understood.append(index + 1)

        Flags.set_misigma(float(sys.argv[index + 1]))
        Debug.write('Merged I/sigma limit set to %f' % \
                    Flags.get_misigma())

        return

    def _help_misigma(self):
        return '-misigma N'

    def _read_completeness(self):
        try:
            index = sys.argv.index('-completeness')
        except ValueError, e:
            return

        if index < 0:
            raise RuntimeError, 'negative index'

        self._understood.append(index)
        self._understood.append(index + 1)

        Flags.set_completeness(float(sys.argv[index + 1]))
        Debug.write('Completeness limit set to %f' % \
                    Flags.get_completeness())

        return

    def _help_completeness(self):
        return '-completeness N'

    def _read_rmerge(self):
        try:
            index = sys.argv.index('-rmerge')
        except ValueError, e:
            return

        if index < 0:
            raise RuntimeError, 'negative index'

        self._understood.append(index)
        self._understood.append(index + 1)

        Flags.set_rmerge(float(sys.argv[index + 1]))
        Debug.write('Rmerge limit set to %f' % \
                    Flags.get_rmerge())

        return

    def _help_rmerge(self):
        return '-rmerge N'

    def _read_microcrystal(self):

        if '-microcrystal' in sys.argv:
            Flags.set_microcrystal()
            Debug.write('Microcrystal mode on')
            self._understood.append(sys.argv.index('-microcrystal'))

        return

    def _read_failover(self):

        if '-failover' in sys.argv:
            Flags.set_failover()
            Debug.write('Failover mode on')
            self._understood.append(sys.argv.index('-failover'))

        return

    def _read_blend(self):

        if '-blend' in sys.argv:
            Flags.set_blend()
            Debug.write('Blend mode on')
            self._understood.append(sys.argv.index('-blend'))

        return

    def _read_ispyb_xml_out(self):
        try:
            index = sys.argv.index('-ispyb_xml_out')
        except ValueError, e:
            self._ispyb_xml_out = None
            return

        if index < 0:
            raise RuntimeError, 'negative index'

        self._understood.append(index)
        self._understood.append(index + 1)
        Flags.set_ispyb_xml_out(sys.argv[index + 1])
        Debug.write('ISPyB XML output set to %s' % sys.argv[index + 1])

        return

    def _help_ispyb_xml_out(self):
        return '-ispyb_xml_out project.xml'

    def _read_hdr_in(self):
        try:
            index = sys.argv.index('-hdr_in')
        except ValueError, e:
            self._hdr_in = None
            return

        if index < 0:
            raise RuntimeError, 'negative index'

        self._understood.append(index)
        self._understood.append(index + 1)
        Flags.set_hdr_in(sys.argv[index + 1])

        return

    def _help_hdr_in(self):
        return '-hdr_in project.hdr'

    def _read_hdr_out(self):
        try:
            index = sys.argv.index('-hdr_out')
        except ValueError, e:
            self._hdr_out = None
            return

        if index < 0:
            raise RuntimeError, 'negative index'

        self._understood.append(index)
        self._understood.append(index + 1)
        Flags.set_hdr_out(sys.argv[index + 1])
        Debug.write('Output header file set to %s' % sys.argv[index + 1])

        return

    def _help_hdr_out(self):
        return '-hdr_out project.hdr'

    def get_template(self):
        return self._default_template

    def get_directory(self):
        return self._default_directory

    def get_image(self):
        return self._default_image

    def _read_trust_timestamps(self):

        if '-trust_timestamps' in sys.argv:
            Flags.set_trust_timestamps(True)
            Debug.write('Trust timestamps on')
            self._understood.append(sys.argv.index('-trust_timestamps'))

        return

    def _read_batch_scale(self):

        if '-batch_scale' in sys.argv:
            Flags.set_batch_scale(True)
            Debug.write('Batch scaling mode on')
            self._understood.append(sys.argv.index('-batch_scale'))

        return

    def _read_small_molecule(self):

        if '-small_molecule' in sys.argv:
            Flags.set_small_molecule(True)
            Debug.write('Small molecule selected')
            self._understood.append(sys.argv.index('-small_molecule'))

        return

    def _read_scale_model(self):
        try:
            index = sys.argv.index('-scale_model')
        except ValueError, e:
            return

        if index < 0:
            raise RuntimeError, 'negative index'

        self._understood.append(index)
        self._understood.append(index + 1)

        Flags.set_scale_model(sys.argv[index + 1])
        Debug.write('Scaling model set to: %s' % Flags.get_scale_model())

        return

    def _read_quick(self):

        if '-quick' in sys.argv:
            Flags.set_quick(True)
            Debug.write('Quick mode selected')
            self._understood.append(sys.argv.index('-quick'))
        return

    def _read_chef(self):

        if '-chef' in sys.argv:
            Flags.set_chef(True)
            self._understood.append(sys.argv.index('-chef'))
            Debug.write('Chef mode selected')

        if '-nochef' in sys.argv:
            Flags.set_chef(False)
            self._understood.append(sys.argv.index('-nochef'))
            Debug.write('Chef mode deselected')

        return

    def _read_reversephi(self):

        if '-reversephi' in sys.argv:
            Flags.set_reversephi(True)
            self._understood.append(sys.argv.index('-reversephi'))
            Debug.write('Reversephi mode selected')
        return

    def _read_no_lattice_test(self):

        if '-no_lattice_test' in sys.argv:
            Flags.set_no_lattice_test(True)
            self._understood.append(sys.argv.index('-no_lattice_test'))
            Debug.write('No lattice test mode selected')
        return

    def _read_no_relax(self):

        if '-no_relax' in sys.argv:
            Flags.set_relax(False)
            self._understood.append(sys.argv.index('-no_relax'))
            Debug.write('XDS relax about indexing selected')
        return

    def _read_no_profile(self):

        if '-no_profile' in sys.argv:
            Flags.set_profile(False)
            self._understood.append(sys.argv.index('-no_profile'))
            Debug.write('XDS profile fitting OFF')
        return

    def _read_zero_dose(self):

        if '-zero_dose' in sys.argv:
            Flags.set_zero_dose(True)
            self._understood.append(sys.argv.index('-zero_dose'))
            Debug.write('Zero-dose mode (XDS/XSCALE) selected')
        return

    def _read_norefine(self):

        if '-norefine' in sys.argv:
            Flags.set_refine(False)
            self._understood.append(sys.argv.index('-norefine'))
            # FIXME what does this do??? - switch off orientation refinement
            # in integration
        return

    def _read_noremove(self):

        if '-noremove' in sys.argv:
            self._understood.append(sys.argv.index('-noremove'))
            Flags.set_remove(False)
        return

    def _read_2dr(self):

        if '-2dr' in sys.argv or '-2d' in sys.argv:
            add_preference('integrater', 'mosflmr')
            add_preference('scaler', 'ccp4r')
            if '-2d' in sys.argv:
                self._understood.append(sys.argv.index('-2d'))
            if '-2dr' in sys.argv:
                self._understood.append(sys.argv.index('-2dr'))
            Debug.write('2DR pipeline selected')
        return

    def _read_2da(self):

        if '-2da' in sys.argv:
            add_preference('integrater', 'mosflmr')
            add_preference('scaler', 'ccp4a')
            if '-2da' in sys.argv:
                self._understood.append(sys.argv.index('-2da'))
            Debug.write('2DA pipeline selected')
        return

    def _read_2dia(self):

        if '-2dai' in sys.argv or '-2dia' in sys.argv:
            add_preference('indexer', 'mosflm')
            add_preference('integrater', 'mosflmr')
            add_preference('scaler', 'ccp4a')
            if '-2dai' in sys.argv:
                self._understood.append(sys.argv.index('-2dai'))
            if '-2dia' in sys.argv:
                self._understood.append(sys.argv.index('-2dia'))
            Debug.write('2DA pipeline selected')
        return

    def _read_2dir(self):

        if '-2dir' in sys.argv or '-2di' in sys.argv:
            add_preference('indexer', 'mosflm')
            add_preference('integrater', 'mosflmr')
            add_preference('scaler', 'ccp4r')
            if '-2di' in sys.argv:
                self._understood.append(sys.argv.index('-2di'))
            if '-2dir' in sys.argv:
                self._understood.append(sys.argv.index('-2dir'))
            Debug.write('2DR pipeline selected')
        return

    def _read_3dr(self):

        if '-3dr' in sys.argv or '-3d' in sys.argv:
            add_preference('integrater', 'xdsr')
            add_preference('scaler', 'xdsr')
            if '-3d' in sys.argv:
                self._understood.append(sys.argv.index('-3d'))
            if '-3dr' in sys.argv:
                self._understood.append(sys.argv.index('-3dr'))
            Debug.write('3DR pipeline selected')
        return

    def _read_3dir(self):

        if '-3dir' in sys.argv or '-3di' in sys.argv:
            add_preference('indexer', 'xds')
            add_preference('integrater', 'xdsr')
            add_preference('scaler', 'xdsr')
            if '-3di' in sys.argv:
                self._understood.append(sys.argv.index('-3di'))
            if '-3dir' in sys.argv:
                self._understood.append(sys.argv.index('-3dir'))
            Debug.write('3DR pipeline selected')
        return

    def _read_3diir(self):

        if '-3diir' in sys.argv or '-3dii' in sys.argv:
            add_preference('indexer', 'xdsii')
            add_preference('integrater', 'xdsr')
            add_preference('scaler', 'xdsr')
            if '-3dii' in sys.argv:
                self._understood.append(sys.argv.index('-3dii'))
            if '-3diir' in sys.argv:
                self._understood.append(sys.argv.index('-3diir'))
            Debug.write('3D II R pipeline (XDS IDXREF all images) selected')
        return

    def _read_3ds(self):

        if '-3ds' in sys.argv :
            add_preference('indexer', 'xdssum')
            add_preference('integrater', 'xdsr')
            add_preference('scaler', 'xdsa')
            if '-3ds' in sys.argv:
                self._understood.append(sys.argv.index('-3ds'))
            Debug.write('3DS pipeline selected')
        return

    def _read_3dar(self):

        if '-3dar' in sys.argv or '-3da' in sys.argv:
            add_preference('integrater', 'xdsr')
            add_preference('scaler', 'xdsa')
            if '-3da' in sys.argv:
                self._understood.append(sys.argv.index('-3da'))
            if '-3dar' in sys.argv:
                self._understood.append(sys.argv.index('-3dar'))
            Debug.write('3DAR pipeline selected')
        return

    def _read_3dair(self):

        if '-3dair' in sys.argv or '-3dai' in sys.argv:
            add_preference('indexer', 'xds')
            add_preference('integrater', 'xdsr')
            add_preference('scaler', 'xdsa')
            if '-3dai' in sys.argv:
                self._understood.append(sys.argv.index('-3dai'))
            if '-3dair' in sys.argv:
                self._understood.append(sys.argv.index('-3dair'))
            Debug.write('3DAR pipeline selected')
        return

    def _read_3daiir(self):

        if '-3daiir' in sys.argv or '-3daii' in sys.argv or \
               '-3diia' in sys.argv:
            add_preference('indexer', 'xdsii')
            add_preference('integrater', 'xdsr')
            add_preference('scaler', 'xdsa')
            if '-3daii' in sys.argv:
                self._understood.append(sys.argv.index('-3daii'))
            if '-3diia' in sys.argv:
                self._understood.append(sys.argv.index('-3diia'))
            if '-3daiir' in sys.argv:
                self._understood.append(sys.argv.index('-3daiir'))
            Debug.write('3DA II R pipeline (XDS IDXREF all images) selected')
        return

    def _read_debug(self):

        if '-debug' in sys.argv:
            # join the debug stream to the main output
            Debug.join(Chatter)
            self._understood.append(sys.argv.index('-debug'))
            Debug.write('Debugging output switched on')
        return

    def _read_interactive(self):

        if '-interactive' in sys.argv:
            Flags.set_interactive(True)
            self._understood.append(sys.argv.index('-interactive'))
            Debug.write('Interactive indexing ON')

        return

    def _read_ice(self):

        if '-ice' in sys.argv:
            Flags.set_ice(True)
            self._understood.append(sys.argv.index('-ice'))
            Debug.write('Ice ring exclusion ON')

        return

    def _read_egg(self):

        if '-egg' in sys.argv:
            self._understood.append(sys.argv.index('-egg'))
            Flags.set_egg(True)

        return

    def _read_uniform_sd(self):

        if '-no_uniform_sd' in sys.argv:
            Flags.set_uniform_sd(False)
            self._understood.append(sys.argv.index('-no_uniform_sd'))
            Debug.write('Uniform SD OFF')

        return

    def _read_migrate_data(self):

        if '-migrate_data' in sys.argv:
            Flags.set_migrate_data(True)
            self._understood.append(sys.argv.index('-migrate_data'))
            Debug.write('Data migration switched on')
        return

    def _read_cell(self):
        '''Read the cell constants from the command line.'''

        index = -1

        try:
            index = sys.argv.index('-cell')
        except ValueError, e:
            return

        if index < 0:
            raise RuntimeError, 'negative index'

        try:
            cell = sys.argv[index + 1].split(',')
        except IndexError, e:
            raise RuntimeError, \
                  '-cell correct use "-cell a,b,c,alpha,beta,gamma"'

        if len(cell) != 6:
            raise RuntimeError, \
                  '-cell correct use "-cell a,b,c,alpha,beta,gamma"'

        _cell = tuple(map(float, cell))

        Flags.set_cell(_cell)

        format = 6 * ' %7.2f'

        self._understood.append(index)
        self._understood.append(index + 1)

        Debug.write('Cell read from command line:' + \
                    format % _cell)

        return

    def _help_cell(self):
        '''Return a help string for the read cell method.'''
        return '-cell a,b,c,alpha,beta,gamma'

    def _read_free_fraction(self):
        try:
            index = sys.argv.index('-free_fraction')
        except ValueError, e:
            return

        if index < 0:
            raise RuntimeError, 'negative index'

        self._understood.append(index)
        self._understood.append(index + 1)

        Flags.set_free_fraction(float(sys.argv[index + 1]))
        Debug.write('Free fraction set to %f' % Flags.get_free_fraction())

        return

    def _help_free_fraction(self):
        return '-free_fraction N'

    def _read_free_total(self):
        try:
            index = sys.argv.index('-free_total')
        except ValueError, e:
            return

        if index < 0:
            raise RuntimeError, 'negative index'

        self._understood.append(index)
        self._understood.append(index + 1)

        Flags.set_free_total(int(sys.argv[index + 1]))
        Debug.write('Free total set to %f' % Flags.get_free_total())

        return

    def _help_free_total(self):
        return '-free_total N'

    def _read_mask(self):
        try:
            index = sys.argv.index('-mask')
        except ValueError, e:
            return

        if index < 0:
            raise RuntimeError, 'negative index'

        self._understood.append(index)
        self._understood.append(index + 1)
        Flags.set_mask(sys.argv[index + 1])

        return

    def get_mask(self):
        return self._mask

    def _help_mask(self):
        return '-mask mask.dat'

    def get_mask(self):
        return self._mask

    def _read_fixed_628(self):
        try:
            index = sys.argv.index('-fixed_628')
        except ValueError, e:
            return

        if index < 0:
            raise RuntimeError, 'negative index'

        self._understood.append(index)
        Flags.set_fixed_628()

        return

    def _help_fixed_628(self):
        return '-fixed_628'

    def _read_indexer(self):

        try:
            index = sys.argv.index('-indexer')
        except ValueError, e:
            return

        indexer = sys.argv[index + 1]
        add_preference('indexer', indexer)
        self._understood.append(index)
        self._understood.append(index + 1)
        return

    def _read_integrater(self):

        try:
            index = sys.argv.index('-integrater')
        except ValueError, e:
            return

        integrater = sys.argv[index + 1]
        add_preference('integrater', integrater)
        self._understood.append(index)
        self._understood.append(index + 1)
        return

    def _read_scaler(self):

        try:
            index = sys.argv.index('-scaler')
        except ValueError, e:
            return

        scaler = sys.argv[index + 1]
        add_preference('scaler', scaler)
        self._understood.append(index)
        self._understood.append(index + 1)
        return

    def _read_executables(self):
        try:
            index = sys.argv.index('-executable')
        except ValueError, e:
            return
        executable_string = sys.argv[index + 1]
        assert('=' in executable_string)
        executable, path = executable_string.split('=')
        Executables.add(executable, path)
        self._understood.append(index)
        self._understood.append(index + 1)
        return

CommandLine = _CommandLine()
CommandLine.setup()

if __name__ == '__main__':
    print CommandLine.get_beam()
    print CommandLine.get_xinfo()
