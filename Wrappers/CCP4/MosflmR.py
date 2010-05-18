#!/usr/bin/env python
# Mosflm.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 23rd June 2006
# 
# A wrapper for the data processing program Mosflm, with the following
# methods to provide functionality:
# 
# index: autoindexing functionality (implemented)
# integrate: process a frame or a dataset (implemented)
#
# Internally this will also require cell refinement and so on, but this
# will be implicit - the cell refinement is a local requirement for
# mosflm only - though this will provide some useful functionality
# for diagnosing wrong indexing solutions.
#
# Input requirements:
# 
# At the minimum the indexing needs a beam centre, some images to index
# from and the template and directory where these images may be found.
# The indexing will return the most likely solution, or the one specified
# if this has been done. The interface should look like indexing with 
# labelit. However, a matrix file to index against could optionally be 
# supplied, to help with processing MAD data.
# 
# For integration, an appropriate matrix file, beam centre, lattice
# (spacegroup) and mosaic spread are needed, along with (optionally) a
# gain and definately images to process. A resolution limit may also be
# supplied.
# 
# The following are good example scripts of how this could work:
# 
# [autoindexing + cell refinement]
# 
# ipmosflm << eof
# beam 108.9 105.0
# directory /data/graeme/12287
# template 12287_1_E1_###.img
# autoindex dps image 1   ! can add refine after dps
# autoindex dps image 60  ! can add refine after dps
# mosaic estimate
# newmat index.mat
# go
# ! cell refinement stuff - needs more than 2 images
# newmat refined.mat
# postref multi segments 2
# process 1 3
# go
# process 58 60
# go
# eof
# 
# [integration]
# 
# ipmosflm hklout 12287_1_E1.mtz << eof
# resolution 1.65
# beam 108.9 105.0
# directory /data/graeme/12287
# template 12287_1_E1_###.img
# matrix refined.mat
# mosaic 0.51
# limits esclude   0.9 103.9 208.9 105.5
# limits exclude 103.5   4.4 106.0 209.0
# limits quadriateral 110.6 105.5 107.2 105.8 104.4 4.7 108.7 4.7
# gain 0.13
# separation close
# postref fix all
# process 1 60
# go
# eof
# 
# FIXED 16/AUG/06 the distortion & raster parameters decided on in the 
# cell refinement stages need to be recycled to use in integration. This is
# demonstrated by running an interactive (through the GUI) mosflm autoindex
# and refine job, then dumping the runit script. The important information is
# in the following records:
#
#  Final optimised raster parameters:   15   17   12    5    6
#    => RASTER keyword
#  Separation parameters updated to   0.71mm in X and  0.71mm in Y
#    => SEPARATION keyword
#    XCEN    YCEN  XTOFRA   XTOFD  YSCALE  TILT TWIST
#  108.97  105.31  0.9980  149.71  0.9984   -13   -46
#    => BEAM, DISTANCE, DISTORTION keywords (note that the numbers
#       are on the next line here)
#
# This should make the resulting integration more effective. The idea
# for this implementation is that the numbers end up in the "integrate
# set parameter" dictionary and are therefore recycled, in the same way
# that the GAIN currently works.
#
# FIXED 23/AUG/06 If the mosaic spread is refined to a negative number
#                 during the cell refinement, raise an exception asserting  
#                 that the lattice is wrong. This should eliminate that 
#                 lattice and all possibilities above it in symmetry from
#                 the list of possible lattices, and the next one down
#                 should be selected. This will require the "list of allowed
#                 lattices" stuff to be implemented, which is another
#                 FIXME all of it's own...
#
# FIXED 23/AUG/06 Another one - the raster parameters decided in indexing
#                 should be used in the cell refinement if the indexer was
#                 a mosflm and so is the refiner/integrater - which means
#                 that the indexer needs to be able to store integration
#                 parameters in the same way that the integrater does...
#                 Aha - this can go in the payload as something like
#                 "mosflm integration parameters" - excellent! Here are the
#                 complaints I am trying to correct:
#
# **** Information ****
# No RASTER keyword has been given.
# (Gives the starting parameters for the measurement box).
# Suitable parameters will be determined automatically.
#
#
# **** Information ****
# No SEPARATION keyword has been given.
# (Gives minimum spot separation before spots are flagged as overlapping.
# Suitable parameters will be determined automatically.
# 
# FIXED 23/AUG/06 Yet another one, though this may apply more to a higher
#                 level application than this module - there should be an
#                 "estimate resolution" during the integration, so that
#                 the final set contains good measurements, good profiles.
# 
# FIXME  4/SEP/06 Make sure that the SUMMARY files & friends are written
#                 to named files, to make sure they don't get overwritten.
#                 Also more careful naming of integrate.log &c. needed.
#  
# FIXME 08/SEP/06 Look at the DELX, DELY of profiles in the output, since 
#                 this can be an indicator of funky things going on in
#                 the integration. I seem to recall that TS00 complains
#                 about this, with the allegation of crystal slippage.
# 
# FIXME 11/SEP/06 Need to mask "dead" areas of the detector. E.g. a static
#                 mask from the detector class, plus some kind of mask 
#                 computed from the image [the latter is research!]
# 
# FIXME 11/SEP/06 Also want to check that the resolution of the data is
#                 better than (say) 3.5A, because below that Mosflm has 
#                 trouble refining the cell etc. Could add a resolution 
#                 estimate to the output of Indexer, which could either
#                 invoke labelit.stats_distl or grep the results from 
#                 the Mosflm output...
#
#                 Look for record "99% have resolution less than"...
# 
# FIXED 27/SEP/06 GAIN & detectors - all data processed for one crystal on
#                 one detector should have the same value for the GAIN - 
#                 this will mean that this has to be recycled. Add a framework
#                 to integrater to allow parameters to be exported, in
#                 the same way as they can be recycled via the integrater
#                 parameter framework. This is done - look at Integrater.
# 
# FIXME 19/OCT/06 it may be more reliable to do the indexing first then run a
#                 separate job to estimate the mosaic spread. Also important
#                 if this is to be used in DNA... this will need the matrix,
#                 resolution, raster parameters, refined beam.
# 
# FIXED 23/OCT/06 need to be able to do something useful when the cell
#                 refinement gives a "large" error in something... in
#                 particular be able to use more images for cell refinement
#                 and have another go! Done.
# 
# FIXME 28/NOV/06 need to rerun integration with the correct GAIN set before
#                 assessing I/sigma limits, since these will depend on the
#                 GAIN (however this could be weak - assess the benefit in
#                 repeating the integration.)
#
# FIXED 06/FEB/07 need to be able to track the autoindex solution number,
#                 so in cases where I want an exact solution I can fetch 
#                 it out from the list of solutions and FORCE mosflm
#                 to give me the right answer.
#
#                 This is going to have to work as follows. If there is
#                 a "horrible" exception, then the "correct" solution number
#                 needs to be obtained and set. The indexing done flag needs
#                 to be set as False, then the _index method should return.
#                 On the next pass the correct solution should be selected 
#                 and everything should be peachy. On this correct solution
#                 the recorded solution number should be reset to 0.
#
# FIXME 29/JUN/07 add functionality just to use this as a replacement for
#                 Diffdump in highly extreme circumstances - note well that
#                 this could be very slow...

import os
import sys
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

from Background.Background import Background
from Driver.DriverFactory import DriverFactory
from Decorators.DecoratorFactory import DecoratorFactory

# interfaces that this will present
from Schema.Interfaces.FrameProcessor import FrameProcessor
from Schema.Interfaces.Indexer import Indexer
from Schema.Interfaces.Integrater import Integrater

# output streams &c.

from Handlers.Streams import Chatter, Debug, Journal
from Handlers.Citations import Citations
from Handlers.Flags import Flags

# helpers

from MosflmHelpers import _happy_integrate_lp, \
     _parse_mosflm_integration_output, decide_integration_resolution_limit, \
     _parse_mosflm_index_output, standard_mask, \
     _get_indexing_solution_number, detector_class_to_mosflm, \
     _parse_summary_file

from Modules.GainEstimater import gain
from Handlers.Files import FileHandler

from lib.Guff import auto_logfiler, mean_sd
from lib.SymmetryLib import lattice_to_spacegroup

from Experts.MatrixExpert import transmogrify_matrix, \
     get_reciprocal_space_primitive_matrix, reindex_sym_related
from Experts.ResolutionExperts import mosflm_mtz_to_list, \
     bin_o_tron, digest
from Experts.MissetExpert import MosflmMissetExpert

# exceptions

from Schema.Exceptions.BadLatticeError import BadLatticeError
from Schema.Exceptions.NegativeMosaicError import NegativeMosaicError
from Schema.Exceptions.IndexingError import IndexingError
from Schema.Exceptions.IntegrationError import IntegrationError

# other classes which are necessary to implement the integrater
# interface (e.g. new version, with reindexing as the finish...)

from Wrappers.CCP4.Reindex import Reindex
from Wrappers.CCP4.Sortmtz import Sortmtz
from Wrappers.XIA.Diffdump import Diffdump
from Wrappers.XIA.Printpeaks import Printpeaks
from Modules.IceId import IceId

# cell refinement image helpers

from Modules.CellRefImageSelect import identify_perpendicular_axes
from Modules.MosflmCheckIndexerSolution import mosflm_check_indexer_solution

# jiffy functions for means, standard deviations and outliers

def meansd(values):
    mean = sum(values) / len(values)
    var = sum([(v - mean) * (v - mean) for v in values]) / len(values)
    return mean, math.sqrt(var)

def remove_outliers(values, limit):
    result = []
    outliers = []
    for j in range(len(values)):
        scratch = []
        for k in range(len(values)):
            if j != k:
                scratch.append(values[k])
        m, s = meansd(scratch)
        if math.fabs(values[j] - m) / s <= limit * s:
            result.append(values[j])
        else:
            outliers.append(values[j])

    return result, outliers

def MosflmR(DriverType = None):
    '''A factory for MosflmWrapper classes.'''

    DriverInstance = DriverFactory.Driver(DriverType)
    CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, 'ccp4')

    class MosflmRWrapper(CCP4DriverInstance.__class__,
                         FrameProcessor,
                         Indexer,
                         Integrater):
        '''A wrapper for Mosflm, using the CCP4-ified Driver.'''

        def __init__(self):
            # generic things
            CCP4DriverInstance.__class__.__init__(self)

            if Flags.get_automatch():
                self.set_executable(os.path.join(
                    os.environ['CCP4'], 'bin', 'ipmosflm.test'))

            else:
                self.set_executable(os.path.join(
                    os.environ['CCP4'], 'bin', 'ipmosflm'))
                
            FrameProcessor.__init__(self)
            Indexer.__init__(self)
            Integrater.__init__(self)

            # store the Driver instance used for this for use when working
            # in parallel - use with DriverFactory.Driver(DriverType)

            self._mosflm_driver_type = DriverType

            # local parameters used in autoindexing
            self._mosflm_autoindex_sol = 0
            self._mosflm_autoindex_thresh = None

            # local parameters used in cell refinement
            self._mosflm_cell_ref_images = None
            self._mosflm_cell_ref_resolution = None
            self._mosflm_cell_ref_double_mosaic = False

            # and the calculation of the missetting angles
            self._mosflm_misset_expert = None
            
            # local parameters used in integration
            self._mosflm_refine_profiles = True
            self._mosflm_postref_fix_mosaic = False
            self._mosflm_rerun_integration = False
            self._mosflm_hklout = ''

            self._mosflm_gain = None

            # things to support strategy calculation with BEST
            self._mosflm_best_parfile = None
            self._mosflm_best_datfile = None
            self._mosflm_best_hklfile = None

            return

        def diffdump(self, image):
            '''Run a diffdump style dump to check the parameters in the
            image header...'''

            pass

        def _mosflm_get_header(self, image):
            '''Return the header for this image.'''
            name = self.get_image_name(image)            
            dd = Diffdump()
            dd.set_image(name)
            return dd.readheader()

        def _estimate_gain(self):
            '''Estimate a GAIN appropriate for reducing this set.'''

            # pass this in from the frameprocessor interface - bug # 2333
            if self.get_gain():
                self._mosflm_gain = self.get_gain()

            if self._mosflm_gain:
                return

            images = self.get_matching_images()

            gains = []

            if len(images) < 10:
                # use all images
                for i in images:
                    gains.append(gain(self.get_image_name(i)))
            else:
                # use 5 from the start and 5 from the end
                for i in images[:5]:
                    gains.append(gain(self.get_image_name(i)))
                for i in images[-5:]:
                    gains.append(gain(self.get_image_name(i)))

            self._mosflm_gain = sum(gains) / len(gains)

            Chatter.write('Estimate gain of %5.2f' % self._mosflm_gain)
            
            return
        
        def _index_prepare(self):

            if self._indxr_images == []:
                self._index_select_images()
                
            return

        def _index_select_images(self):
            '''Select correct images based on image headers.'''

            if Flags.get_small_molecule():
                return self._index_select_images_small_molecule()

            phi_width = self.get_header_item('phi_width')
            images = self.get_matching_images()

            Debug.write('Selected image %s' % images[0])

            self.add_indexer_image_wedge(images[0])

            offset = images[0] - 1

            if offset + int(90.0 / phi_width) in images:
                Debug.write('Selected image %s' % (offset +
                                                   int(45.0 / phi_width)))
                Debug.write('Selected image %s' % (offset +
                                                   int(90.0 / phi_width)))
                self.add_indexer_image_wedge(offset + int(45.0 / phi_width))
                self.add_indexer_image_wedge(offset + int(90.0 / phi_width))
            else:
                middle = len(images) / 2
                if len(images) >= 3:
                    Debug.write('Selected image %s' % images[middle])
                    self.add_indexer_image_wedge(images[middle])
                Debug.write('Selected image %s' % images[-1])
                self.add_indexer_image_wedge(images[-1])

            return

        def _index_select_images_small_molecule(self):
            '''Select correct images based on image headers. This one is for
            when you have small molecule data so want more images.'''

            phi_width = self.get_header_item('phi_width')
            images = self.get_matching_images()

            Debug.write('Selected image %s' % images[0])

            self.add_indexer_image_wedge(images[0])

            offset = images[0] - 1

            # add an image every 15 degrees up to 90 degrees

            for j in range(6):

                image_number = offset + int(15 * (j + 1) / phi_width)

                if not image_number in images:
                    break

                Debug.write('Selected image %s' % image_number)
                self.add_indexer_image_wedge(image_number)

            return

        def _refine_select_images(self, mosaic):
            '''Select images for cell refinement based on image headers.'''

            cell_ref_images = []

            phi_width = self.get_header_item('phi_width')
            min_images = max(3, int(2 * mosaic / phi_width))

            if min_images > 9:
                min_images = 9
            
            images = self.get_matching_images()

            if len(images) < 3 * min_images:
                cell_ref_images.append((min(images), max(images)))
                return cell_ref_images

            cell_ref_images = []
            cell_ref_images.append((images[0], images[min_images - 1]))

            ideal_last = int(90.0 / phi_width) + min_images

            if ideal_last < len(images):
                ideal_middle = int(45.0 / phi_width) - min_images / 2
                cell_ref_images.append((images[ideal_middle - 1],
                                        images[ideal_middle - 2 + min_images]))
                cell_ref_images.append((images[ideal_last - min_images],
                                        images[ideal_last]))

            else:
                middle = int((max(images) + min(images) - min_images) / 2)
                cell_ref_images.append((middle - 1,
                                        middle - 2 + min_images))
                cell_ref_images.append((images[-min_images],
                                        images[-1]))
                

            return cell_ref_images
                            
        def _index(self):
            '''Implement the indexer interface.'''

            Citations.cite('mosflm')

            self.reset()

            _images = []
            for i in self._indxr_images:
                for j in i:
                    if not j in _images:
                        _images.append(j)
                    
            _images.sort()

            images_str = '%d' % _images[0]
            for i in _images[1:]:
                images_str += ', %d' % i

            cell_str = None
            if self._indxr_input_cell:
                cell_str = '%.2f %.2f %.2f %.2f %.2f %.2f' % \
                            self._indxr_input_cell

            if self._indxr_sweep_name:

                # then this is a proper autoindexing run - describe this
                # to the journal entry

                if len(self._fp_directory) <= 50:
                    dirname = self._fp_directory
                else:
                    dirname = '...%s' % self._fp_directory[-46:]

                Journal.block(
                    'autoindexing', self._indxr_sweep_name, 'mosflm',
                    {'images':images_str,
                     'target cell':self._indxr_input_cell,
                     'target lattice':self._indxr_input_lattice,
                     'template':self._fp_template,
                     'directory':dirname})
            
            task = 'Autoindex from images:'

            for i in _images:
                task += ' %s' % self.get_image_name(i)

            self.set_task(task)

            auto_logfiler(self)
            self.start()

            if self.get_reversephi():
                detector = detector_class_to_mosflm(
                    self.get_header_item('detector_class'))
                self.input('detector %s reversephi' % detector)

            self.input('template "%s"' % self.get_template())
            self.input('directory "%s"' % self.get_directory())
            self.input('newmat xiaindex.mat')

            if self.get_beam_prov() == 'user':
                self.input('beam %f %f' % self.get_beam())

            if self.get_wavelength_prov() == 'user':
                self.input('wavelength %f' % self.get_wavelength())

            if self.get_distance_prov() == 'user':
                self.input('distance %f' % self.get_distance())

            # FIXME need to be able to handle an input
            # unit cell here - should also be able to
            # handle writing in the crystal orientation (which
            # would be useful) but I may save that one for
            # later... c/f TS02/1VK8

            # N.B. need to make sure that this is a sensible answer
            # which is recycled later on!

            if self._indxr_input_cell:
                self.input('cell %f %f %f %f %f %f' % \
                           self._indxr_input_cell)

            if self._indxr_input_lattice != None:
                spacegroup_number = lattice_to_spacegroup(
                    self._indxr_input_lattice)
                self.input('symmetry %d' % spacegroup_number)

	    # FIXME 25/OCT/06 have found that a threshold of 10 works
            # better for TS01/LREM - need to make sure that this is 
            # generally applicable...

            # FIXME - gather thresholds for each image and use the minimum
            # value for all - unless I have a previous example here!

            # Added printpeaks check which should be interesting...

            if not self._mosflm_autoindex_thresh:

                # miniCBF is not currently supported - so use default
                # I/sigma of 20 for those...

                try:

                    min_peaks = 200

                    Debug.write('Aiming for at least %d spots...' % min_peaks)

                    thresholds = []
                    
                    for i in _images:
                        
                        p = Printpeaks()
                        p.set_image(self.get_image_name(i))
                        thresh = p.threshold(min_peaks)
                        
                        Debug.write('Autoindex threshold for image %d: %d' % \
                                    (i, thresh))

                        thresholds.append(thresh)
                
                    thresh = min(thresholds)
                    self._mosflm_autoindex_thresh = thresh

                except exceptions.Exception, e:
                    Debug.write('Error computing threshold: %s' % str(e))
                    Debug.write('Using default of 20.0')
                    thresh = 20.0
                
            else:
                thresh = self._mosflm_autoindex_thresh

            Debug.write('Using autoindex threshold: %d' % thresh)

            for i in _images:

                if self._mosflm_autoindex_sol:
                    self.input(
                        'autoindex dps refine image %d thresh %d solu %d' % \
                        (i, thresh, self._mosflm_autoindex_sol))
                else:
                    self.input(
                        'autoindex dps refine image %d thresh %d' % \
                        (i, thresh))

            # now forget this to prevent weird things happening later on
            if self._mosflm_autoindex_sol:
                self._mosflm_autoindex_sol = 0

            self.input('mosaic estimate')
            self.input('go')

            self.close_wait()

            output = self.get_all_output()

            for o in output:
                if 'Final cell (after refinement)' in o:
                    indxr_cell = tuple(map(float, o.split()[-6:]))

                    if min(list(indxr_cell)) < 10.0 and \
                       indxr_cell[2] / indxr_cell[0] > 6:

                        Debug.write(
                            'Unrealistic autoindexing solution: ' + 
                            '%.2f %.2f %.2f %.2f %.2f %.2f' % indxr_cell)

                        # tweak some parameters and try again...
                        self._mosflm_autoindex_thresh *= 1.5
                        self.set_indexer_done(False)
                        
                        return

            intgr_params = { }

            # look up other possible indexing solutions (not well - in
            # standard settings only!) This is moved earlier as it could
            # result in returning if Mosflm has selected the wrong
            # solution!

            try:
                self._indxr_other_lattice_cell = _parse_mosflm_index_output(
                    output)

                # Change 27/FEB/08 to support user assigned spacegroups
                if self._indxr_user_input_lattice:
                    lattice_to_spacegroup_dict = {
                        'aP':1, 'mP':3, 'mC':5, 'oP':16, 'oC':20, 'oF':22,
                        'oI':23, 'tP':75, 'tI':79, 'hP':143, 'hR':146,
                        'cP':195, 'cF':196, 'cI':197}
                    for k in self._indxr_other_lattice_cell.keys():
                        if lattice_to_spacegroup_dict[k] > \
                               lattice_to_spacegroup_dict[
                            self._indxr_input_lattice]:
                            del(self._indxr_other_lattice_cell[k])
                    

                # check that the selected unit cell matches - and if
                # not raise a "horrible" exception

                if self._indxr_input_cell:
                
                    for o in output:
                        if 'Final cell (after refinement)' in o:
                            indxr_cell = tuple(map(float, o.split()[-6:]))

                    for j in range(6):
                        if math.fabs(self._indxr_input_cell[j] -
                                     indxr_cell[j]) > 2.0:
                            Chatter.write(
                                'Mosflm autoindexing did not select ' +
                                'correct (target) unit cell')
                            raise RuntimeError, \
                                  'something horrible happened in indexing'

            except RuntimeError, e:
                # check if mosflm rejected a solution we have it
                if 'horribl' in str(e):
                    # ok it did - time to break out the big guns...
                    if not self._indxr_input_cell:
                        raise RuntimeError, \
                              'error in solution selection when not preset'

                    self._mosflm_autoindex_sol = _get_indexing_solution_number(
                        output,
                        self._indxr_input_cell,
                        self._indxr_input_lattice)

                    # set the fact that we are not done...
                    self.set_indexer_done(False)

                    # and return - hopefully this will restart everything
                    return
                else:
                    raise e

            for o in output:
                if 'Final cell (after refinement)' in o:
                    self._indxr_cell = tuple(map(float, o.split()[-6:]))
                if 'Beam coordinates of' in o:
                    self._indxr_refined_beam = tuple(map(float, o.split(
                        )[-2:]))

                # FIXED this may not be there if this is a repeat indexing!
                if 'Symmetry:' in o:
                    self._indxr_lattice = o.split(':')[1].split()[0]

                # so we have to resort to this instead...
                if 'Refining solution #' in o:
                    spagnum = int(o.split(')')[0].split()[-1])
                    lattice_to_spacegroup_dict = {'aP':1, 'mP':3, 'mC':5,
                                                  'oP':16, 'oC':20, 'oF':22,
                                                  'oI':23, 'tP':75, 'tI':79,
                                                  'hP':143, 'hR':146,
                                                  'cP':195, 'cF':196,
                                                  'cI':197}

                    spacegroup_to_lattice = { }
                    for k in lattice_to_spacegroup_dict.keys():
                        spacegroup_to_lattice[
                            lattice_to_spacegroup_dict[k]] = k
                    self._indxr_lattice = spacegroup_to_lattice[spagnum]

                    
                # in here I need to check if the mosaic spread estimation
                # has failed. If it has it is likely that the selected
                # lattice has too high symmetry, and the "next one down"
                # is needed

                if 'The mosaicity has been estimated' in o:
                    self._indxr_mosaic = float(o.split('>')[1].split()[0])

                # alternatively this could have failed - which happens
                # sometimes...

                if 'The mosaicity estimation has not worked for some' in o:
                    # this is a problem... in particular with the
                    # mosflm built on linux in CCP4 6.0.1...
                    # FIXME this should be a specific kind of
                    # exception e.g. an IndexError
                    raise IndexingError, 'mosaicity estimation failed'

                # or it may alternatively look like this...

                if 'The mosaicity has NOT been estimated' in o:
                    # then consider setting it do a default value...
                    # equal to the oscillation width (a good guess)
                    
                    phi_width = self.get_header_item('phi_width')

                    Chatter.write(
                        'Mosaic estimation failed, so guessing at %4.2f' % \
                        phi_width)

                    self._indxr_mosaic = phi_width

                # mosflm doesn't refine this in autoindexing...
                if 'Crystal to detector distance of' in o:
                    self._indxr_refined_distance = float(o.split(
                        )[5].replace('mm', ''))

                # but it does complain if it is different to the header
                # value - so just use the input value in this case...
                if 'Input crystal to detector distance' in o \
                   and 'does NOT agree with' in o:
                    self._indxr_refined_distance = self.get_distance()
                

                # record raster parameters and so on, useful for the
                # cell refinement etc - this will be added to a
                # payload dictionary of mosflm integration keywords
                # look for "measurement box parameters"

                if 'parameters have been set to' in o:
                    intgr_params['raster'] = map(
                        int, o.split()[-5:])

                if '(currently SEPARATION' in o:
                    intgr_params['separation'] = map(
                        float, o.replace(')', '').split()[-2:])

                # get the resolution estimate out...
                if '99% have resolution' in o:
                    self._indxr_resolution_estimate = float(
                        o.split()[-2])

            # FIXME this needs to be picked up by the integrater
            # interface which uses this Indexer, if it's a mosflm
            # implementation
            
            self._indxr_payload['mosflm_integration_parameters'] = intgr_params
                                                                 
            self._indxr_payload['mosflm_orientation_matrix'] = open(
                os.path.join(self.get_working_directory(),
                             'xiaindex.mat'), 'r').readlines()

            # also look at the images given in input to try to decide if
            # they are icy...

            ice = []
            
            for i in _images:

                icy = IceId()
                icy.set_image(self.get_image_name(i))
                icy.set_beam(self._indxr_refined_beam)
                
                ice.append(icy.search())

            if sum(ice) / len(ice) > 0.45:
                self._indxr_ice = 1

                Debug.write('Autoindexing images look icy: %.3f' % \
                            (sum(ice) / len(ice)))

            else:
                Debug.write('Autoindexing images look ok: %.3f' % \
                            (sum(ice) / len(ice)))
                

            return

        def _index_finish(self):
            '''Check that the autoindexing gave a convincing result, and
            if not (i.e. it gave a centred lattice where a primitive one
            would be correct) pick up the correct solution.'''

            status, lattice, matrix, cell = mosflm_check_indexer_solution(
                self)

            if status is None:

                # basis is primitive

                return

            if status is False:

                # basis is centred, and passes test

                return

            # ok need to update internals...

            self._indxr_lattice = lattice
            self._indxr_cell = cell

            Debug.write('Inserting solution: %s ' % lattice + 
                        '%6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % cell)

            self._indxr_replace(lattice, cell)

            self._indxr_payload['mosflm_orientation_matrix'] = matrix

            return

        # METHOD to help cell refinement - if the autoindexing has been done
        # with another program, it could be helpful to run autoindexing
        # with Mosflm (not to keep the results, mind) to get these parameters
        # out - for example raster parameters etc.

        def _mosflm_generate_raster(self, _images):
            '''Get out the parameters from autoindexing without using the
            result - this is probably ok as it is quite quick ;o).'''

            # reset the log file tracking and whatnot

            self.reset()

            # have to get the images to use into here somehow - work through
            # using the first image from each cell refinement wedge? that
            # would probably hit the spot...
                    
            auto_logfiler(self)

            Debug.write('Running mosflm to generate RASTER, SEPARATION')
            
            self.start()

            if self.get_reversephi():
                detector = detector_class_to_mosflm(
                    self.get_header_item('detector_class'))
                self.input('detector %s reversephi' % detector)

            self.input('template "%s"' % self.get_template())
            self.input('directory "%s"' % self.get_directory())
            self.input('newmat xiaindex.mat')

            # why would I not want to assign the right beam centre?

            if self.get_beam_prov() == 'user' or True:
                self.input('beam %f %f' % self.get_beam())

            if self.get_wavelength_prov() == 'user':
                self.input('wavelength %f' % self.get_wavelength())

            if self.get_distance_prov() == 'user':
                self.input('distance %f' % self.get_distance())

            # Added printpeaks check which should be interesting...

            if not self._mosflm_autoindex_thresh:

                # miniCBF is not currently supported - so use default
                # I/sigma of 20 for those...

                try:

                    min_peaks = 200
                    Debug.write('Aiming for at least %d spots...' % min_peaks)
                    thresholds = []
                    
                    for i in _images:
                        
                        p = Printpeaks()
                        p.set_image(self.get_image_name(i))
                        thresh = p.threshold(min_peaks)
                        
                        Debug.write('Autoindex threshold for image %d: %d' % \
                                    (i, thresh))

                        thresholds.append(thresh)
                
                    thresh = min(thresholds)
                    self._mosflm_autoindex_thresh = thresh

                except exceptions.Exception, e:
                    Debug.write('Error computing threshold: %s' % str(e))
                    Debug.write('Using default of 20.0')
                    thresh = 20.0
                
            else:
                thresh = self._mosflm_autoindex_thresh

            Debug.write('Using autoindex threshold: %d' % thresh)

            for i in _images:

                self.input(
                    'autoindex dps refine image %d thresh %d' % \
                    (i, thresh))

            self.input('mosaic estimate')
            self.input('go')

            self.close_wait()

            intgr_params = { }

            output = self.get_all_output()

            for o in output:

                # record raster parameters and so on, useful for the
                # cell refinement etc - this will be added to a
                # payload dictionary of mosflm integration keywords
                # look for "measurement box parameters"

                if 'parameters have been set to' in o:
                    intgr_params['raster'] = map(
                        int, o.split()[-5:])

                if '(currently SEPARATION' in o:
                    intgr_params['separation'] = map(
                        float, o.replace(')', '').split()[-2:])
                    
            return intgr_params

        def _integrate_prepare(self):
            '''Prepare for integration - note that if there is a reason
            why this is needed to be run again, set self._intgr_prepare_done
            as False.'''

            self.digest_template()

            if not self._mosflm_gain and self.get_gain():
                self._mosflm_gain = self.get_gain()

            if not self._mosflm_cell_ref_images:
                indxr = self.get_integrater_indexer()
                lattice = indxr.get_indexer_lattice()
                mosaic = indxr.get_indexer_mosaic()
                spacegroup_number = lattice_to_spacegroup(lattice)

                # FIXME is this ignored now?
                if spacegroup_number >= 75:
                    num_wedges = 1
                else:
                    num_wedges = 2

                self._mosflm_cell_ref_images = self._refine_select_images(
                    mosaic)

            indxr = self.get_integrater_indexer()

            images_str = '%d to %d' % self._mosflm_cell_ref_images[0]
            for i in self._mosflm_cell_ref_images[1:]:
                images_str += ', %d to %d' % i

            cell_str = '%.2f %.2f %.2f %.2f %.2f %.2f' % \
                       indxr.get_indexer_cell()

            if len(self._fp_directory) <= 50:
                dirname = self._fp_directory
            else:
                dirname = '...%s' % self._fp_directory[-46:]

            Journal.block('cell refining', self._intgr_sweep_name, 'mosflm',
                          {'images':images_str,
                           'start cell':cell_str,
                           'target lattice':indxr.get_indexer_lattice(),
                           'template':self._fp_template,
                           'directory':dirname})

            # in here, check to see if we have the raster parameters and
            # separation from indexing - if we used a different indexer
            # we may not, so if this is the case call a function to generate
            # them...

            if not indxr.get_indexer_payload(
                'mosflm_integration_parameters'):

                # generate a list of first images

                images = []
                for cri in self._mosflm_cell_ref_images:
                    images.append(cri[0])

                images.sort()

                integration_params = self._mosflm_generate_raster(images)

                # copy them over to where they are needed

                if integration_params.has_key('separation'):
                    self.set_integrater_parameter(
                        'mosflm', 'separation',
                        '%f %f' % tuple(integration_params['separation']))
                if integration_params.has_key('raster'):
                    self.set_integrater_parameter(
                        'mosflm', 'raster',
                        '%d %d %d %d %d' % tuple(integration_params['raster']))
            
            # next test the cell refinement with the correct lattice
            # and P1 and see how the numbers stack up...

            # FIXME in here 19/JUNE/08 - if I get a negative mosaic spread
            # in here it may be worth doubling the estimated mosaic spread
            # and having another go. If it fails a second time, then
            # let the exception through... - this should now raise a
            # NegativeMosaicError not a BadLatticeError

            # copy the cell refinement resolution in...

            self._mosflm_cell_ref_resolution = indxr.get_indexer_resolution()

            Debug.write(
                'Using resolution limit of %.2f for cell refinement' % \
                self._mosflm_cell_ref_resolution)

            # now trap NegativeMosaicError exception - once!

            try:

                # now reading the background residual values as well - if these
                # are > 10 it would indicate that the images are blank (assert)
                # so ignore from the analyis / comparison

                self.reset()
                auto_logfiler(self)
                rms_deviations_p1, br_p1 = self._mosflm_test_refine_cell('aP')
                self.reset()
                auto_logfiler(self)
                rms_deviations, br = self._mosflm_refine_cell()

            except NegativeMosaicError, nme:
                # need to handle cases where the mosaic spread refines to
                # a negative value when the lattice is right - this could
                # be caused by the starting value being too small so
                # try doubling - if this fails, reject lattice as duff...

                if self._mosflm_cell_ref_double_mosaic:

                    # reset flag; half mosaic; raise BadLatticeError

                    Debug.write('Mosaic negative even x2 -> BadLattice')
                    
                    self._mosflm_cell_ref_double_mosaic = False
                    raise BadLatticeError, 'negative mosaic spread'

                else:

                    # set flag, double mosaic, return to try again

                    Debug.write('Mosaic negative -> try x2')

                    self._mosflm_cell_ref_double_mosaic = True
                    
                    self.set_integrater_prepare_done(False)

                    return
            
            if not self.get_integrater_prepare_done():
                # cell refinement failed so no point getting the
                # results of refinement in P1... now this is
                # ignored as it is important we refine the cell
                # in P1 first...
                return

            # run the cell refinement again with the refined parameters
            # in the correct lattice as this will give a fair comparison
            # with the P1 refinement (see bug # 2539) - would also be
            # interesting to see how much better these are...
            # no longer need these...

            # self.reset()
            # auto_logfiler(self)
            # rms_deviations = self._mosflm_test_refine_cell(
            # self.get_integrater_indexer().get_indexer_lattice())
            
            images = []
            for cri in self._mosflm_cell_ref_images:
                for j in range(cri[0], cri[1] + 1):
                    images.append(j)
                    
            if rms_deviations and rms_deviations_p1:
                cycles = []
                j = 1
                while rms_deviations.has_key(j) and \
                      rms_deviations_p1.has_key(j):
                    cycles.append(j)
                    j += 1
                Debug.write('Cell refinement comparison:')
                Debug.write('Image   correct   triclinic')
                ratio = 0.0

                ratios = []

                for c in cycles:
                    Debug.write('Cycle %d' % c)
                    for j, image in enumerate(images):

                        background_residual = max(br_p1[c][image],
                                                  br[c][image])

                        if background_residual > 10:
                            Debug.write('. %4d   %.2f     %.2f (ignored)' % \
                                        (images[j], rms_deviations[c][j],
                                         rms_deviations_p1[c][j]))
                            continue

                        Debug.write('. %4d   %.2f     %.2f' % \
                                    (images[j], rms_deviations[c][j],
                                     rms_deviations_p1[c][j]))
                        
                        ratio += rms_deviations[c][j] / rms_deviations_p1[c][j]
                        ratios.append(
                            (rms_deviations[c][j] / rms_deviations_p1[c][j]))

                # fixme in here only run this if lattice != aP

                if False and self.get_integrater_indexer(
                    ).get_indexer_lattice() != 'aP':
                
                    good, bad = remove_outliers(ratios, 6)
                    m, s = meansd(good)

                    bs = ''
                    for b in bad:
                        bs += '%.3f ' % b
                        
                    Debug.write('%d outlier ratios: %s' % (len(bad), bs))
                    Debug.write('Of the good: %.3f +- %.3f' % (m, s))

                Debug.write('Average ratio: %.2f' % \
                            (ratio / len(ratios)))

                if (ratio / (max(cycles) * len(images))) > \
                       Flags.get_rejection_threshold():
                    raise BadLatticeError, 'incorrect lattice constraints'

            else:
                Debug.write('Cell refinement in P1 failed...')

            # also look for the images we want to integrate... since this
            # is part of the preparation and was causing fun with
            # bug # 2040 - going quickly! this resets the integration done
            # flag...
            
            cell_str = '%.2f %.2f %.2f %.2f %.2f %.2f' % \
                       self._intgr_cell

            Journal.entry({'refined cell':cell_str})

            if not self._intgr_wedge:
                images = self.get_matching_images()
                self.set_integrater_wedge(min(images),
                                          max(images))
            

            return

        def _integrate(self):
            '''Implement the integrater interface.'''

            # cite the program
            Citations.cite('mosflm')

            # FIXME in here I want to be able to work "fast" or "slow"
            # if fast, ignore cell refinement (i.e. to get the pointless
            # output quickly.) 30/OCT/06 decide that this is is not
            # appropriate for xia2.

            # this means that the integration must be able to know
            # what "state" it is being run from... this is perhaps best
            # achieved by repopulating the indexing results with the output
            # of the cell refinement, which have the same prototype.

            # fixme should this have
            # 
            # self._determine_pointgroup()
            # 
            # first???
            #
            # or is that an outside responsibility? yes.

            # FIXME 20/OCT/06 this needs to be able to check if (1) the
            #                 cell refinement has already been performed
            #                 for the correct lattice and (2) if there
            #                 if a good reason for rerunning the integration.
            #                 See changes to Integrater.py in Schema /
            #                 Interfaces as to why this is suddenly
            #                 important (in a nutshell, this will handle
            #                 all of the necessary rerunning in a while-loop.)

            # by default we don't want to rerun, or we could be here forever
            # (and that did happen! :o( )

            images_str = '%d to %d' % self._intgr_wedge
            cell_str = '%.2f %.2f %.2f %.2f %.2f %.2f' % self._intgr_cell

            if len(self._fp_directory) <= 50:
                dirname = self._fp_directory
            else:
                dirname = '...%s' % self._fp_directory[-46:]

            Journal.block(
                'integrating', self._intgr_sweep_name, 'mosflm',
                {'images':images_str,
                 'cell':cell_str,
                 'lattice':self.get_integrater_indexer().get_indexer_lattice(),
                 'template':self._fp_template,
                 'directory':dirname,
                 'resolution':'%.2f' % self._intgr_reso_high})

            self._mosflm_rerun_integration = False

            wd = self.get_working_directory()

            try:
 
                self.reset()
                auto_logfiler(self)

                if self.get_integrater_sweep_name():
                    pname, xname, dname = self.get_integrater_project_info()
                    FileHandler.record_log_file(
                        '%s %s %s %s mosflm integrate' % \
                        (self.get_integrater_sweep_name(),
                         pname, xname, dname),
                        self.get_log_file())
                
                if Flags.get_parallel() > 1:
                    Debug.write('Parallel integration: %d jobs' %
                                Flags.get_parallel())
                    self._intgr_hklout = self._mosflm_parallel_integrate()
                else:
                    self._intgr_hklout = self._mosflm_integrate()
                self._mosflm_hklout = self._intgr_hklout

            except IntegrationError, e:
                if 'negative mosaic spread' in str(e):
                    if self._mosflm_postref_fix_mosaic:
                        Chatter.write(
                            'Negative mosaic spread - stopping integration')
                        raise BadLatticeError, 'negative mosaic spread'
                        
                    Chatter.write(
                        'Negative mosaic spread - rerunning integration')
                    self.set_integrater_done(False)
                    self._mosflm_postref_fix_mosaic = True

            if self._mosflm_rerun_integration and not Flags.get_quick():
                # make sure that this is run again...
                Chatter.write('Need to rerun the integration...')
                self.set_integrater_done(False)

            return self._intgr_hklout

        def _integrate_finish(self):
            '''Finish the integration - if necessary performing reindexing
            based on the pointgroup and the reindexing operator.'''

            # Check if we need to perform any reindexing... this will
            # be the case if we have no reindexing operator and we
            # are also in the correct pointgroup. Alternatively we may
            # not have a spacegroup set as yet...

            if self._intgr_reindex_operator is None and \
               self._intgr_spacegroup_number == lattice_to_spacegroup(
                self.get_integrater_indexer().get_indexer_lattice()):
                return self._mosflm_hklout

            if self._intgr_reindex_operator is None and \
               self._intgr_spacegroup_number == 0:
                return self._mosflm_hklout

            Debug.write('Reindexing to spacegroup %d (%s)' % \
                        (self._intgr_spacegroup_number,
                         self._intgr_reindex_operator))

            hklin = self._mosflm_hklout
            reindex = Reindex()
            reindex.set_working_directory(self.get_working_directory())
            auto_logfiler(reindex)

            reindex.set_operator(self._intgr_reindex_operator)

            if self._intgr_spacegroup_number:
                reindex.set_spacegroup(self._intgr_spacegroup_number)

            hklout = '%s_reindex.mtz' % hklin[:-4]

            reindex.set_hklin(hklin)
            reindex.set_hklout(hklout)

            reindex.reindex()

            self._intgr_hklout = hklout
            return hklout

        def _mosflm_test_refine_cell(self, test_lattice):
            '''Test performing cell refinement in with a different
            lattice to the one which was selected by the autoindex
            procedure.'''

            # this version will not actually *change* anything in the class.

            # note well that this will need the unit cell to be
            # transformed from a centred to a primitive lattice, perhaps.
            # yes that is definately the case - the matrix will also
            # need to be transformed :o( this is fine, see below.

            # assert that this is called after the initial call to
            # cell refinement in the correct PG so a lot of this can
            # be ignored...

            indxr = self.get_integrater_indexer()

            lattice = indxr.get_indexer_lattice()
            mosaic = indxr.get_indexer_mosaic()
            beam = indxr.get_indexer_beam()
            distance = indxr.get_indexer_distance()
            matrix = indxr.get_indexer_payload('mosflm_orientation_matrix')

            # bug # 3174 - if mosaic is very small (here defined to be 
            # 0.25 x osc_width) then set to this minimum value.

            if mosaic < 0.25 * self.get_header_item('phi_width'):
                mosaic = 0.25 * self.get_header_item('phi_width')

            input_matrix = ''
            for m in matrix:
                input_matrix += '%s\n' % m

            new_matrix = transmogrify_matrix(lattice, input_matrix,
                                             test_lattice,
                                             self.get_wavelength(),
                                             self.get_working_directory())

            spacegroup_number = lattice_to_spacegroup(test_lattice)

            if not self._mosflm_cell_ref_images:
                raise RuntimeError, 'wedges must be assigned already'

            open(os.path.join(self.get_working_directory(),
                              'test-xiaindex-%s.mat' % lattice),
                 'w').write(new_matrix)

            self.start()

            if self._mosflm_gain:
                self.input('gain %5.2f' % self._mosflm_gain)

            if self.get_reversephi():
                detector = detector_class_to_mosflm(
                    self.get_header_item('detector_class'))
                self.input('detector %s reversephi' % detector)

            self.input('template "%s"' % self.get_template())
            self.input('directory "%s"' % self.get_directory())

            self.input('matrix test-xiaindex-%s.mat' % lattice)
            self.input('newmat test-xiarefine.mat')

            self.input('beam %f %f' % beam)
            self.input('distance %f' % distance)

            self.input('symmetry %s' % spacegroup_number)

            # FIXME 18/JUN/08 - it may help to have an overestimate
            # of the mosaic spread in here as it *may* refine down
            # better than up... - this is not a good idea as it may
            # also not refine at all! - 12972 # integration failed

            # Bug # 3103
            if self._mosflm_cell_ref_double_mosaic:
                self.input('mosaic %f' % (2.0 * mosaic))
            else:
                self.input('mosaic %f' % mosaic)

            # if set, use the resolution for cell refinement - see
            # bug # 2078...
            
            if self._mosflm_cell_ref_resolution and not Flags.get_tricky():
                self.input('resolution %f' % \
                           self._mosflm_cell_ref_resolution)

            if self._mosflm_postref_fix_mosaic:
                self.input('postref fix mosaic')

            # note well that the beam centre is coming from indexing so
            # should be already properly handled

            if self.get_wavelength_prov() == 'user':
                self.input('wavelength %f' % self.get_wavelength())

            # get all of the stored parameter values
            parameters = self.get_integrater_parameters('mosflm')

            # FIXME 27/SEP/06:
            # have to make sure that these are correctly applied -
            # that is, be sure that these come actually from autoindexing
            # not somehow from a previous instance of data integration...
            
            self.input('!parameters from autoindex run')
            for p in parameters.keys():
                self.input('%s %s' % (p, str(parameters[p])))

            # compute the detector limits to use for this...
            # these are w.r.t. the beam centre and are there to
            # ensure that spots are not predicted off the detector
            # (see bug # 2551)

            detector_width = self._fp_header['size'][0] * \
                             self._fp_header['pixel'][0]
            detector_height = self._fp_header['size'][1] * \
                              self._fp_header['pixel'][1]

            # fixme this will probably not work well for non-square
            # detectors...

            # FIXME 25/FEB/09 - replace this with limits xscan and yscan
            # which are relative to the detector centre not the direct
            # beam coordinate...

            # lim_x = min(beam[0], detector_width - beam[0])
            # lim_y = min(beam[1], detector_height - beam[1])

            # Debug.write('Detector limits: %.1f %.1f' % (lim_x, lim_y))

            # self.input('limits xmin 0.0 xmax %.1f ymin 0.0 ymax %.1f' % \
            # (lim_x, lim_y))            

            lim_x = 0.5 * detector_width
            lim_y = 0.5 * detector_height

            Debug.write('Scanner limits: %.1f %.1f' % (lim_x, lim_y))
            self.input('limits xscan %f yscan %f' % (lim_x, lim_y))

            # fudge factors to prevent Mosflm from being too fussy - 
            # FIXME this should probably be resolution / wavelength
            # dependent...
            self.input('separation close')
            self.input('refinement residual 15.0')
            self.input('refinement include partials')

            # set up the cell refinement - allowing quite a lot of
            # refinement for tricky cases (e.g. 7.2 SRS insulin SAD
            # data collected on MAR IP)

            self._reorder_cell_refinement_images()
            
            self.input('postref multi segments %d repeat 10' % \
                       len(self._mosflm_cell_ref_images))

            # FIXME 
            self.input('postref maxresidual 5.0')

            genfile = os.path.join(os.environ['BINSORT_SCR'],
                                   '%d_mosflm.gen' % self.get_xpid())

            self.input('genfile %s' % genfile)
            
            for cri in self._mosflm_cell_ref_images:
                self.input('process %d %d' % cri)
                self.input('go')

            # that should be everything 
            self.close_wait()

            # get the log file
            output = self.get_all_output()

            rms_values_last = None
            rms_values = None

            new_cycle_number = 0
            new_rms_values = { }
            new_image_counter = None
            new_ignore_update = False

            parse_cycle = 1
            parse_image = 0

            background_residual = { }
                                    
            for i in range(len(output)):
                o = output[i]

                # FIXME this output is sometimes mashed - the output
                # during the actual processing cycles is more reliable,
                # though perhaps harder to keep track of...

                # the correct way to run this will be to manually track
                # the cell refinement cycles, and look for
                # 'Post-refinement will use' as the beginning UNLESS
                # 'As this is near to the start, repeat integration'
                # was somewhere just above, in which case the cycle will
                # not be incremented. 

                if 'Processing Image' in o:
                    new_image_counter = int(o.split()[2])
                    parse_image = int(o.split()[2])

                if 'Repeating the entire run' in o:
                    parse_cycle += 1

                if 'Background residual' in o:
                    res = float(o.replace('residual=', '').split()[8])
                    
                    if not parse_cycle in background_residual:
                        background_residual[parse_cycle] = { }
                    background_residual[parse_cycle][parse_image] = res
                    
                if 'As this is near to the start' in o:
                    new_ignore_update = True

                if 'Post-refinement will use partials' in o:
                    if new_ignore_update:
                        new_ignore_update = False
                    else:
                        new_cycle_number += 1
                        new_rms_values[new_cycle_number] = { }

                if 'Final rms residual' in o:
                    rv = float(o.replace('mm', ' ').split()[3])
                    new_rms_values[new_cycle_number][new_image_counter] = rv

                if 'Rms positional error (mm) as a function of' in o and True:
                    images = []
                    cycles = []
                    rms_values = { }

                    j = i + 1

                    while output[j].split():
                        if 'Image' in output[j]:
                            for image in map(int, output[j].replace(
                                'Image', '').split()):
                                images.append(image)
                        else:
                            cycle = int(output[j].replace(
                                'Cycle', '').split()[0])
                            
                            if not cycle in cycles:
                                cycles.append(cycle)
                                rms_values[cycle] = []
                            
                            record = [output[j][k:k + 6] \
                                      for k in range(
                                11, len(output[j]), 6)]

                            data = []
                            for r in record:
                                if r.strip():
                                    data.append(r.strip())
                                record = data
                                    
                            try:
                                values = map(float, record)
                                for v in values:
                                    rms_values[cycle].append(v)
                            except ValueError, e:
                                Debug.write(
                                    'Error parsing %s as floats' % \
                                    output[j][12:])
                            
                        j += 1
                        

                    # now transform back the new rms residual values
                    # into the old structure... messy but effective!

                    for cycle in new_rms_values.keys():
                        images = new_rms_values[cycle].keys()
                        images.sort()
                        rms_values[cycle] = []
                        for i in images:
                            rms_values[cycle].append(
                                new_rms_values[cycle][i])
                    
                    rms_values_last = rms_values[max(cycles)]

            return rms_values, background_residual

        def _mosflm_refine_cell(self, set_spacegroup = None):
            '''Perform the refinement of the unit cell. This will populate
            all of the information needed to perform the integration.'''

            # self.reset()

            if not self.get_integrater_indexer():
                # this wrapper can present the indexer interface
                # if needed, so do so. if this set command has
                # been called already this should not be used...
                self.set_integrater_indexer(self)

            # get the things we need from the indexer - beware that if
            # the indexer has not yet been run this may spawn other
            # jobs...

            indxr = self.get_integrater_indexer()

            if not indxr.get_indexer_payload('mosflm_orientation_matrix'):
                # we will have to do  some indexing ourselves - the
                # existing indexing job doesn't provide an orientation
                # matrix

                # FIXME this needs implementing - copy information
                # from this indexer to myself, then reset my indexer too me

                pass

            lattice = indxr.get_indexer_lattice()
            mosaic = indxr.get_indexer_mosaic()
            cell = indxr.get_indexer_cell()
            beam = indxr.get_indexer_beam()

            # bug # 3174 - if mosaic is very small (here defined to be 
            # 0.25 x osc_width) then set to this minimum value.

            if mosaic < 0.25 * self.get_header_item('phi_width'):
                mosaic = 0.25 * self.get_header_item('phi_width')
                
            # check to see if there is a special mosflm beam around!

            if indxr.get_indexer_payload('mosflm_beam_centre'):
                beam = indxr.get_indexer_payload('mosflm_beam_centre')

            distance = indxr.get_indexer_distance()
            matrix = indxr.get_indexer_payload('mosflm_orientation_matrix')

            # check to see if there are parameters which I should be using for
            # cell refinement etc in here - if there are, use them - this
            # will also appear in integrate, for cases where that will
            # be called without cell refinemnt

            integration_params = indxr.get_indexer_payload(
                'mosflm_integration_parameters')

            if integration_params:
                # copy them somewhere useful... into the dictionary?
                # yes - that way they can be recycled...
                # after that, zap them because they will be obsolete!
                if integration_params.has_key('separation'):
                    self.set_integrater_parameter(
                        'mosflm', 'separation',
                        '%f %f' % tuple(integration_params['separation']))
                if integration_params.has_key('raster'):
                    self.set_integrater_parameter(
                        'mosflm', 'raster',
                        '%d %d %d %d %d' % tuple(integration_params['raster']))
                    
            indxr.set_indexer_payload('mosflm_integration_parameters', None)

            # copy these into myself for later reference, if indexer
            # is not myself - everything else is copied via the
            # cell refinement process...

            if indxr != self:
                self.set_indexer_input_lattice(lattice)
                self.set_indexer_beam(beam)


            # here need to check the LATTICE - which will be
            # something like tP etc. FIXME how to cope when the
            # spacegroup has been explicitly stated?

            spacegroup_number = lattice_to_spacegroup(lattice)

	    # FIXME 11/SEP/06 have an example set of data which will
            #                 make cell refinement "fail" - that is
            #                 not work very well - 9485/3[1VPX]. Therefore
	    #                 allow for more image wedges, read output.
            # 
            # What we are looking for in the output is:
            # 
            # INACCURATE CELL PARAMETERS
            #
            # followed by the dodgy cell parameters, along with the 
            # associated standard errors. Based on these need to decide 
            # what extra data would be helpful. Will also want to record
            # these standard deviations to decide if the next run of 
            # cell refinement makes things better... Turns out that this
            # example is very low resolution, so don't worry too hard
            # about it!

            if spacegroup_number >= 75:
                num_wedges = 1
            else:
                num_wedges = 2

            # FIXME 23/OCT/06 should only do this if the images are not
            # already assigned - for instance, in the case where the cell
            # refinement fails and more images are added after that failure
            # need to be able to cope with not changing them at this stage...

            # self._mosflm_cell_ref_images = None

            if not self._mosflm_cell_ref_images:
                self._mosflm_cell_ref_images = self._refine_select_images(
                    mosaic)

            # write the matrix file in xiaindex.mat

            f = open(os.path.join(self.get_working_directory(),
                                  'xiaindex-%s.mat' % lattice), 'w')
            for m in matrix:
                f.write(m)
            f.close()

            # then start the cell refinement

            task = 'Refine cell from %d wedges' % \
                   len(self._mosflm_cell_ref_images)

            self.set_task(task)

            self.start()

            if self._mosflm_gain:
                self.input('gain %5.2f' % self._mosflm_gain)

            if self.get_reversephi():
                detector = detector_class_to_mosflm(
                    self.get_header_item('detector_class'))
                self.input('detector %s reversephi' % detector)

            self.input('template "%s"' % self.get_template())
            self.input('directory "%s"' % self.get_directory())

            self.input('matrix xiaindex-%s.mat' % lattice)
            self.input('newmat xiarefine.mat')

            self.input('beam %f %f' % beam)
            self.input('distance %f' % distance)

            # FIXED is this the correct form? - it is now.

            # want to be able to test cell refinement in P1
            # as a way of investigating how solid the autoindex
            # solution is... therefore allow spacegroup to
            # be explicitly set...
            
            if set_spacegroup:
                self.input('symmetry %s' % set_spacegroup)
            else:
                self.input('symmetry %s' % spacegroup_number)
                
            # FIXME 18/JUN/08 - it may help to have an overestimate
            # of the mosaic spread in here as it *may* refine down
            # better than up... - this is not a good idea as it may
            # also not refine at all! - 12972 # integration failed

            # Bug # 3103
            if self._mosflm_cell_ref_double_mosaic:
                self.input('mosaic %f' % (2.0 * mosaic))
            else:
                self.input('mosaic %f' % mosaic)

            if self._mosflm_postref_fix_mosaic:
                self.input('postref fix mosaic')

            # if set, use the resolution for cell refinement - see
            # bug # 2078...
            
            if self._mosflm_cell_ref_resolution and not Flags.get_tricky():
                self.input('resolution %f' % \
                           self._mosflm_cell_ref_resolution)

            # note well that the beam centre is coming from indexing so
            # should be already properly handled
            if self.get_wavelength_prov() == 'user':
                self.input('wavelength %f' % self.get_wavelength())

            # get all of the stored parameter values
            parameters = self.get_integrater_parameters('mosflm')

            # FIXME 27/SEP/06:
            # have to make sure that these are correctly applied -
            # that is, be sure that these come actually from autoindexing
            # not somehow from a previous instance of data integration...
            
            self.input('!parameters from autoindex run')
            for p in parameters.keys():
                self.input('%s %s' % (p, str(parameters[p])))

            # fudge factors to prevent Mosflm from being too fussy
            self.input('separation close')
            self.input('refinement residual 15')
            self.input('refinement include partials')

            # compute the detector limits to use for this...
            # these are w.r.t. the beam centre and are there to
            # ensure that spots are not predicted off the detector
            # (see bug # 2551)

            detector_width = self._fp_header['size'][0] * \
                             self._fp_header['pixel'][0]
            detector_height = self._fp_header['size'][1] * \
                              self._fp_header['pixel'][1]

            lim_x = 0.5 * detector_width
            lim_y = 0.5 * detector_height

            Debug.write('Scanner limits: %.1f %.1f' % (lim_x, lim_y))
            self.input('limits xscan %f yscan %f' % (lim_x, lim_y))

            # set up the cell refinement - allowing quite a lot of
            # refinement for tricky cases (e.g. 7.2 SRS insulin SAD
            # data collected on MAR IP)

            self._reorder_cell_refinement_images()

            self.input('postref multi segments %d repeat 10' % \
                       len(self._mosflm_cell_ref_images))

            # FIXME
            self.input('postref maxresidual 5.0')
            
            genfile = os.path.join(os.environ['BINSORT_SCR'],
                                   '%d_mosflm.gen' % self.get_xpid())

            self.input('genfile %s' % genfile)

            for cri in self._mosflm_cell_ref_images:
                self.input('process %d %d' % cri)
                self.input('go')

            # that should be everything 
            self.close_wait()

            # get the log file
            output = self.get_all_output()

            # then look to see if the cell refinement worked ok - if it
            # didn't then this may indicate that the lattice was wrongly
            # selected.

            cell_refinement_ok = False

            for o in output:
                
                if 'Cell refinement is complete' in o:
                    cell_refinement_ok = True
                    
            if not cell_refinement_ok:
                Chatter.write(
                    'Looks like cell refinement failed - more follows...')

            # how best to handle this, I don't know... could
            #
            # (1) raise an exception
            # (2) try to figure out the solution myself
            #
            # probably (1) is better, because this will allow the higher
            # level of intelligence to sort it out. don't worry too hard
            # about this in the initial version, since labelit indexing
            # is pretty damn robust.

            # if it succeeded then populate the indexer output (myself)
            # with the new information - this can then be used
            # transparently in the integration.

            # here I need to get the refined distance, mosaic spread, unit
            # cell and matrix - should also look the yscale and so on, as
            # well as the final rms deviation in phi and distance

            # FIRST look for errors, and analysis stuff which may be
            # important...

            rms_values_last = None
            rms_values = None
            
            new_cycle_number = 0
            new_rms_values = { }
            new_image_counter = None
            new_ignore_update = False

            parse_cycle = 1
            parse_image = 0

            background_residual = { }
            
            for i in range(len(output)):
                o = output[i]

                # Fixme 01/NOV/06 dump this stuff from the top (error trapping)
                # into a trap_cell_refinement_errors method which is called
                # before the rest of the output is parsed...
                # look for overall cell refinement failure

                if 'Processing will be aborted' in o:

                    raise BadLatticeError, 'cell refinement failed'
                    
                
                # look to store the rms deviations on a per-image basis
                # this may be used to decide what to do about "inaccurate
                # cell parameters" below... may also want to record
                # them for comparison with cell refinement with a lower
                # spacegroup for solution elimination purposes...

                # FIXME this output is sometimes mashed - the output
                # during the actual processing cycles is more reliable,
                # though perhaps harder to keep track of...

                # the correct way to run this will be to manually track
                # the cell refinement cycles, and look for
                # 'Post-refinement will use' as the beginning UNLESS
                # 'As this is near to the start, repeat integration'
                # was somewhere just above, in which case the cycle will
                # not be incremented. 

                if 'Processing Image' in o:
                    new_image_counter = int(o.split()[2])

                if 'As this is near to the start' in o:
                    new_ignore_update = True

                if 'Post-refinement will use partials' in o:
                    if new_ignore_update:
                        new_ignore_update = False
                    else:
                        new_cycle_number += 1
                        new_rms_values[new_cycle_number] = { }

                if 'Final rms residual' in o:
                    rv = float(o.replace('mm', ' ').split()[3])
                    new_rms_values[new_cycle_number][new_image_counter] = rv

                if 'Rms positional error (mm) as a function of' in o and True:
                    images = []
                    cycles = []
                    rms_values = { }

                    j = i + 1

                    while output[j].split():
                        if 'Image' in output[j]:
                            for image in map(int, output[j].replace(
                                'Image', '').split()):
                                images.append(image)
                        else:
                            cycle = int(output[j].replace(
                                'Cycle', '').split()[0])
                            
                            if not cycle in cycles:
                                cycles.append(cycle)
                                rms_values[cycle] = []
                            
                            record = [output[j][k:k + 6] \
                                      for k in range(
                                11, len(output[j]), 6)]

                            data = []
                            for r in record:
                                if r.strip():
                                    data.append(r.strip())
                                record = data
                                    
                            try:
                                values = map(float, record)
                                for v in values:
                                    rms_values[cycle].append(v)
                            except ValueError, e:
                                Debug.write(
                                    'Error parsing %s as floats' % \
                                    output[j][12:])
                            
                        j += 1
                        
                    # by now we should have recorded everything so...print!
                    # Chatter.write('Final RMS deviations per image')
                    # for j in range(len(images)):
                    # Chatter.write('- %4d %5.3f' % (images[j],
                    # rms_values_last[j]))
                    
                    # now transform back the new rms residual values
                    # into the old structure... messy but effective!

                    for cycle in new_rms_values.keys():
                        images = new_rms_values[cycle].keys()
                        images.sort()
                        rms_values[cycle] = []
                        for i in images:
                            rms_values[cycle].append(
                                new_rms_values[cycle][i])

                    if cycles:
                        rms_values_last = rms_values[max(cycles)]
                    else:
                        rms_values_last = None

                # look for "error" type problems

                if 'is greater than the maximum allowed' in o and \
                       'FINAL weighted residual' in o:
                   
                    Debug.write('Large weighted residual... ignoring')
                    
                if 'INACCURATE CELL PARAMETERS' in o:
                    
                    # get the inaccurate cell parameters in question
                    parameters = output[i + 3].lower().split()

                    # and the standard deviations - so we can decide
                    # if it really has failed

                    sd_record = output[i + 5].replace(
                        'A', ' ').replace(',', ' ').split()
                    sds = map(float, [sd_record[j] for j in range(1, 12, 2)])

                    Debug.write('Standard deviations:')
                    Debug.write('A     %4.2f  B     %4.2f  C     %4.2f' % \
                                (tuple(sds[:3])))
                    Debug.write('Alpha %4.2f  Beta  %4.2f  Gamma %4.2f' % \
                                (tuple(sds[3:6])))
                                  
                    # FIXME 01/NOV/06 this needs to be toned down a little -
                    # perhaps looking at the relative error in the cell
                    # parameter, or a weighted "error" of the two combined,
                    # because this may give rise to an error: TS01 NATIVE LR
                    # failed in integration with this, because the error
                    # in a was > 0.1A in 228. Assert perhaps that the error
                    # should be less than 1.0e-3 * cell axis and less than
                    # 0.15A?

                    # and warn about them
                    Debug.write(
                        'In cell refinement, the following cell parameters')
                    Debug.write(
                        'have refined poorly:')
                    for p in parameters:
                        Debug.write('... %s' % p)

                    Debug.write(
                        'However, will continue to integration.')
                        

		if 'One or more cell parameters has changed by more' in o:
                    # this is a more severe example of the above problem...
                    Debug.write(
                        'Cell refinement is unstable...')

                    # so decide what to do about it...

                    raise BadLatticeError, 'Cell refinement failed'

                # other possible problems in the cell refinement - a
                # negative mosaic spread, for instance

                if 'Refined mosaic spread (excluding safety factor)' in o:
                    mosaic = float(o.split()[-1])

                    if mosaic < 0.05:
                        Debug.write('Negative mosaic spread (%5.2f)' %
                                    mosaic)

                        raise NegativeMosaicError, 'refinement failed'

            parse_cycle = 1
            parse_image = 0

            background_residual = { }
                        
            for i, o in enumerate(output):
                # o = output[i]

                # FIXED for all of these which follow - the refined values
                # for these parameters should only be stored if the cell
                # refinement were 100% successful - therefore gather
                # them up here and store them at the very end (e.g. once
                # success has been confirmed.) 01/NOV/06

                # FIXME will these get lost if the indexer in question is
                # not this program...? Find out... would be nice to write
                # this to Chatter too...

                # OK, in here want to accumulate the profile background
                # information (which will provide a clue as to whether
                # the image is blank) as a function of cycle and image
                # number - only challenge is that this will require harvesting
                # the information by hand...

                if 'Processing Image' in o:
                    parse_image = int(o.split()[2])

                if 'Repeating the entire run' in o:
                    parse_cycle += 1

                if 'Background residual' in o:

                    res = float(o.replace('residual=', '').split()[8])
                    
                    if not parse_cycle in background_residual:
                        background_residual[parse_cycle] = { }
                    background_residual[parse_cycle][parse_image] = res

                if 'Cell refinement is complete' in o:
                    j = i + 2
                    refined_cell = map(float, output[j].split()[2:])
                    error = map(float, output[j + 1].split()[1:])

                    names = ['A', 'B', 'C', 'Alpha', 'Beta', 'Gamma']

                    Debug.write('Errors in cell parameters (relative %)')

                    for j in range(6):
                        Debug.write('%s\t%7.3f %5.3f %.3f' % \
                                    (names[j], refined_cell[j],
                                     error[j],
                                     100.0 * error[j] / refined_cell[j]))
                
                if 'Refined cell' in o:
                    # feed these back to the indexer
                    indxr._indxr_cell = tuple(map(float, o.split()[-6:]))

                    # record the refined cell parameters for getting later
                    self._intgr_cell = tuple(map(float, o.split()[-6:]))
                    
                # FIXME do I need this? I think that the refined distance
                # is passed in as an integration parameter (see below)
                if 'Detector distance as a' in o:
                    # look through the "cycles" to get the final refined
                    # distance
                    j = i + 1
                    while output[j].strip() != '':
                        j += 1
                    distances = map(float, output[j - 1].split()[2:])
                    distance = 0.0
                    for d in distances:
                        distance += d
                    distance /= len(distances)
                    indxr._indxr_refined_distance = distance

                if 'YSCALE as a function' in o:
                    # look through the "cycles" to get the final refined
                    # yscale value
                    j = i + 1
                    while output[j].strip() != '':
                        j += 1
                    yscales = map(float, output[j - 1].split()[2:])
                    yscale = 0.0
                    for y in yscales:
                        yscale += y
                    yscale /= len(yscales)

                    self.set_integrater_parameter('mosflm',
                                                  'distortion yscale',
                                                  yscale)

                # next look for the distortion & raster parameters
                # see FIXME at the top of this file from 16/AUG/06

                if 'Final optimised raster parameters:' in o:
                    self.set_integrater_parameter('mosflm',
                                                  'raster',
                                                  o.split(':')[1].strip())

                if 'Separation parameters updated to' in o:
                    tokens = o.replace('mm', ' ').split()
                    self.set_integrater_parameter('mosflm',
                                                  'separation',
                                                  '%s %s' % \
                                                  (tokens[4], tokens[8]))
                    
                if 'XCEN    YCEN  XTOFRA' in o:
                    numbers = output[i + 1].split()

                    # this should probably be done via the FrameProcessor
                    # interface...
                    self.set_integrater_parameter('mosflm',
                                                  'beam',
                                                  '%s %s' % \
                                                  (numbers[0], numbers[1]))

                    # FIXME should this go through the FP interface?
                    # this conflicts with the calculation above
                    # of the average distance as well...
                    self.set_integrater_parameter('mosflm',
                                                  'distance',
                                                  numbers[3])
                    
                    self.set_integrater_parameter('mosflm',
                                                  'distortion tilt',
                                                  numbers[5])
                    self.set_integrater_parameter('mosflm',
                                                  'distortion twist',
                                                  numbers[6])

                # FIXME does this work if this mosflm is not
                # the one being used as an indexer? - probably not -
                # I will need a getIndexer.setMosaic() or something...
                if 'Refined mosaic spread' in o:
                    indxr._indxr_mosaic = float(o.split()[-1])

            # hack... FIXME (maybe?)
            # self._indxr_done = True
            self.set_indexer_done(True)
            
            # shouldn't need this.. remember that Python deals in pointers!
            self.set_indexer_payload('mosflm_orientation_matrix', open(
                os.path.join(self.get_working_directory(),
                             'xiarefine.mat'), 'r').readlines())
            indxr.set_indexer_payload('mosflm_orientation_matrix', open(
                os.path.join(self.get_working_directory(),
                             'xiarefine.mat'), 'r').readlines())

            return rms_values, background_residual

        def _mosflm_integrate(self):
            '''Perform the actual integration, based on the results of the
            cell refinement or indexing (they have the equivalent form.)'''

            # self.reset()

            # the only way to get here is through the cell refinement,
            # unless we're trying to go fast - which means that we may
            # have to create an indexer if fast - if we're going slow
            # then this should have been done by the cell refinement
            # stage...

            # FIXME add "am I going fast" check here

            if not self.get_integrater_indexer():
                # this wrapper can present the indexer interface
                # if needed, so do so. if this set command has
                # been called already this should not be used...
                self.set_integrater_indexer(self)

            # get the things we need from the indexer - beware that if
            # the indexer has not yet been run this may spawn other
            # jobs...

            indxr = self.get_integrater_indexer()

            if not indxr.get_indexer_payload('mosflm_orientation_matrix'):
                # we will have to do  some indexing ourselves - the
                # existing indexing job doesn't provide an orientation
                # matrix

                # FIXME this needs implementing - copy information
                # from this indexer to myself, then reset my indexer too me

                # FIXME this should probably raise an exception...

                pass

            lattice = indxr.get_indexer_lattice()
            mosaic = indxr.get_indexer_mosaic()
            cell = indxr.get_indexer_cell()
            beam = indxr.get_indexer_beam()
            distance = indxr.get_indexer_distance()
            matrix = indxr.get_indexer_payload('mosflm_orientation_matrix')

            # check to see if there are parameters which I should be using for
            # integration etc in here - if there are, use them - this will
            # only happen when the integration is "fast" and they haven't
            # been eaten by the cell refinemnt process

            integration_params = indxr.get_indexer_payload(
                'mosflm_integration_parameters')
            
            if integration_params:
                # copy them somewhere useful... into the dictionary?
                # yes - that way they can be recycled...
                # after that, zap them because they will be obsolete!
                if integration_params.has_key('separation'):
                    self.set_integrater_parameter(
                        'mosflm', 'separation',
                        '%f %f' % tuple(integration_params['separation']))
                if integration_params.has_key('raster'):
                    self.set_integrater_parameter(
                        'mosflm', 'raster',
                        '%d %d %d %d %d' % tuple(integration_params['raster']))
                    
            indxr.set_indexer_payload('mosflm_integration_parameters', None)

            # here need to check the LATTICE - which will be
            # something like tP etc. FIXME how to cope when the
            # spacegroup has been explicitly stated?

            spacegroup_number = lattice_to_spacegroup(lattice)

            f = open(os.path.join(self.get_working_directory(),
                                  'xiaintegrate.mat'), 'w')
            for m in matrix:
                f.write(m)
            f.close()

            # then start the integration

            task = 'Integrate frames %d to %d' % self._intgr_wedge

            self.set_task(task)

            summary_file = 'summary_%s.log' % spacegroup_number

            self.add_command_line('SUMMARY')
            self.add_command_line(summary_file)

            self.start()

            # if the integrater interface has the project, crystal, dataset
            # information available, pass this in to mosflm and also switch
            # on the harvesrng output. warning! if the harvesting is switched
            # on then this means that the files will all go to the same
            # place - for the moment move this to cwd.

            if not self._mosflm_refine_profiles:
                self.input('profile nooptimise')

            pname, xname, dname = self.get_integrater_project_info()

            if pname != None and xname != None and dname != None:
                Debug.write('Harvesting: %s/%s/%s' % (pname, xname, dname))
                
                # ensure that the harvest directory exists for this project
                # and if not, make it as mosflm may barf doing so!

                harvest_dir = os.path.join(os.environ['HARVESTHOME'],
                                           'DepositFiles', pname)

                if not os.path.exists(harvest_dir):
                    Debug.write('Creating harvest directory...')
                    os.makedirs(harvest_dir)

                # harvest file name will be %s.mosflm_run_start_end % dname
            
                self.input('harvest on')
                self.input('pname %s' % pname)
                self.input('xname %s' % xname)

                temp_dname = '%s_%s' % \
                             (dname, self.get_integrater_sweep_name())

                self.input('dname %s' % temp_dname)
                # self.input('ucwd')

            if self.get_reversephi():
                detector = detector_class_to_mosflm(
                    self.get_header_item('detector_class'))
                self.input('detector %s reversephi' % detector)

            self.input('template "%s"' % self.get_template())
            self.input('directory "%s"' % self.get_directory())

            # check for ice - and if so, exclude (ranges taken from
            # XDS documentation)
            if self.get_integrater_ice() != 0:

                Debug.write('Excluding ice rings')
                
                for record in open(os.path.join(
                    os.environ['XIA2_ROOT'],
                    'Data', 'Ice','Rings.dat')).readlines():
                    
                    resol = tuple(map(float, record.split()[:2]))
                    self.input('resolution exclude %.2f %.2f' % (resol))

            # generate the mask information from the detector class
            mask = standard_mask(self._fp_header['detector_class'])
            for m in mask:
                self.input(m)

            self.input('matrix xiaintegrate.mat')

            self.input('beam %f %f' % beam)
            self.input('distance %f' % distance)
            self.input('symmetry %s' % spacegroup_number)
            self.input('mosaic %f' % mosaic)

            self.input('refinement include partials')

            # note well that the beam centre is coming from indexing so
            # should be already properly handled - likewise the distance
            if self.get_wavelength_prov() == 'user':
                self.input('wavelength %f' % self.get_wavelength())

            # get all of the stored parameter values
            parameters = self.get_integrater_parameters('mosflm')
            for p in parameters.keys():
                self.input('%s %s' % (p, str(parameters[p])))

            # in here I need to get the GAIN parameter from the sweep
            # or from somewhere in memory....

            if self._mosflm_gain:
                self.input('gain %5.2f' % self._mosflm_gain)

            # check for resolution limits
            if self._intgr_reso_high > 0.0:
                if self._intgr_reso_low:
                    self.input('resolution %f %f' % (self._intgr_reso_high,
                                                     self._intgr_reso_low))
                else:
                    self.input('resolution %f' % self._intgr_reso_high)

            # set up the integration
            self.input('postref fix all')
            # fudge this needs to be fixed. FIXME!
            self.input('postref maxresidual 5.0')

            # compute the detector limits to use for this...
            # these are w.r.t. the beam centre and are there to
            # ensure that spots are not predicted off the detector
            # (see bug # 2551)

            detector_width = self._fp_header['size'][0] * \
                             self._fp_header['pixel'][0]
            detector_height = self._fp_header['size'][1] * \
                              self._fp_header['pixel'][1]

            # fixme this will probably not work well for non-square
            # detectors...

            # lim_x = min(beam[0], detector_width - beam[0])
            # lim_y = min(beam[1], detector_height - beam[1])

            # Debug.write('Detector limits: %.1f %.1f' % (lim_x, lim_y))

            # self.input('limits xmin 0.0 xmax %.1f ymin 0.0 ymax %.1f' % \
            # (lim_x, lim_y))            

            lim_x = 0.5 * detector_width
            lim_y = 0.5 * detector_height

            Debug.write('Scanner limits: %.1f %.1f' % (lim_x, lim_y))
            self.input('limits xscan %f yscan %f' % (lim_x, lim_y))

            if self._mosflm_postref_fix_mosaic:
                self.input('postref fix mosaic')
                
            self.input('separation close')

            # FIXME this is a horrible hack - I at least need to 
            # sand box this ... 
            if self.get_header_item('detector') == 'raxis':
                self.input('adcoffset 0')

            offset = self.get_frame_offset()

            genfile = os.path.join(os.environ['BINSORT_SCR'],
                                   '%d_mosflm.gen' % self.get_xpid())

            self.input('genfile %s' % genfile)

            # add an extra chunk of orientation refinement

            if Flags.get_tricky():
                a = self._intgr_wedge[0] - offset
                if self._intgr_wedge[0] - self._intgr_wedge[1] > 20:
                    b = a + 20
                else:
                    b = self._intgr_wedge[1] - offset

                self.input('postref segment 1 fix all')
                self.input('process %d %d' % (a, b))
                self.input('go')
                self.input('postref nosegment')
                self.input('process block %d' % \
                           (self._intgr_wedge[1] - self._intgr_wedge[0]))

            self.input('process %d %d' % (self._intgr_wedge[0] - offset,
                                          self._intgr_wedge[1] - offset))
                
            self.input('go')

            # that should be everything 
            self.close_wait()

            # get the log file
            output = self.get_all_output()

            # record a copy of it, perhaps
            # if self.get_integrater_sweep_name():
            # pname, xname, dname = self.get_integrater_project_info()
            # FileHandler.record_log_file('%s %s %s %s mosflm integrate' % \
            # (self.get_integrater_sweep_name(),
            # pname, xname, dname),
            # self.get_log_file())

            # look for things that we want to know...
            # that is, the output reflection file name, the updated
            # value for the gain (if present,) any warnings, errors,
            # or just interesting facts.

            integrated_images_first = 1.0e6
            integrated_images_last = -1.0e6

            # look for major errors

            for i in range(len(output)):
                o = output[i]
                if 'LWBAT: error in ccp4_lwbat' in o:
                    raise RuntimeError, 'serious mosflm error - inspect %s' % \
                          self.get_log_file()

            for i in range(len(output)):
                o = output[i]

                if 'Integrating Image' in o:
                    batch = int(o.split()[2])
                    if batch < integrated_images_first:
                        integrated_images_first = batch
                    if batch > integrated_images_last:
                        integrated_images_last = batch

                if 'ERROR IN DETECTOR GAIN' in o:
                    # look for the correct gain
                    for j in range(i, i + 10):
                        if output[j].split()[:2] == ['set', 'to']:
                            gain = float(output[j].split()[-1][:-1])

                            # check that this is not the input
                            # value... Bug # 3374

                            if self._mosflm_gain:
                                
                                if math.fabs(gain - self._mosflm_gain) > 0.02:
                            
                                    self.set_integrater_parameter(
                                        'mosflm', 'gain', gain)
                                    self.set_integrater_export_parameter(
                                        'mosflm', 'gain', gain)
                                    Debug.write('GAIN updated to %f' % gain)

                                    self._mosflm_gain = gain
                                    self._mosflm_rerun_integration = True

                            else:

                                self.set_integrater_parameter(
                                    'mosflm', 'gain', gain)
                                self.set_integrater_export_parameter(
                                    'mosflm', 'gain', gain)
                                Debug.write('GAIN found to be %f' % gain)
                                
                                self._mosflm_gain = gain
                                self._mosflm_rerun_integration = True

                # FIXME if mosaic spread refines to a negative value
                # once the lattice has passed the triclinic postrefinement
                # test then fix this by setting "POSTREF FIX MOSAIC" and
                # restarting.

                if 'Smoothed value for refined mosaic spread' in o:
                    mosaic = float(o.split()[-1])
                    if mosaic < 0.0:
                        raise IntegrationError, 'negative mosaic spread'

                if 'WRITTEN OUTPUT MTZ FILE' in o:
                    self._mosflm_hklout = os.path.join(
                        self.get_working_directory(),
                        output[i + 1].split()[-1])

                    Debug.write('Integration output: %s' % \
                                self._mosflm_hklout)

                if 'Number of Reflections' in o:
                    self._intgr_n_ref = int(o.split()[-1])

                # FIXME check for BGSIG errors - if one is found
                # analyse the output for a sensible resolution
                # limit to use for integration...

                # NO! if a BGSIG error happened try not refining the
                # profile and running again...
                if 'BGSIG too large' in o:
                    # we have a BGSIG problem - explain, fix the
                    # problem and rerun

                    if not self._mosflm_refine_profiles:
                        raise RuntimeError, 'BGSIG error with profiles fixed'
                    
                    Debug.write(
                        'BGSIG error detected - try fixing profile...')
                    
                    self._mosflm_refine_profiles = False
                    self.set_integrater_done(False)

                    return

                if 'An unrecoverable error has occurred in GETPROF' in o:
                    Debug.write(
                        'GETPROF error detected - try fixing profile...')
                    self._mosflm_refine_profiles = False
                    self.set_integrater_done(False)

                    return
                    
                if 'MOSFLM HAS TERMINATED EARLY' in o:
                    Chatter.write('Mosflm has failed in integration')
                    message = 'The input was:\n\n'
                    for input in self.get_all_input():
                        message += '  %s' % input
                    Chatter.write(message)
                    raise RuntimeError, \
                          'integration failed: reason unknown (log %s)' % \
                          self.get_log_file()

            if not self._mosflm_hklout:
                raise RuntimeError, 'processing abandoned'

            self._intgr_batches_out = (integrated_images_first,
                                       integrated_images_last)

            Chatter.write('Processed batches %d to %d' % \
                          self._intgr_batches_out)

            # write the report for each image as .*-#$ to Chatter -
            # detailed report will be written automagically to science...

            parsed_output = _parse_mosflm_integration_output(output)

            spot_status = _happy_integrate_lp(parsed_output)

            # inspect the output for e.g. very high weighted residuals

            images = parsed_output.keys()
            images.sort()
            
            max_weighted_residual = 0.0

            # FIXME bug 2175 this should probably look at the distribution
            # of values rather than the peak, since this is probably a better
            # diagnostic of a poor lattice.

            residuals = []
            for i in images:
                if parsed_output[i].has_key('weighted_residual'):
                    residuals.append(parsed_output[i]['weighted_residual'])

            mean, sd = mean_sd(residuals)

            Chatter.write('Weighted RMSD: %.2f (%.2f)' % \
                          (mean, sd))
            
            for i in images:
                data = parsed_output[i]

                if data.has_key('weighted_residual'):

                    if data['weighted_residual'] > max_weighted_residual:
                        max_weighted_residual = data['weighted_residual']
            
            if len(spot_status) > 60:
                Chatter.write('Integration status per image (60/record):')
            else:
                Chatter.write('Integration status per image:')

            for chunk in [spot_status[i:i + 60] \
                          for i in range(0, len(spot_status), 60)]:
                Chatter.write(chunk)
                
            Chatter.write(
                '"o" => good        "%" => ok        "!" => bad rmsd')
            Chatter.write(
                '"O" => overloaded  "#" => many bad  "." => blank') 
            Chatter.write(
                '"@" => abandoned') 

            # gather the statistics from the postrefinement

            try:
                postref_result = _parse_summary_file(
                    os.path.join(self.get_working_directory(), summary_file))
            except AssertionError, e:
                postref_result = { }

            # now write this to a postrefinement log

            postref_log = os.path.join(self.get_working_directory(),
                                       'postrefinement.log')

            fout = open(postref_log, 'w')

            fout.write('$TABLE: Postrefinement for %s:\n' % \
                       self._intgr_sweep_name)
            fout.write('$GRAPHS: Missetting angles:A:1, 2, 3, 4: $$\n')
            fout.write('Batch PhiX PhiY PhiZ $$ Batch PhiX PhiY PhiZ $$\n')

            for image in sorted(postref_result):
                phix = postref_result[image].get('phix', 0.0)
                phiy = postref_result[image].get('phiy', 0.0)
                phiz = postref_result[image].get('phiz', 0.0)

                fout.write('%d %5.2f %5.2f %5.2f\n' % \
                           (image, phix, phiy, phiz))

            fout.write('$$\n')
            fout.close()            

            if self.get_integrater_sweep_name():
                pname, xname, dname = self.get_integrater_project_info()
                FileHandler.record_log_file('%s %s %s %s postrefinement' % \
                                            (self.get_integrater_sweep_name(),
                                             pname, xname, dname),
                                            postref_log)            

            return self._mosflm_hklout

        def _mosflm_parallel_integrate(self):
            '''Perform the integration as before, but this time as a
            number of parallel Mosflm jobs (hence, in separate directories)
            and including a step of pre-refinement of the mosaic spread and
            missets. This will all be kind of explicit and hence probably
            messy!'''

            # ok, in here try to get the missetting angles at two "widely
            # spaced" points, so that the missetting angle calculating
            # expert can do it's stuff. 

            figured = False
            if figured:

                offset = self.get_frame_offset()
                start = self._intgr_wedge[0] - offset
                end = self._intgr_wedge[1] - offset
                next = start + \
                       int(round(90.0 / self.get_header_item('phi_width')))
                
                if next > end:
                    next = end

                end -= 3

                # right, run:
                
                wd = os.path.join(self.get_working_directory(),
                                  'misset' % j)
                if not os.path.exists(wd):
                    os.makedirs(wd)

                # create the Driver, configure 
                job = DriverFactory.Driver(self._mosflm_driver_type)
                job.set_executable(self.get_executable())
                job.set_working_directory(wd)
                auto_logfiler(job)
                
            # FIXME why am I getting the cell constants and so on from the
            # indexer?! Because that is where the _integrate_prepare step
            # stores them... interesting!

            if not self.get_integrater_indexer():
                # should I raise a RuntimeError here?!
                self.set_integrater_indexer(self)

            indxr = self.get_integrater_indexer()

            lattice = indxr.get_indexer_lattice()
            spacegroup_number = lattice_to_spacegroup(lattice)
            mosaic = indxr.get_indexer_mosaic()
            cell = indxr.get_indexer_cell()
            beam = indxr.get_indexer_beam()
            distance = indxr.get_indexer_distance()
            matrix = indxr.get_indexer_payload('mosflm_orientation_matrix')

            # integration parameters - will have to be copied to all
            # of the running Mosflm instances...

            integration_params = indxr.get_indexer_payload(
                'mosflm_integration_parameters')
            
            if integration_params:
                if integration_params.has_key('separation'):
                    self.set_integrater_parameter(
                        'mosflm', 'separation',
                        '%f %f' % tuple(integration_params['separation']))
                if integration_params.has_key('raster'):
                    self.set_integrater_parameter(
                        'mosflm', 'raster',
                        '%d %d %d %d %d' % tuple(integration_params['raster']))
                    
            indxr.set_indexer_payload('mosflm_integration_parameters', None)
            pname, xname, dname = self.get_integrater_project_info()

            # what follows below should (i) be run in separate directories
            # and (ii) be repeated N=parallel times.

            parallel = Flags.get_parallel()

            if not parallel:
                raise RuntimeError, 'parallel not set'
            if parallel < 2:
                raise RuntimeError, 'parallel not parallel: %s' % parallel

            jobs = []
            hklouts = []
            # reindex_ops = []
            nref = 0
               
            # calculate the chunks to use
            offset = self.get_frame_offset()
            start = self._intgr_wedge[0] - offset
            end = self._intgr_wedge[1] - offset

            left_images = 1 + end - start
            left_chunks = parallel
            chunks = []

            while left_images > 0:
                size = left_images / left_chunks
                chunks.append((start, start + size - 1))
                start += size
                left_images -= size
                left_chunks -= 1

            summary_files = []

            for j in range(parallel):

                # make some working directories, as necessary - chunk-(0:N-1)
                wd = os.path.join(self.get_working_directory(),
                                  'chunk-%d' % j)
                if not os.path.exists(wd):
                    os.makedirs(wd)

                # create the Driver, configure 
                job = DriverFactory.Driver(self._mosflm_driver_type)
                job.set_executable(self.get_executable())
                job.set_working_directory(wd)

                auto_logfiler(job)

                # create the starting point
                f = open(os.path.join(wd, 'xiaintegrate.mat'), 'w')
                for m in matrix:
                    f.write(m)
                f.close()

                spacegroup_number = lattice_to_spacegroup(lattice)
                summary_file = 'summary_%s.log' % spacegroup_number
                job.add_command_line('SUMMARY')
                job.add_command_line(summary_file)

                summary_files.append(os.path.join(wd, summary_file))

                job.start()

                if not self._mosflm_refine_profiles:
                    job.input('profile nooptimise')
                    
                # N.B. for harvesting need to append N to dname.
                    
                if pname != None and xname != None and dname != None:
                    Debug.write('Harvesting: %s/%s/%s' % 
                                (pname, xname, dname))
                    
                    harvest_dir = os.path.join(os.environ['HARVESTHOME'], 
                                               'DepositFiles', pname)

                    if not os.path.exists(harvest_dir):
                        Debug.write('Creating harvest directory...')
                        os.makedirs(harvest_dir)

                    job.input('harvest on')
                    job.input('pname %s' % pname)
                    job.input('xname %s' % xname)

                    temp_dname = '%s_%s' % \
                                 (dname, self.get_integrater_sweep_name())

                    job.input('dname %s' % temp_dname)

                if self.get_reversephi():
                    detector = detector_class_to_mosflm(
                        self.get_header_item('detector_class'))
                    job.input('detector %s reversephi' % detector)

                job.input('template "%s"' % self.get_template())
                job.input('directory "%s"' % self.get_directory())

                # check for ice - and if so, exclude (ranges taken from
                # XDS documentation)
                if self.get_integrater_ice() != 0:

                    Debug.write('Excluding ice rings')
                    
                    for record in open(os.path.join(
                        os.environ['XIA2_ROOT'],
                        'Data', 'Ice','Rings.dat')).readlines():
                    
                        resol = tuple(map(float, record.split()[:2]))
                        job.input('resolution exclude %.2f %.2f' % (resol))

                # generate the mask information from the detector class
                mask = standard_mask(self._fp_header['detector_class'])
                for m in mask:
                    job.input(m)

                # suggestion from HRP 10/AUG/09
                job.input('matrix xiaintegrate.mat')
                # job.input('target xiaintegrate.mat')

                job.input('beam %f %f' % beam)
                job.input('distance %f' % distance)
                job.input('symmetry %s' % spacegroup_number)
                job.input('mosaic %f' % mosaic)

                # TEST: re-autoindex the pattern to see if the problem
                # with the cell refinement convergence radius goes away...
                #
                # This doesn't work, lots of other problems => calculate the
                # right missets ab initio.
                # 
                # a, b = chunks[j]

                # job.input('autoindex dps refine image %d' % a)
                # job.input('autoindex dps refine image %d' % b)
                # job.input('newmat processed.mat')
                # job.input('go')

                if self._mosflm_postref_fix_mosaic:
                    job.input('postref fix mosaic')

                job.input('refinement include partials')

                # note well that the beam centre is coming from indexing so
                # should be already properly handled - likewise the distance
                if self.get_wavelength_prov() == 'user':
                    job.input('wavelength %f' % self.get_wavelength())

                # get all of the stored parameter values
                parameters = self.get_integrater_parameters('mosflm')
                for p in parameters.keys():
                    job.input('%s %s' % (p, str(parameters[p])))

                # in here I need to get the GAIN parameter from the sweep
                # or from somewhere in memory....

                if self._mosflm_gain:
                    job.input('gain %5.2f' % self._mosflm_gain)

                # check for resolution limits
                if self._intgr_reso_high > 0.0:
                    if self._intgr_reso_low:
                        job.input('resolution %f %f' % (self._intgr_reso_high,
                                                         self._intgr_reso_low))
                    else:
                        job.input('resolution %f' % self._intgr_reso_high)

                # set up the integration
                job.input('postref fix all')
                # fudge this needs to be fixed. FIXME!
                job.input('postref maxresidual 5.0')

                # compute the detector limits to use for this...
                # these are w.r.t. the beam centre and are there to
                # ensure that spots are not predicted off the detector
                # (see bug # 2551)
                
                detector_width = self._fp_header['size'][0] * \
                                 self._fp_header['pixel'][0]
                detector_height = self._fp_header['size'][1] * \
                                  self._fp_header['pixel'][1]
                
                # fixme this will probably not work well for non-square
                # detectors... like the pilatus?!

                lim_x = 0.5 * detector_width
                lim_y = 0.5 * detector_height
                
                Debug.write('Scanner limits: %.1f %.1f' % (lim_x, lim_y))
                job.input('limits xscan %f yscan %f' % (lim_x, lim_y))

                # FIXME somewhere here need to include the pre-refinement
                # step... start with reprocessing first 4 images...

                a, b = chunks[j]

                if b - a > 3:
                    b = a + 3

                if Flags.get_automatch():
                    lim = 0.25 * min(detector_width, detector_height)

                    job.input('automatch')
                    job.input('refine nousebox')
                    job.input('refine limit %.2f' % lim)

                job.input('postref multi segments 1')
                job.input('process %d %d' % (a, b))
                job.input('go')
                
                job.input('postref nosegment')
                
                if self._mosflm_postref_fix_mosaic:
                    job.input('postref fix mosaic')
                
                job.input('separation close')

                # FIXME this is a horrible hack - I at least need to 
                # sand box this ... 
                if self.get_header_item('detector') == 'raxis':
                    job.input('adcoffset 0')

                genfile = os.path.join(os.environ['BINSORT_SCR'],
                                       '%d_%d_mosflm.gen' %
                                       (self.get_xpid(), j))

                job.input('genfile %s' % genfile)

                job.input('process %d %d' % chunks[j])
                
                job.input('go')

                # these are now running so ...

                jobs.append(job)

                continue

            # ok, at this stage I need to ...
            #
            # (i) accumulate the statistics as a function of batch
            # (ii) mong them into a single block
            #
            # This is likely to be a pain in the arse!

            first_integrated_batch = 1.0e6
            last_integrated_batch = -1.0e6

            all_residuals = []
            all_spot_status = ''

            threads = []
            
            for j in range(parallel):
                job = jobs[j]

                # now wait for them to finish - first wait will really be the
                # first one, then all should be finished...

                thread = Background(job, 'close_wait')
                thread.start()
                threads.append(thread)

            for j in range(parallel):
                thread = threads[j]
                thread.stop()
                job = jobs[j]

                # get the log file
                output = job.get_all_output()
                
                # record a copy of it, perhaps - though not if parallel
                if self.get_integrater_sweep_name() and False:
                    pname, xname, dname = self.get_integrater_project_info()
                    FileHandler.record_log_file(
                        '%s %s %s %s mosflm integrate' % \
                        (self.get_integrater_sweep_name(),
                         pname, xname, '%s_%d' % (dname, j)),
                        job.get_log_file())

                # look for things that we want to know...
                # that is, the output reflection file name, the updated
                # value for the gain (if present,) any warnings, errors,
                # or just interesting facts.

                integrated_images_first = 1.0e6
                integrated_images_last = -1.0e6
 
                # look for major errors

                for i in range(len(output)):
                    o = output[i]
                    if 'LWBAT: error in ccp4_lwbat' in o:
                        raise RuntimeError, 'serious error - inspect %s' % \
                              self.get_log_file()

                for i in range(len(output)):
                    o = output[i]

                    if 'Integrating Image' in o:
                        batch = int(o.split()[2])
                        if batch < integrated_images_first:
                            integrated_images_first = batch
                        if batch > integrated_images_last:
                            integrated_images_last = batch
                        if batch < first_integrated_batch:
                            first_integrated_batch = batch
                        if batch > last_integrated_batch:
                            last_integrated_batch = batch

                    if 'ERROR IN DETECTOR GAIN' in o:
                        # look for the correct gain
                        for j in range(i, i + 10):
                            if output[j].split()[:2] == ['set', 'to']:
                                gain = float(output[j].split()[-1][:-1])

                                # check that this is not the input
                                # value... Bug # 3374

                                if self._mosflm_gain:
                                
                                    if math.fabs(
                                        gain - self._mosflm_gain) > 0.02:
                            
                                        self.set_integrater_parameter(
                                            'mosflm', 'gain', gain)
                                        self.set_integrater_export_parameter(
                                            'mosflm', 'gain', gain)
                                        Debug.write(
                                            'GAIN updated to %f' % gain)

                                        self._mosflm_gain = gain
                                        self._mosflm_rerun_integration = True

                                else:

                                    self.set_integrater_parameter(
                                        'mosflm', 'gain', gain)
                                    self.set_integrater_export_parameter(
                                        'mosflm', 'gain', gain)
                                    Debug.write('GAIN found to be %f' % gain)
                                
                                    self._mosflm_gain = gain
                                    self._mosflm_rerun_integration = True

                    # FIXME if mosaic spread refines to a negative value
                    # once the lattice has passed the triclinic postrefinement
                    # test then fix this by setting "POSTREF FIX MOSAIC" and
                    # restarting.

                    if 'Smoothed value for refined mosaic spread' in o:
                        mosaic = float(o.split()[-1])
                        if mosaic < 0.0:
                            raise IntegrationError, 'negative mosaic spread'

                    if 'WRITTEN OUTPUT MTZ FILE' in o:
                        hklout = os.path.join(
                            job.get_working_directory(),
                            output[i + 1].split()[-1])

                        Debug.write('Integration output: %s' % hklout)
                        hklouts.append(hklout)

                        # compute the corresponding reindex operation
                        # from the local xiaintegrate.mat and the NEWMAT...
                        # reindex_op = reindex_sym_related(
                        # open(os.path.join(job.get_working_directory(),
                        # 'processed.mat')).read(),
                        # open(os.path.join(job.get_working_directory(),
                        # 'xiaintegrate.mat')).read())
                        
                        # reindex_ops.append(reindex_op)

                    if 'Number of Reflections' in o:
                        nref += int(o.split()[-1])

                    if 'BGSIG too large' in o:
                        Debug.write(
                            'BGSIG error detected - try fixing profile...')
                        self._mosflm_refine_profiles = False
                        self.set_integrater_done(False)
                        
                        return

                    if 'An unrecoverable error has occurred in GETPROF' in o:
                        Debug.write(
                            'GETPROF error detected - try fixing profile...')
                        self._mosflm_refine_profiles = False
                        self.set_integrater_done(False)
                        
                        return

                    if 'MOSFLM HAS TERMINATED EARLY' in o:
                        Chatter.write('Mosflm has failed in integration')
                        message = 'The input was:\n\n'
                        for input in self.get_all_input():
                            message += '  %s' % input
                        Chatter.write(message)
                        raise RuntimeError, \
                              'integration failed: reason unknown (log %s)' % \
                              self.get_log_file()


                # here
                # write the report for each image as .*-#$ to Chatter -
                # detailed report will be written automagically to science...

                parsed_output = _parse_mosflm_integration_output(output)
                spot_status = _happy_integrate_lp(parsed_output)

                # inspect the output for e.g. very high weighted residuals

                images = parsed_output.keys()
                images.sort()
                
                max_weighted_residual = 0.0
                
                residuals = []
                for i in images:
                    if parsed_output[i].has_key('weighted_residual'):
                        residuals.append(parsed_output[i]['weighted_residual'])

                for r in residuals:
                    all_residuals.append(r)

                for s in spot_status:
                    all_spot_status += s
                    
                # concatenate all of the output lines to our own output
                # channel (may be messy, but nothing better presents itself...
                # yuck, this involves delving in to the Driver interface...

                for record in output:
                    self._standard_output_records.append(record)
                    if not self._log_file is None:
                        self._log_file.write(record)
            
            self._intgr_batches_out = (first_integrated_batch,
                                       last_integrated_batch)

            Chatter.write('Processed batches %d to %d' % \
                          self._intgr_batches_out)

            spot_status = all_spot_status

            if len(spot_status) > 60:
                Chatter.write('Integration status per image (60/record):')
            else:
                Chatter.write('Integration status per image:')

            for chunk in [spot_status[i:i + 60] \
                          for i in range(0, len(spot_status), 60)]:
                Chatter.write(chunk)

            Chatter.write(
                '"o" => good        "%" => ok        "!" => bad rmsd')
            Chatter.write(
                '"O" => overloaded  "#" => many bad  "." => blank') 
            Chatter.write(
                '"@" => abandoned') 

            # gather the statistics from the postrefinement for all sweeps

            postref_result = { }

            for summary in summary_files:
                try:
                    update = _parse_summary_file(summary)
                except AssertionError, e:
                    update = { }
                postref_result.update(update)

            # now write this to a postrefinement log

            postref_log = os.path.join(self.get_working_directory(),
                                       'postrefinement.log')

            fout = open(postref_log, 'w')

            fout.write('$TABLE: Postrefinement for %s:\n' % \
                       self._intgr_sweep_name)
            fout.write('$GRAPHS: Missetting angles:A:1, 2, 3, 4: $$\n')
            fout.write('Batch PhiX PhiY PhiZ $$ Batch PhiX PhiY PhiZ $$\n')

            for image in sorted(postref_result):
                phix = postref_result[image].get('phix', 0.0)
                phiy = postref_result[image].get('phiy', 0.0)
                phiz = postref_result[image].get('phiz', 0.0)

                fout.write('%d %5.2f %5.2f %5.2f\n' % \
                           (image, phix, phiy, phiz))

            fout.write('$$\n')
            fout.close()

            if self.get_integrater_sweep_name():
                pname, xname, dname = self.get_integrater_project_info()
                FileHandler.record_log_file('%s %s %s %s postrefinement' % \
                                            (self.get_integrater_sweep_name(),
                                             pname, xname, dname),
                                            postref_log)
            
            # sort together all of the hklout files in hklouts to get the
            # final reflection file... FIXME, need to reindex each of these
            # as well...

            # new_hklouts = hklouts

            # for j, hklin in enumerate(hklouts):
            # reindex_op = reindex_ops[j]
            # reindex = Reindex()
            # reindex.set_working_directory(self.get_working_directory())
            # auto_logfiler(reindex)                
            # hklout = '%s_proc.mtz' % hklin[:-4]
            # reindex.set_hklin(hklin)
            # reindex.set_hklout(hklout)
            # reindex.set_operator(reindex_op)
            # reindex.reindex()
            # new_hklouts.append(hklout)
            
            hklouts.sort()

            hklout = os.path.join(self.get_working_directory(),
                                  os.path.split(hklouts[0])[-1])

            Debug.write('Sorting data to %s' % hklout)
            for hklin in hklouts:
                Debug.write('<= %s' % hklin)

            sortmtz = Sortmtz()
            sortmtz.set_hklout(hklout)
            for hklin in hklouts:
                sortmtz.add_hklin(hklin)

            sortmtz.sort()

            self._mosflm_hklout = hklout

            return self._mosflm_hklout
        
        def _reorder_cell_refinement_images(self):
            if not self._mosflm_cell_ref_images:
                raise RuntimeError, 'no cell refinement images to reorder'

            hashmap = { }

            for m in self._mosflm_cell_ref_images:
                hashmap[m[0]] = m[1]

            keys = hashmap.keys()
            keys.sort()

            cell_ref_images = [(k, hashmap[k]) for k in keys]
            self._mosflm_cell_ref_images = cell_ref_images
            return

        def generate_best_files(self, indxr, image_list):
            '''Integrate a list of single images as numbers with the
            BEST output switched on - this is to support the strategy
            calculation. Also run an autoindex to get the bestfile.dat
            file (the radial background) out.'''

            # first autoindex to generate the .dat file

            if not indxr.get_indexer_payload('mosflm_orientation_matrix'):
                raise RuntimeError, 'indexer has no mosflm orientation'

            lattice = indxr.get_indexer_lattice()
            mosaic = indxr.get_indexer_mosaic()
            cell = indxr.get_indexer_cell()
            beam = indxr.get_indexer_beam()
            distance = indxr.get_indexer_distance()
            matrix = indxr.get_indexer_payload('mosflm_orientation_matrix')

            integration_params = indxr.get_indexer_payload(
                'mosflm_integration_parameters')
            
            if integration_params:
                if integration_params.has_key('separation'):
                    self.set_integrater_parameter(
                        'mosflm', 'separation',
                        '%f %f' % tuple(integration_params['separation']))
                if integration_params.has_key('raster'):
                    self.set_integrater_parameter(
                        'mosflm', 'raster',
                        '%d %d %d %d %d' % tuple(integration_params['raster']))
                    
            spacegroup_number = lattice_to_spacegroup(lattice)

            f = open(os.path.join(self.get_working_directory(),
                                  'xia-best-generate.mat'), 'w')
            for m in matrix:
                f.write(m)
            f.close()

            self.start()

            if self.get_reversephi():
                detector = detector_class_to_mosflm(
                    self.get_header_item('detector_class'))
                self.input('detector %s reversephi' % detector)

            self.input('template "%s"' % self.get_template())
            self.input('directory "%s"' % self.get_directory())

            # generate the mask information from the detector class
            mask = standard_mask(self._fp_header['detector_class'])
            for m in mask:
                self.input(m)

            self.input('matrix xia-best-generate.mat')

            self.input('beam %f %f' % beam)
            self.input('distance %f' % distance)
            self.input('symmetry %s' % spacegroup_number)
            self.input('mosaic %f' % mosaic)

            # note well that the beam centre is coming from indexing so
            # should be already properly handled - likewise the distance
            if self.get_wavelength_prov() == 'user':
                self.input('wavelength %f' % self.get_wavelength())

            # get all of the stored parameter values
            parameters = self.get_integrater_parameters('mosflm')
            for p in parameters.keys():
                self.input('%s %s' % (p, str(parameters[p])))

            # in here I need to get the GAIN parameter from the sweep
            # or from somewhere in memory....

            self.input('best on')
            for image in image_list:
                self.input('autoindex dps refine image %d' % image)
            self.input('go')
            self.input('best off')

            # that should be everything 
            self.close_wait()

            # get the log file
            output = self.get_all_output()

            # then read in the .dat file...

            self._mosflm_best_datfile = open(os.path.join(
                self.get_working_directory(), 'bestfile.dat'), 'r').read()

            # then integrate to get the .par and .hkl file

            self.start()

            if self.get_reversephi():
                detector = detector_class_to_mosflm(
                    self.get_header_item('detector_class'))
                self.input('detector %s reversephi' % detector)

            self.input('template "%s"' % self.get_template())
            self.input('directory "%s"' % self.get_directory())

            # generate the mask information from the detector class
            mask = standard_mask(self._fp_header['detector_class'])
            for m in mask:
                self.input(m)

            self.input('matrix xia-best-generate.mat')

            self.input('beam %f %f' % beam)
            self.input('distance %f' % distance)
            self.input('symmetry %s' % spacegroup_number)
            self.input('mosaic %f' % mosaic)

            # note well that the beam centre is coming from indexing so
            # should be already properly handled - likewise the distance
            if self.get_wavelength_prov() == 'user':
                self.input('wavelength %f' % self.get_wavelength())

            # get all of the stored parameter values
            parameters = self.get_integrater_parameters('mosflm')
            for p in parameters.keys():
                self.input('%s %s' % (p, str(parameters[p])))

            # in here I need to get the GAIN parameter from the sweep
            # or from somewhere in memory....

            if self._mosflm_gain:
                self.input('gain %5.2f' % self._mosflm_gain)

            # check for resolution limits
            if self._intgr_reso_high > 0.0:
                self.input('resolution %f' % self._intgr_reso_high)

            # set up the integration
            self.input('postref fix all')

            detector_width = self._fp_header['size'][0] * \
                             self._fp_header['pixel'][0]
            detector_height = self._fp_header['size'][1] * \
                              self._fp_header['pixel'][1]

            # lim_x = min(beam[0], detector_width - beam[0])
            # lim_y = min(beam[1], detector_height - beam[1])

            # self.input('limits xmin 0.0 xmax %.1f ymin 0.0 ymax %.1f' % \
            # (lim_x, lim_y))            

            lim_x = 0.5 * detector_width
            lim_y = 0.5 * detector_height

            Debug.write('Scanner limits: %.1f %.1f' % (lim_x, lim_y))
            self.input('limits xscan %f yscan %f' % (lim_x, lim_y))

            if self._mosflm_postref_fix_mosaic:
                self.input('postref fix mosaic')
                
            self.input('separation close')

            if self.get_header_item('detector') == 'raxis':
                self.input('adcoffset 0')

            self.input('best on')
            for image in image_list:
                self.input('process %d %d' % (image, image))
                self.input('go')
            self.input('best off')

            # that should be everything 
            self.close_wait()

            # get the log file
            output = self.get_all_output()

            # read the output

            # then read the resulting files into memory
            # bestfile.par, bestfile.hkl.

            self._mosflm_best_parfile = open(os.path.join(
                self.get_working_directory(), 'bestfile.par'), 'r').read()
            self._mosflm_best_hklfile = open(os.path.join(
                self.get_working_directory(), 'bestfile.hkl'), 'r').read()

            return self._mosflm_best_datfile, self._mosflm_best_parfile, \
                   self._mosflm_best_hklfile

        # overload these methods as we don't want the resolution range
        # feeding back...
        
        def set_integrater_resolution(self, dmin, dmax, user = False):
            pass
        
        def set_integrater_high_resolution(self, dmin, user = False):
            pass
        
        def set_integrater_low_resolution(self, dmax):
            self._intgr_reso_low = dmax
            return
      
    return MosflmRWrapper()

if __name__ == '__main__':

    # run a demo test

    if not os.environ.has_key('XIA2_ROOT'):
        raise RuntimeError, 'XIA2_ROOT not defined'

    m = MosflmR()
    directory = os.path.join(os.environ['XIA2_ROOT'],
                             'Data', 'Test', 'Images')

    # from Labelit
    m.set_beam((108.9, 105.0))

    m.setup_from_image(os.path.join(directory, '12287_1_E1_001.img'))

    # FIXME 16/AUG/06 this should be set automatically - there is no
    # reason to manually specify the images

    m.add_indexer_image_wedge(1)
    m.add_indexer_image_wedge(90)
    # m.set_indexer_input_lattice('aP')

    # to test the awkward indexing problems -
    # this is not the default solution
    
    # m.set_indexer_input_lattice('mP')
    # m.set_indexer_input_cell((51.72, 51.66, 157.89, 90.00, 90.00, 90.00))

    print 'Refined beam is: %6.2f %6.2f' % m.get_indexer_beam()
    print 'Distance:        %6.2f' % m.get_indexer_distance()
    print 'Cell: %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % m.get_indexer_cell()
    print 'Lattice: %s' % m.get_indexer_lattice()
    print 'Mosaic: %6.2f' % m.get_indexer_mosaic()

    print 'Matrix:'
    for l in m.get_indexer_payload('mosflm_orientation_matrix'):
        print l[:-1]

    # generate BEST files

    m.generate_best_files(m, [1, 90])

if False:

    n = Mosflm()
    n.setup_from_image(os.path.join(directory, '12287_1_E1_001.img'))
    n.set_integrater_indexer(m)

    n.integrate()

    print 'Refined beam is: %6.2f %6.2f' % n.get_indexer_beam()
    print 'Distance:        %6.2f' % n.get_indexer_distance()
    print 'Cell: %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % n.get_indexer_cell()
    print 'Lattice: %s' % n.get_indexer_lattice()
    print 'Mosaic: %6.2f' % n.get_indexer_mosaic()

    print 'Matrix:'
    for l in n.get_indexer_payload('mosflm_orientation_matrix'):
        print l[:-1]

