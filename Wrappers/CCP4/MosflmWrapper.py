#!/usr/bin/env python
# MosflmWrapper.py
#   Copyright (C) 2011 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# A real wrapper for the data processing program Mosflm, which will be wrapped
# with the following methods to provide functionality:
#
# index: autoindexing functionality (implemented)
# integrate: process a frame or a dataset (implemented)
#
# These will clearly have intermediate steps - however these will be handled
# within e.g. the MosflmIntegrater (i.e. properly!)

import os
import sys
import shutil
import math
import exceptions

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'
if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                                 'Python'))
if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Driver.DriverFactory import DriverFactory
from Decorators.DecoratorFactory import DecoratorFactory

# interfaces that this will present
from Schema.Interfaces.FrameProcessor import FrameProcessor

# output streams &c.
from Handlers.Streams import Chatter, Debug, Journal
from Handlers.Citations import Citations
from Handlers.Flags import Flags
from Handlers.Files import FileHandler

# odds and ends
from lib.bits import auto_logfiler, mean_sd, remove_outliers, meansd
from lib.SymmetryLib import lattice_to_spacegroup

from Experts.MatrixExpert import transmogrify_matrix, \
     get_reciprocal_space_primitive_matrix, reindex_sym_related
from Experts.ResolutionExperts import mosflm_mtz_to_list, \
     bin_o_tron, digest

def MosflmWrapper(DriverType = None):
    '''A factory for MosflmWrapper classes.'''

    DriverInstance = DriverFactory.Driver(DriverType)
    CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, 'ccp4')

    class _MosflmWrapper(CCP4DriverInstance.__class__,
                         FrameProcessor):
        '''A wrapper for Mosflm, using the CCP4-ified Driver, to wrap for the
        Indexer and Integrater functionality...'''

        def __init__(self):
            # generic things
            CCP4DriverInstance.__class__.__init__(self)

            # FIXME should this be "hard" coded as the ccp4 one?

            self.set_executable(os.path.join(
                os.environ['CCP4'], 'bin', 'ipmosflm'))

            FrameProcessor.__init__(self)

            return

        def integrate_single_images(self, indxr, images):
            '''Integrate a list of images.'''

            auto_logfiler(self)

            lattice = indxr.get_indexer_lattice()
            mosaic = indxr.get_indexer_mosaic()
            cell = indxr.get_indexer_cell()
            beam = indxr.get_indexer_beam()
            distance = indxr.get_indexer_distance()
            matrix = indxr.get_indexer_payload('mosflm_orientation_matrix')

            spacegroup_number = lattice_to_spacegroup(lattice)

            f = open(os.path.join(self.get_working_directory(),
                                  'xiaintegrate.mat'), 'w')

            for m in matrix:
                f.write(m)
            f.close()

            # then start the integration

            summary_file = 'summary_%s.log' % spacegroup_number

            self.add_command_line('SUMMARY')
            self.add_command_line(summary_file)

            self.start()

            self.input('template "%s"' % self.get_template())
            self.input('directory "%s"' % self.get_directory())

            mask = standard_mask(self._fp_header['detector_class'])

            for m in mask:
                self.input(m)

            self.input('matrix xiaintegrate.mat')

            self.input('beam %f %f' % beam)
            self.input('distance %f' % distance)
            self.input('symmetry %s' % spacegroup_number)
            self.input('mosaic %f' % mosaic)

            self.input('refinement include partials')

            if self.get_wavelength_prov() == 'user':
                self.input('wavelength %f' % self.get_wavelength())

            parameters = self.get_integrater_parameters('mosflm')
            for p in parameters.keys():
                self.input('%s %s' % (p, str(parameters[p])))

            # set up the integration
            self.input('postref fix all')
            self.input('postref maxresidual 5.0')

            detector_width = self._fp_header['size'][0] * \
                             self._fp_header['pixel'][0]
            detector_height = self._fp_header['size'][1] * \
                              self._fp_header['pixel'][1]

            lim_x = 0.5 * detector_width
            lim_y = 0.5 * detector_height

            self.input('limits xscan %f yscan %f' % (lim_x, lim_y))
            self.input('separation close')

            genfile = os.path.join(os.environ['CCP4_SCR'],
                                   '%d_mosflm.gen' % self.get_xpid())

            self.input('genfile %s' % genfile)

            for i in images:
                self.input('process %d %d')
                self.input('go')

            # that should be everything
            self.close_wait()

            # get the log file
            output = self.get_all_output()

            return

    return _MosflmWrapper()
