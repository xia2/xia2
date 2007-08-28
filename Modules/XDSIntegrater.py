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
from Experts.SymmetryExpert import r_to_rt

# interfaces that this must implement to be an integrater

from Schema.Interfaces.Integrater import Integrater
from Schema.Interfaces.FrameProcessor import FrameProcessor
from Schema.Exceptions.BadLatticeError import BadLatticeError

# indexing functionality if not already provided - even if it is
# we still need to reindex with XDS.

from Modules.XDSIndexer import XDSIndexer

# odds and sods that are needed

from lib.Guff import auto_logfiler
from Handlers.Streams import Chatter, Debug
from Handlers.Flags import Flags
from Handlers.Files import FileHandler

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
        integrate = _Integrate()
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


        # set a low resolution limit (which isn't really used...)
        # this should perhaps be done more intelligently from an
        # analysis of the spot list or something...?
        self.set_integrater_low_resolution(40.0)

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
            # set the indexer up as per the frameprocessor interface...
            # this would usually happen within the IndexerFactory.
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

        # copy the data across
        self._data_files = copy.deepcopy(
            self._intgr_indexer.get_indexer_payload('xds_files'))

        Debug.write('Files available at the end of XDS integrate prepare:')
        for f in self._data_files.keys():
            Debug.write('%s' % f)

        # copy the distance too...
        self.set_distance(self._intgr_indexer.get_indexer_distance())

        return

    def _integrate(self):
        '''Actually do the integration - in XDS terms this will mean running
        DEFPIX and INTEGRATE to measure all the reflections.'''

        first_image_in_wedge = self.get_image_name(self._intgr_wedge[0])

        defpix = self.Defpix()

        # pass in the correct data

        for file in ['X-CORRECTIONS.pck',
                     'Y-CORRECTIONS.pck',
                     'BKGINIT.pck',
                     'XPARM.XDS']:
            defpix.set_input_data_file(file, self._data_files[file])

        defpix.set_data_range(self._intgr_wedge[0],
                              self._intgr_wedge[1])

        if self.get_integrater_high_resolution() > 0.0:
            Debug.write('Setting resolution limit in DEFPIX to %.2f' % \
                        self.get_integrater_high_resolution())
            defpix.set_resolution_high(self.get_integrater_high_resolution())

        defpix.run()

        # and gather the result files
        for file in ['BKGPIX.pck',
                     'ABS.pck']:
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

        for file in ['X-CORRECTIONS.pck',
                     'Y-CORRECTIONS.pck',
                     'BLANK.pck',
                     'BKGPIX.pck',
                     'GAIN.pck']:
            integrate.set_input_data_file(file, self._data_files[file])

        # use the refined parameters for integration?

        fixed_2401 = True
       
        if self._data_files.has_key('GXPARM.XDS') and fixed_2401:
            Debug.write('Using globally refined parameters')
            integrate.set_input_data_file(
                'XPARM.XDS', self._data_files['GXPARM.XDS'])
            integrate.set_refined_xparm()
        else:
            integrate.set_input_data_file(
                'XPARM.XDS', self._data_files['XPARM.XDS'])

        integrate.run()

        # should the existence of these require that I rerun the
        # integration or can we assume that the application of a
        # sensible resolution limit will achieve this??

        self._integrate_parameters = integrate.get_updates()

        return

    def _integrate_finish(self):
        '''Finish off the integration by running correct.'''

        # first run the postrefinement etc with spacegroup P1
        # and the current unit cell - this will be used to
        # obtain a benchmark rmsd in pixels / phi and also
        # cell deviations (this is working towards spotting bad
        # indexing solutions) - only do this if we have no
        # reindex matrix... and no postrefined cell...

        p1_deviations = None

        if not self.get_integrater_reindex_matrix() and not self._intgr_cell:
            correct = self.Correct()

            correct.set_data_range(self._intgr_wedge[0],
                                   self._intgr_wedge[1])
        
            if self.get_polarization() > 0.0:
                correct.set_polarization(self.get_polarization())

            correct.set_spacegroup_number(1)
            correct.set_cell(
                self._intgr_indexer.get_indexer_cell())

            correct.run()

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
        
        if self.get_integrater_high_resolution() > 0.0:
            Debug.write('Using resolution limit: %.2f' % \
                        self.get_integrater_high_resolution())
            correct.set_resolution_high(self.get_integrater_high_resolution())

        if self.get_polarization() > 0.0:
            correct.set_polarization(self.get_polarization())

        if self.get_integrater_spacegroup_number():
            correct.set_spacegroup_number(
                self.get_integrater_spacegroup_number())
            if not self._intgr_cell:
                raise RuntimeError, 'no unit cell to recycle'
            correct.set_cell(self._intgr_cell)

        if self.get_integrater_reindex_matrix():
            correct.set_reindex_matrix(
                r_to_rt(self.get_integrater_reindex_matrix()))
        
        correct.run()

        if self.get_integrater_high_resolution() == 0.0:
            # get the "correct" resolution from ... correct
            
            Debug.write('Setting integrater resolution to %.2f' % \
                        correct.get_result('highest_resolution'))
            if not Flags.get_quick():
                self.set_integrater_high_resolution(
                    correct.get_result('highest_resolution'))
            else:
                # just record it for future reference
                self._intgr_reso_high = correct.get_result(
                    'highest_resolution')                                     

        # should get some interesting stuff from the XDS correct file
        # here, for instance the resolution range to use in integration
        # (which should be fed back if not fast) and so on...

        self._intgr_hklout = os.path.join(
            self.get_working_directory(),
            'XDS_ASCII.HKL')

        # look at the resolution limit...
        resolution = correct.get_result('resolution_estimate')

        if self.get_integrater_high_resolution():
            if resolution - self.get_integrater_high_resolution() < 0.075:
                
                # ignore this new resolution limit - this is similar to what
                # was done for the Mosflm implementation...

                Debug.write('Ignoring slight change in resolution limit')
                resolution = self.get_integrater_high_resolution()

        if resolution > self.get_integrater_high_resolution() and \
               not Flags.get_quick():
            self.set_integrater_high_resolution(resolution)
            Chatter.write('Set resolution limit: %5.2f' % resolution)
        elif Flags.get_quick():
            # just record it for future reference
            self._intgr_reso_high = resolution
            Chatter.write(
                'Set resolution limit: %5.2f (quick, so no rerun)' % \
                resolution)
            
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

        correct_deviations = (correct.get_result('rmsd_pixel'),
                              correct.get_result('rmsd_phi'))

        if p1_deviations:
            # compare and reject if both > 50% higher
            threshold = Flags.get_rejection_threshold()
            if correct_deviations[0] / p1_deviations[0] > threshold and \
                   correct_deviations[1] / p1_deviations[1] > threshold:
                Chatter.write(
                'Eliminating this indexing solution as postrefinement')
                Chatter.write(
                'deviations rather high relative to triclinic')
                raise BadLatticeError, \
                      'high relative deviations in postrefinement'

        if not Flags.get_quick():
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
                # unless we have added no new reflections
                if used:                
                    self.set_integrater_finish_done(False)

        else:
            Chatter.write(
                'Going quickly so not removing %d outlier reflections...' % \
                len(correct.get_remove()))

        return self._intgr_hklout
            
        

if __name__ == '__main__':

    # run a demo test

    if not os.environ.has_key('XIA2_ROOT'):
        raise RuntimeError, 'XIA2_ROOT not defined'

    xi = XDSIntegrater()

    directory = os.path.join('/data', 'graeme', 'insulin', 'demo')

    xi.setup_from_image(os.path.join(directory, 'insulin_1_001.img'))


    xi.integrate()
