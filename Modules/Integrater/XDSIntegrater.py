#!/usr/bin/env python
# XDSIntegrater.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 14th December 2006
#
# An implementation of the Integrater interface using XDS. This depends on the
# XDS wrappers to actually implement the functionality.
#
# This will "wrap" the XDS programs DEFPIX and INTEGRATE - CORRECT is
# considered to be a part of the scaling - see XDSScaler.py.
#
# 02/JAN/07 FIXME need to ensure that the indexing is repeated if necessary.

import os
import sys
import math
import copy
import shutil

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

# wrappers for programs that this needs

from Wrappers.XDS.XDSDefpix import XDSDefpix as _Defpix
from Wrappers.XDS.XDSIntegrate import XDSIntegrate as _Integrate
from Wrappers.XDS.XDSCorrect import XDSCorrect as _Correct

# helper functions

from Wrappers.XDS.XDS import beam_centre_mosflm_to_xds
from Wrappers.XDS.XDS import beam_centre_xds_to_mosflm
from Wrappers.XDS.XDS import xds_read_xparm
from Experts.SymmetryExpert import r_to_rt, rt_to_r
from Experts.SymmetryExpert import symop_to_mat, mat_to_symop

# interfaces that this must implement to be an integrater

from Schema.Interfaces.Integrater import Integrater
from Schema.Interfaces.FrameProcessor import FrameProcessor
from Schema.Exceptions.BadLatticeError import BadLatticeError

# indexing functionality if not already provided - even if it is
# we still need to reindex with XDS.

from Modules.Indexer.XDSIndexer import XDSIndexer

# odds and sods that are needed

from lib.bits import auto_logfiler
from Handlers.Streams import Chatter, Debug, Journal
from Handlers.Flags import Flags
from Handlers.Files import FileHandler

from Experts.SymmetryExpert import lattice_to_spacegroup_number

class XDSIntegrater(FrameProcessor,
                    Integrater):
    '''A class to implement the Integrater interface using *only* XDS
    programs.'''

    def __init__(self):

        # set up the inherited objects

        FrameProcessor.__init__(self)
        Integrater.__init__(self)

        # check that the programs exist - this will raise an exception if
        # they do not...

        integrate = _Integrate()

        # admin junk
        self._working_directory = os.getcwd()

        # place to store working data
        self._data_files = { }

        # internal parameters to pass around
        self._integrate_parameters = { }

        return

    # overload these methods as we don't want the resolution range
    # feeding back... aha - but we may want to assign them
    # from outside!

    def set_integrater_resolution(self, dmin, dmax, user = False):
        if user:
            Integrater.set_integrater_resolution(self, dmin, dmax, user)
        return

    def set_integrater_high_resolution(self, dmin, user = False):
        if user:
            Integrater.set_integrater_high_resolution(self, dmin, user)
        return

    def set_integrater_low_resolution(self, dmax, user = False):
        self._intgr_reso_low = dmax
        return

    # admin functions

    def set_working_directory(self, working_directory):
        self._working_directory = working_directory
        return

    def get_working_directory(self):
        return self._working_directory

    def _set_integrater_reindex_operator_callback(self):
        '''If a REMOVE.HKL file exists in the working
        directory, remove it...'''
        if os.path.exists(os.path.join(
            self.get_working_directory(),
            'REMOVE.HKL')):
            os.remove(os.path.join(
                self.get_working_directory(),
                'REMOVE.HKL'))
            Debug.write('Deleting REMOVE.HKL as reindex op set.')
        return

    # factory functions

    def Defpix(self):
        defpix = _Defpix()
        defpix.set_working_directory(self.get_working_directory())

        defpix.setup_from_image(self.get_image_name(
            self._intgr_wedge[0]))

        if self.get_distance():
            defpix.set_distance(self.get_distance())

        if self.get_wavelength():
            defpix.set_wavelength(self.get_wavelength())

        auto_logfiler(defpix, 'DEFPIX')

        return defpix

    def Integrate(self):
        from Handlers.Phil import PhilIndex
        integrate = _Integrate(params=PhilIndex.params.xds.integrate)
        integrate.set_working_directory(self.get_working_directory())

        integrate.setup_from_image(self.get_image_name(
            self._intgr_wedge[0]))

        if self.get_distance():
            integrate.set_distance(self.get_distance())

        if self.get_wavelength():
            integrate.set_wavelength(self.get_wavelength())

        auto_logfiler(integrate, 'INTEGRATE')

        return integrate

    def Correct(self):
        correct = _Correct()
        correct.set_working_directory(self.get_working_directory())

        correct.setup_from_image(self.get_image_name(
            self._intgr_wedge[0]))

        if self.get_distance():
            correct.set_distance(self.get_distance())

        if self.get_wavelength():
            correct.set_wavelength(self.get_wavelength())

        if self.get_integrater_ice():
            correct.set_ice(self.get_integrater_ice())

        if self.get_integrater_excluded_regions():
            correct.set_excluded_regions(self.get_integrater_excluded_regions())

        if self.get_integrater_anomalous():
            correct.set_anomalous(True)

        if self.get_integrater_low_resolution() > 0.0:
            Debug.write('Using low resolution limit: %.2f' % \
                        self.get_integrater_low_resolution())
            correct.set_resolution_high(0.0)
            correct.set_resolution_low(
                self.get_integrater_low_resolution())

        auto_logfiler(correct, 'CORRECT')

        return correct

    # now some real functions, which do useful things

    def _integrater_reset_callback(self):
        '''Delete all results on a reset.'''
        Debug.write('Deleting all stored results.')
        self._data_files = { }
        self._integrate_parameters = { }
        return

    def _integrate_prepare(self):
        '''Prepare for integration - in XDS terms this may mean rerunning
        IDXREF to get the XPARM etc. DEFPIX is considered part of the full
        integration as it is resolution dependent.'''

        # decide what images we are going to process, if not already
        # specified
        if not self._intgr_wedge:
            images = self.get_matching_images()
            self.set_integrater_wedge(min(images),
                                      max(images))

        Debug.write('XDS INTEGRATE PREPARE:')
        Debug.write('Wavelength: %.6f' % self.get_wavelength())
        Debug.write('Distance: %.2f' % self.get_distance())

        if not self._intgr_indexer:
            self.set_integrater_indexer(XDSIndexer())
            self.get_integrater_indexer().set_indexer_sweep(
                self.get_integrater_sweep())

            self._intgr_indexer.set_working_directory(
                self.get_working_directory())

            self._intgr_indexer.setup_from_image(self.get_image_name(
                self._intgr_wedge[0]))

            if self.get_frame_wedge():
                wedge = self.get_frame_wedge()
                Debug.write('Propogating wedge limit: %d %d' % wedge)
                self._intgr_indexer.set_frame_wedge(wedge[0],
                                                    wedge[1])

            # this needs to be set up from the contents of the
            # Integrater frame processer - wavelength &c.

            if self.get_beam():
                self._intgr_indexer.set_beam(self.get_beam())

            if self.get_distance():
                self._intgr_indexer.set_distance(self.get_distance())

            if self.get_wavelength():
                self._intgr_indexer.set_wavelength(
                    self.get_wavelength())

        # get the unit cell from this indexer to initiate processing
        # if it is new... and also copy out all of the information for
        # the XDS indexer if not...

        cell = self._intgr_indexer.get_indexer_cell()
        lattice = self._intgr_indexer.get_indexer_lattice()
        beam = self._intgr_indexer.get_indexer_beam()
        distance = self._intgr_indexer.get_indexer_distance()

        # check if the lattice was user assigned...
        user_assigned = self._intgr_indexer.get_indexer_user_input_lattice()

        # check that the indexer is an XDS indexer - if not then
        # create one...

        if not self._intgr_indexer.get_indexer_payload('xds_files'):
            Debug.write('Generating an XDS indexer')

            # note to self for the future - this set will reset the
            # integrater prepare done flag - this means that we will
            # go through this routine all over again. However this
            # is not a problem as all that will happen is that the
            # results will be re-got, no additional processing will
            # be performed...

            self.set_integrater_indexer(XDSIndexer())
            self.get_integrater_indexer().set_indexer_sweep(
                self.get_integrater_sweep())

            # set the indexer up as per the frameprocessor interface...
            # this would usually happen within the IndexerFactory.

            self.get_integrater_indexer().set_indexer_sweep_name(
                self.get_integrater_sweep_name())

            self.get_integrater_indexer().setup_from_image(
                self.get_image_name(
                self._intgr_wedge[0]))
            self.get_integrater_indexer().set_working_directory(
                self.get_working_directory())

            if self.get_frame_wedge():
                wedge = self.get_frame_wedge()
                Debug.write('Propogating wedge limit: %d %d' % wedge)
                self._intgr_indexer.set_frame_wedge(wedge[0],
                                                    wedge[1])

            if self.get_reversephi():
                Debug.write('Propogating reverse-phi...')
                self._intgr_indexer.set_reversephi()

            # now copy information from the old indexer to the new
            # one - lattice, cell, distance etc.

            # bug # 2434 - providing the correct target cell
            # may be screwing things up - perhaps it would
            # be best to allow XDS just to index with a free
            # cell but target lattice??
            if Flags.get_relax():
                Debug.write(
                    'Inputting target cell: %.2f %.2f %.2f %.2f %.2f %.2f' % \
                    cell)
                self._intgr_indexer.set_indexer_input_cell(cell)
            input_cell = cell

            # propogate the wavelength information...
            if self.get_wavelength():
                self._intgr_indexer.set_wavelength(
                    self.get_wavelength())

            self._intgr_indexer.set_indexer_input_lattice(lattice)

            if user_assigned:
                Debug.write('Assigning the user given lattice: %s' % \
                            lattice)
                self._intgr_indexer.set_indexer_user_input_lattice(True)

            self._intgr_indexer.set_distance(distance)
            self._intgr_indexer.set_beam(beam)

            # re-get the unit cell &c. and check that the indexing
            # worked correctly

            Debug.write('Rerunning indexing with XDS')

            cell = self._intgr_indexer.get_indexer_cell()
            lattice = self._intgr_indexer.get_indexer_lattice()

            # then in here check that the target unit cell corresponds
            # to the unit cell I wanted as input...? now for this I
            # should probably compute the unit cell volume rather
            # than comparing the cell axes as they may have been
            # switched around...

            # FIXME comparison needed

        # set a low resolution limit (which isn't really used...)
        # this should perhaps be done more intelligently from an
        # analysis of the spot list or something...?

        if not self.get_integrater_low_resolution():

            dmin = self._intgr_indexer.get_indexer_low_resolution()
            self.set_integrater_low_resolution(dmin)

            Debug.write('Low resolution set to: %s' % \
                        self.get_integrater_low_resolution())

        # copy the data across
        self._data_files = copy.deepcopy(
            self._intgr_indexer.get_indexer_payload('xds_files'))

        Debug.write('Files available at the end of XDS integrate prepare:')
        for f in self._data_files.keys():
            Debug.write('%s' % f)

        # copy the distance too...
        self.set_distance(self._intgr_indexer.get_indexer_distance())

        # delete things we should not know e.g. the postrefined cell from
        # CORRECT - c/f bug # 2695
        self._intgr_cell = None
        self._intgr_spacegroup_number = None

        return

    def _integrate(self):
        '''Actually do the integration - in XDS terms this will mean running
        DEFPIX and INTEGRATE to measure all the reflections.'''

        images_str = '%d to %d' % self._intgr_wedge
        cell_str = '%.2f %.2f %.2f %.2f %.2f %.2f' % \
                   self._intgr_indexer.get_indexer_cell()

        if len(self._fp_directory) <= 50:
            dirname = self._fp_directory
        else:
            dirname = '...%s' % self._fp_directory[-46:]

        Journal.block(
            'integrating', self._intgr_sweep_name, 'XDS',
            {'images':images_str,
             'cell':cell_str,
             'lattice':self.get_integrater_indexer().get_indexer_lattice(),
             'template':self._fp_template,
             'directory':dirname,
             'resolution':'%.2f' % self._intgr_reso_high})

        first_image_in_wedge = self.get_image_name(self._intgr_wedge[0])

        defpix = self.Defpix()

        # pass in the correct data

        for file in ['X-CORRECTIONS.cbf',
                     'Y-CORRECTIONS.cbf',
                     'BKGINIT.cbf',
                     'XPARM.XDS']:
            defpix.set_input_data_file(file, self._data_files[file])

        defpix.set_data_range(self._intgr_wedge[0],
                              self._intgr_wedge[1])

        if self.get_integrater_high_resolution() > 0.0 and \
               self.get_integrater_user_resolution():
            Debug.write('Setting resolution limit in DEFPIX to %.2f' % \
                        self.get_integrater_high_resolution())
            defpix.set_resolution_high(self.get_integrater_high_resolution())
            defpix.set_resolution_low(self.get_integrater_low_resolution())

        elif self.get_integrater_low_resolution():
            Debug.write('Setting low resolution limit in DEFPIX to %.2f' % \
                        self.get_integrater_low_resolution())
            defpix.set_resolution_high(0.0)
            defpix.set_resolution_low(self.get_integrater_low_resolution())

        defpix.run()

        # and gather the result files
        for file in ['BKGPIX.cbf',
                     'ABS.cbf']:
            self._data_files[file] = defpix.get_output_data_file(file)

        integrate = self.Integrate()

        if self._integrate_parameters:
            integrate.set_updates(self._integrate_parameters)

        # decide what images we are going to process, if not already
        # specified

        if not self._intgr_wedge:
            images = self.get_matching_images()
            self.set_integrater_wedge(min(images),
                                      max(images))

        first_image_in_wedge = self.get_image_name(self._intgr_wedge[0])

        integrate.set_data_range(self._intgr_wedge[0],
                                 self._intgr_wedge[1])

        for file in ['X-CORRECTIONS.cbf',
                     'Y-CORRECTIONS.cbf',
                     'BLANK.cbf',
                     'BKGPIX.cbf',
                     'GAIN.cbf']:
            integrate.set_input_data_file(file, self._data_files[file])

        if self._data_files.has_key('GXPARM.XDS'):
            Debug.write('Using globally refined parameters')
            integrate.set_input_data_file(
                'XPARM.XDS', self._data_files['GXPARM.XDS'])
            integrate.set_refined_xparm()
        else:
            integrate.set_input_data_file(
                'XPARM.XDS', self._data_files['XPARM.XDS'])

        integrate.run()

        # record the log file -

        pname, xname, dname = self.get_integrater_project_info()
        sweep = self.get_integrater_sweep_name()
        FileHandler.record_log_file('%s %s %s %s INTEGRATE' % \
                                    (pname, xname, dname, sweep),
                                    os.path.join(self.get_working_directory(),
                                                 'INTEGRATE.LP'))

        # and copy the first pass INTEGRATE.HKL...

        lattice = self._intgr_indexer.get_indexer_lattice()
        if not os.path.exists(os.path.join(
            self.get_working_directory(),
            'INTEGRATE-%s.HKL' % lattice)):
            here = self.get_working_directory()
            shutil.copyfile(os.path.join(here, 'INTEGRATE.HKL'),
                            os.path.join(here, 'INTEGRATE-%s.HKL' % lattice))

        # record INTEGRATE.HKL for e.g. BLEND.

        FileHandler.record_more_data_file(
            '%s %s %s %s INTEGRATE' % (pname, xname, dname, sweep),
            os.path.join(self.get_working_directory(), 'INTEGRATE.HKL'))

        # should the existence of these require that I rerun the
        # integration or can we assume that the application of a
        # sensible resolution limit will achieve this??

        self._integrate_parameters = integrate.get_updates()

        # record the mosaic spread &c.

        m_min, m_mean, m_max = integrate.get_mosaic()
        self.set_integrater_mosaic_min_mean_max(m_min, m_mean, m_max)

        Chatter.write('Mosaic spread: %.3f < %.3f < %.3f' % \
                      self.get_integrater_mosaic_min_mean_max())

        return os.path.join(self.get_working_directory(), 'INTEGRATE.HKL')

    def _integrate_finish(self):
        '''Finish off the integration by running correct.'''

        # first run the postrefinement etc with spacegroup P1
        # and the current unit cell - this will be used to
        # obtain a benchmark rmsd in pixels / phi and also
        # cell deviations (this is working towards spotting bad
        # indexing solutions) - only do this if we have no
        # reindex matrix... and no postrefined cell...

        p1_deviations = None

        # fix for bug # 3264 -
        # if we have not run integration with refined parameters, make it so...
        # erm? shouldn't this therefore return if this is the principle, or
        # set the flag after we have tested the lattice?

        if not self._data_files.has_key('GXPARM.XDS'):
            Debug.write(
                'Resetting integrater, to ensure refined orientation is used')
            self.set_integrater_done(False)

        if not self.get_integrater_reindex_matrix() and not self._intgr_cell \
               and not Flags.get_no_lattice_test() and \
               not self.get_integrater_sweep().get_user_lattice():
            correct = self.Correct()

            correct.set_data_range(self._intgr_wedge[0],
                                   self._intgr_wedge[1])

            if self.get_polarization() > 0.0:
                correct.set_polarization(self.get_polarization())

            # FIXME should this be using the correctly transformed
            # cell or are the results ok without it?!

            correct.set_spacegroup_number(1)
            correct.set_cell(
                self._intgr_indexer.get_indexer_cell())

            correct.run()

            # record the log file -

            pname, xname, dname = self.get_integrater_project_info()
            sweep = self.get_integrater_sweep_name()
            FileHandler.record_log_file('%s %s %s %s CORRECT' % \
                                        (pname, xname, dname, sweep),
                                        os.path.join(
                self.get_working_directory(),
                'CORRECT.LP'))

            FileHandler.record_more_data_file(
                '%s %s %s %s CORRECT' % (pname, xname, dname, sweep),
                os.path.join(self.get_working_directory(), 'XDS_ASCII.HKL'))

            cell = correct.get_result('cell')
            cell_esd = correct.get_result('cell_esd')

            Debug.write('Postrefinement in P1 results:')
            Debug.write('%7.3f %7.3f %7.3f %7.3f %7.3f %7.3f' % \
                        tuple(cell))
            Debug.write('%7.3f %7.3f %7.3f %7.3f %7.3f %7.3f' % \
                        tuple(cell_esd))
            Debug.write('Deviations: %.2f pixels %.2f degrees' % \
                        (correct.get_result('rmsd_pixel'),
                         correct.get_result('rmsd_phi')))

            p1_deviations = (correct.get_result('rmsd_pixel'),
                             correct.get_result('rmsd_phi'))

        # next run the postrefinement etc with the given
        # cell / lattice - this will be the assumed result...

        correct = self.Correct()

        correct.set_data_range(self._intgr_wedge[0],
                               self._intgr_wedge[1])

        if self.get_polarization() > 0.0:
            correct.set_polarization(self.get_polarization())

        # BUG # 2695 probably comes from here - need to check...
        # if the pointless interface comes back with a different
        # crystal setting then the unit cell stored in self._intgr_cell
        # needs to be set to None...

        if self.get_integrater_spacegroup_number():
            correct.set_spacegroup_number(
                self.get_integrater_spacegroup_number())
            if not self._intgr_cell:
                raise RuntimeError, 'no unit cell to recycle'
            correct.set_cell(self._intgr_cell)

        # BUG # 3113 - new version of XDS will try and figure the
        # best spacegroup out from the intensities (and get it wrong!)
        # unless we set the spacegroup and cell explicitly

        if not self.get_integrater_spacegroup_number():
            cell = self._intgr_indexer.get_indexer_cell()
            lattice = self._intgr_indexer.get_indexer_lattice()
            spacegroup_number = lattice_to_spacegroup_number(lattice)

            # this should not prevent the postrefinement from
            # working correctly, else what is above would not
            # work correctly (the postrefinement test)

            correct.set_spacegroup_number(spacegroup_number)
            correct.set_cell(cell)

            Debug.write('Setting spacegroup to: %d' % spacegroup_number)
            Debug.write('Setting cell to: %.2f %.2f %.2f %.2f %.2f %.2f' % \
                        cell)

        if self.get_integrater_reindex_matrix():

            # bug! if the lattice is not primitive the values in this
            # reindex matrix need to be multiplied by a constant which
            # depends on the Bravais lattice centering.

            lattice = self._intgr_indexer.get_indexer_lattice()

            matrix = r_to_rt(self.get_integrater_reindex_matrix())

            if lattice[1] == 'P':
                mult = 1
            elif lattice[1] == 'C' or lattice[1] == 'I':
                mult = 2
            elif lattice[1] == 'R':
                mult = 3
            elif lattice[1] == 'F':
                mult = 4
            else:
                raise RuntimeError, 'unknown multiplier for lattice %s' % \
                      lattice

            Debug.write('REIDX multiplier for lattice %s: %d' % \
                        (lattice, mult))

            mult_matrix = [mult * m for m in matrix]

            Debug.write('REIDX set to %d %d %d %d %d %d %d %d %d %d %d %d' % \
                        tuple(mult_matrix))
            correct.set_reindex_matrix(mult_matrix)

        correct.run()

        # erm. just to be sure
        if self.get_integrater_reindex_matrix() and \
               correct.get_reindex_used():
            raise RuntimeError, 'Reindex panic!'

        # get the reindex operation used, which may be useful if none was
        # set but XDS decided to apply one, e.g. #419.

        if not self.get_integrater_reindex_matrix() and \
               correct.get_reindex_used():
            # convert this reindex operation to h, k, l form: n.b. this
            # will involve dividing through by the lattice centring multiplier

            matrix = rt_to_r(correct.get_reindex_used())

            lattice = self._intgr_indexer.get_indexer_lattice()

            if lattice[1] == 'P':
                mult = 1.0
            elif lattice[1] == 'C' or lattice[1] == 'I':
                mult = 2.0
            elif lattice[1] == 'R':
                mult = 3.0
            elif lattice[1] == 'F':
                mult = 4.0

            matrix = [m / mult for m in matrix]

            reindex_op = mat_to_symop(matrix)

            # assign this to self: will this reset?! make for a leaky
            # abstraction and just assign this...

            # self.set_integrater_reindex_operator(reindex)

            self._intgr_reindex_operator = reindex_op


        # record the log file -

        pname, xname, dname = self.get_integrater_project_info()
        sweep = self.get_integrater_sweep_name()
        FileHandler.record_log_file('%s %s %s %s CORRECT' % \
                                    (pname, xname, dname, sweep),
                                    os.path.join(self.get_working_directory(),
                                                 'CORRECT.LP'))

        # should get some interesting stuff from the XDS correct file
        # here, for instance the resolution range to use in integration
        # (which should be fed back if not fast) and so on...

        intgr_hklout = os.path.join(self.get_working_directory(),
                                    'XDS_ASCII.HKL')

        # also record the batch range - needed for the analysis of the
        # radiation damage in chef...

        self._intgr_batches_out = (self._intgr_wedge[0],
                                   self._intgr_wedge[1])

        # FIXME perhaps I should also feedback the GXPARM file here??
        for file in ['GXPARM.XDS']:
            self._data_files[file] = correct.get_output_data_file(file)

        # record the postrefined cell parameters
        self._intgr_cell = correct.get_result('cell')
        self._intgr_n_ref = correct.get_result('n_ref')

        Debug.write('Postrefinement in "correct" spacegroup results:')
        Debug.write('%7.3f %7.3f %7.3f %7.3f %7.3f %7.3f' % \
                    tuple(correct.get_result('cell')))
        Debug.write('%7.3f %7.3f %7.3f %7.3f %7.3f %7.3f' % \
                    tuple(correct.get_result('cell_esd')))
        Debug.write('Deviations: %.2f pixels %.2f degrees' % \
                    (correct.get_result('rmsd_pixel'),
                     correct.get_result('rmsd_phi')))

        Debug.write('Error correction parameters: A=%.3f B=%.3f' % \
                    correct.get_result('sdcorrection'))

        # compute misorientation of axes

        xparm_dict = xds_read_xparm(os.path.join(self.get_working_directory(),
                                                 'GXPARM.XDS'))

        rotn = xparm_dict['axis']
        beam = xparm_dict['beam']

        dot = sum([rotn[j] * beam[j] for j in range(3)])
        r = math.sqrt(sum([rotn[j] * rotn[j] for j in range(3)]))
        b = math.sqrt(sum([beam[j] * beam[j] for j in range(3)]))

        rtod = 180.0 / math.pi

        angle = rtod * math.fabs(0.5 * math.pi - math.acos(dot / (r * b)))

        Debug.write('Axis misalignment %.2f degrees' % angle)

        correct_deviations = (correct.get_result('rmsd_pixel'),
                              correct.get_result('rmsd_phi'))

        if p1_deviations:
            # compare and reject if both > 50% higher - though adding a little
            # flexibility - 0.5 pixel / osc width slack.

            phi_width = self.get_header_item('phi_width')

            pixel = p1_deviations[0]
            phi = math.sqrt(0.05 * 0.05 + \
                            p1_deviations[1] * p1_deviations[1])

            threshold = Flags.get_rejection_threshold()

            Debug.write('RMSD ratio: %.2f' % (correct_deviations[0] / pixel))
            Debug.write('RMSPhi ratio: %.2f' % (correct_deviations[1] / phi))

            if correct_deviations[0] / pixel > threshold and \
                   correct_deviations[1] / phi > threshold:

                Chatter.write(
                'Eliminating this indexing solution as postrefinement')
                Chatter.write(
                'deviations rather high relative to triclinic')
                raise BadLatticeError, \
                      'high relative deviations in postrefinement'

        if not Flags.get_quick() and Flags.get_remove():
            # check for alien reflections and perhaps recycle - removing them
            if len(correct.get_remove()) > 0:

                correct_remove = correct.get_remove()
                current_remove = []
                final_remove = []

                # first ensure that there are no duplicate entries...
                if os.path.exists(os.path.join(
                    self.get_working_directory(),
                    'REMOVE.HKL')):
                    for line in open(os.path.join(
                        self.get_working_directory(),
                        'REMOVE.HKL'), 'r').readlines():
                        h, k, l = map(int, line.split()[:3])
                        z = float(line.split()[3])

                        if not (h, k, l, z) in current_remove:
                            current_remove.append((h, k, l, z))

                    for c in correct_remove:
                        if c in current_remove:
                            continue
                        final_remove.append(c)

                    Debug.write(
                        '%d alien reflections are already removed' % \
                        (len(correct_remove) - len(final_remove)))
                else:
                    # we want to remove all of the new dodgy reflections
                    final_remove = correct_remove

                remove_hkl = open(os.path.join(
                    self.get_working_directory(),
                    'REMOVE.HKL'), 'w')

                z_min = Flags.get_z_min()
                rejected = 0

                # write in the old reflections
                for remove in current_remove:
                    z = remove[3]
                    if z >= z_min:
                        remove_hkl.write('%d %d %d %f\n' % remove)
                    else:
                        rejected += 1
                Debug.write('Wrote %d old reflections to REMOVE.HKL' % \
                            (len(current_remove) - rejected))
                Debug.write('Rejected %d as z < %f' % \
                            (rejected, z_min))

                # and the new reflections
                rejected = 0
                used = 0
                for remove in final_remove:
                    z = remove[3]
                    if z >= z_min:
                        used += 1
                        remove_hkl.write('%d %d %d %f\n' % remove)
                    else:
                        rejected += 1
                Debug.write('Wrote %d new reflections to REMOVE.HKL' % \
                            (len(final_remove) - rejected))
                Debug.write('Rejected %d as z < %f' % \
                            (rejected, z_min))

                remove_hkl.close()

                # we want to rerun the finishing step so...
                # unless we have added no new reflections... or unless we
                # have not confirmed the point group (see SCI-398)

                if used and self.get_integrater_reindex_matrix():
                    self.set_integrater_finish_done(False)

        else:
            Debug.write(
                'Going quickly so not removing %d outlier reflections...' % \
                len(correct.get_remove()))

        return intgr_hklout

if __name__ == '__main__':

    # run a demo test

    if not os.environ.has_key('XIA2_ROOT'):
        raise RuntimeError, 'XIA2_ROOT not defined'

    xi = XDSIntegrater()

    directory = os.path.join('/data', 'graeme', 'insulin', 'demo')

    xi.setup_from_image(os.path.join(directory, 'insulin_1_001.img'))


    xi.integrate()
