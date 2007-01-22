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
# FIXME 23/AUG/06 If the mosaic spread is refined to a negative number
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
# FIXME 23/AUG/06 Yet another one, though this may apply more to a higher
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

import os
import sys

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
from Schema.Interfaces.Indexer import Indexer
from Schema.Interfaces.Integrater import Integrater

# output streams &c.

from Handlers.Streams import Admin, Science, Status, Chatter
from Handlers.Exception import DPAException

# helpers

from MosflmHelpers import _happy_integrate_lp, \
     _parse_mosflm_integration_output, decide_integration_resolution_limit, \
     _parse_mosflm_index_output

from Modules.GainEstimater import gain

from lib.Guff import auto_logfiler

def Mosflm(DriverType = None):
    '''A factory for MosflmWrapper classes.'''

    DriverInstance = DriverFactory.Driver(DriverType)
    CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, 'ccp4')

    class MosflmWrapper(CCP4DriverInstance.__class__,
                        FrameProcessor,
                        Indexer,
                        Integrater):
        '''A wrapper for Mosflm, using the CCP4-ified Driver.'''

        def __init__(self):
            # generic things
            CCP4DriverInstance.__class__.__init__(self)
            self.set_executable('ipmosflm')

            FrameProcessor.__init__(self)
            Indexer.__init__(self)
            Integrater.__init__(self)

            # local parameters used in cell refinement
            self._mosflm_cell_ref_images = None

            # local parameters used in integration
            self._mosflm_rerun_integration = False
            self._mosflm_hklout = ''

            self._gain = None

            return

        def _estimate_gain(self):
            '''Estimate a GAIN appropriate for reducing this set.'''

            if self._gain:
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

            self._gain = sum(gains) / len(gains)

            Chatter.write('Estimate gain of %5.2f' % self._gain)
            
            return
        
        def _index_prepare(self):
            # prepare to do some autoindexing
            
            if self._indxr_images == []:
                self._index_select_images()
            return

        def _index_select_images(self):
            '''Select correct images based on image headers.'''

            # FIXME perhaps this should be somewhere central, because
            # LabelitScreen will share the same implementation

            phi_width = self.get_header_item('phi_width')
            images = self.get_matching_images()

            # FIXME what to do if phi_width is 0.0? set it
            # to 1.0! This should be safe enough... though a warning
            # would not go amiss...

            if phi_width == 0.0:
                Chatter.write('Phi width 0.0? Assuming 1.0!')
                phi_width = 1.0

            self.add_indexer_image_wedge(images[0])
            if int(90.0 / phi_width) in images:
                self.add_indexer_image_wedge(int(90.0 / phi_width))
            else:
                self.add_indexer_image_wedge(images[-1])

            return

        def _refine_select_images(self, num_wedges, mosaic):
            '''Select images for cell refinement based on image headers.'''

            # first select the images to use for cell refinement
            # if spacegroup >= 75 use one wedge of 2-3 * mosaic spread, min
            # 3 images, else use two wedges of this size as near as possible
            # to 90 degrees separated. However, is this reliable enough?
            # FIXME this needs to be established, in particular in the case
            # where the lattice is wrongly assigned

            # WARNING this will fail if phi width was 0 - should
            # never happen though

            if num_wedges > 3:
                # allow a rerun later on, perhaps? c/f integrating TS01
                # where this failure is an indication that lattice != oI
                self._mosflm_cell_ref_images = None
                raise DPAException, 'cannot cope with more than 3 wedges'

            phi_width = self.get_header_item('phi_width')

            # FIXME what to do if phi_width is 0.0? set it
            # to 1.0! This should be safe enough... though a warning
            # would not go amiss...

            if phi_width == 0.0:
                Chatter.write('Phi width 0.0? Assuming 1.0!')
                phi_width = 1.0
            
            min_images = max(3, int(2 * mosaic / phi_width))
            
            # next select what we need from the list...

            images = self.get_matching_images()

            if len(images) < num_wedges * min_images:
                raise RuntimeError, 'not enough images to refine unit cell'

            cell_ref_images = []
            cell_ref_images.append((images[0], images[min_images - 1]))

            # FIXME 23/OCT/06 need to be able to cope with more than two
            # wedges - in this case have the spread evenly between 0 and
            # 90 degrees as that measures all of the required unit cell
            # vectors..

            if num_wedges == 2:
                ideal_last = int(90.0 / phi_width) + min_images
                if ideal_last in images:
                    cell_ref_images.append((images[ideal_last - min_images],
                                            images[ideal_last]))
                else:
                    # there aren't 90 degrees of images
                    cell_ref_images.append((images[-min_images],
                                            images[-1]))

            elif num_wedges == 3:
                ideal_middle = int(45.0 / phi_width) + min_images
                if ideal_middle in images:
                    cell_ref_images.append((images[ideal_middle - min_images],
                                            images[ideal_middle - 1]))
                else:
                    # there aren't 45 degrees of images
                    raise RuntimeError, \
                          'not enough data to do 3 wedge cell refinement'

                ideal_last = int(90.0 / phi_width) + min_images

                if ideal_last in images:
                    cell_ref_images.append((images[ideal_last - min_images],
                                            images[ideal_last]))
                else:
                    # there aren't 90 degrees of images
                    cell_ref_images.append((images[-min_images],
                                            images[-1]))
                

            return cell_ref_images
                            
        def _index(self):
            '''Implement the indexer interface.'''

            self.reset()

            _images = []
            for i in self._indxr_images:
                for j in i:
                    if not j in _images:
                        _images.append(j)
                    
            _images.sort()

            task = 'Autoindex from images:'

            for i in _images:
                task += ' %s' % self.get_image_name(i)

            self.set_task(task)

            auto_logfiler(self)
            self.start()

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

            if self._indxr_input_cell:
                self.input('cell %f %f %f %f %f %f' % \
                           self._indxr_input_cell)

            if self._indxr_input_lattice != None:
                lattice_to_spacegroup = {'aP':1,
                                         'mP':3,
                                         'mC':5,
                                         'oP':16,
                                         'oC':20,
                                         'oF':22,
                                         'oI':23,
                                         'tP':75,
                                         'tI':79,
                                         'hP':143,
                                         'hR':146,
                                         'cP':195,
                                         'cF':196,
                                         'cI':197}
                                     
                spacegroup_number = lattice_to_spacegroup[
                    self._indxr_input_lattice]
                self.input('symmetry %d' % spacegroup_number)

	    # FIXME 25/OCT/06 have found that a threshold of 10 works
            # better for TS01/LREM - need to make sure that this is 
            # generally applicable...
            for i in _images:
                self.input('autoindex dps refine image %d thresh 10' % i)

            self.input('mosaic estimate')
            self.input('go')

            self.close_wait()

            output = self.get_all_output()

            intgr_params = { }

            for o in output:
                if 'Final cell (after refinement)' in o:
                    self._indxr_cell = tuple(map(float, o.split()[-6:]))
                if 'Beam coordinates of' in o:
                    self._indxr_refined_beam = tuple(map(float, o.split(
                        )[-2:]))

                # FIXME this may not be there if this is a repeat indexing!
                if 'Symmetry:' in o:
                    self._indxr_lattice = o.split(':')[1].split()[0]

                # so we have to resort to this instead...
                if 'Refining solution #' in o:
                    spagnum = int(o.split(')')[0].split()[-1])
                    lattice_to_spacegroup = {'aP':1, 'mP':3, 'mC':5,
                                             'oP':16, 'oC':20, 'oF':22,
                                             'oI':23, 'tP':75, 'tI':79,
                                             'hP':143, 'hR':146,
                                             'cP':195, 'cF':196,
                                             'cI':197}

                    spacegroup_to_lattice = { }
                    for k in lattice_to_spacegroup.keys():
                        spacegroup_to_lattice[lattice_to_spacegroup[k]] = k
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
                    raise DPAException, 'mosaicity estimation failed'

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
                    Science.write('Resolution estimated to be %5.2f A' % \
                                  self._indxr_resolution_estimate)


            # look up other possible indexing solutions (not well - in
            # standard settings only!)

            self._indxr_other_lattice_cell = _parse_mosflm_index_output(
                output)

            # FIXME this needs to be picked up by the integrater
            # interface which uses this Indexer, if it's a mosflm
            # implementation
            
            self._indxr_payload['mosflm_integration_parameters'] = intgr_params
                                                                 
            self._indxr_payload['mosflm_orientation_matrix'] = open(
                os.path.join(self.get_working_directory(),
                             'xiaindex.mat'), 'r').readlines()

            return

        def _integrate_prepare(self):
            '''Prepare for integration - note that if there is a reason
            why this is needed to be run again, set self._intgr_prepare_done
            as False.'''

            # generate the gain if necessary
            self._estimate_gain()

            self.reset()
            auto_logfiler(self)
            self._mosflm_refine_cell()

            return

        def _integrate(self):
            '''Implement the integrater interface.'''

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
            self._mosflm_rerun_integration = False

            wd = self.get_working_directory()

            # if not fast:
            # self.reset()
            # auto_logfiler(self)
            # self._mosflm_refine_cell()
                
            self.reset()
            auto_logfiler(self)
            hklout = self._mosflm_integrate()

            # FIXME now ignoring the "fast" directive...

            if self._mosflm_rerun_integration:
                # make sure that this is run again...
                Chatter.write('Need to rerun the integration...')
                self.set_integrater_done(False)

            # if self._mosflm_rerun_integration and not fast:
            # FIXME this needs to be passed to the admin stream
            # print 'Rerunning integration...'
            # self.reset()
            # auto_logfiler(self)
            # hklout = self._mosflm_integrate()

            return hklout

        def _mosflm_refine_cell(self):
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
                    
            indxr.set_indexer_payload('mosflm_integration_params', None)

            # copy these into myself for later reference, if indexer
            # is not myself - everything else is copied via the
            # cell refinement process...

            if indxr != self:
                self.set_indexer_input_lattice(lattice)
                self.set_indexer_beam(beam)


            # here need to check the LATTICE - which will be
            # something like tP etc. FIXME how to cope when the
            # spacegroup has been explicitly stated?

            lattice_to_spacegroup = {'aP':1,
                                     'mP':3,
                                     'mC':5,
                                     'oP':16,
                                     'oC':20,
                                     'oF':22,
                                     'oI':23,
                                     'tP':75,
                                     'tI':79,
                                     'hP':143,
                                     'hR':146,
                                     'cP':195,
                                     'cF':196,
                                     'cI':197}
                                     
            spacegroup_number = lattice_to_spacegroup[lattice]

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
                    num_wedges, mosaic)

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

            self.input('gain %5.2f' % self._gain)

            self.input('template "%s"' % self.get_template())
            self.input('directory "%s"' % self.get_directory())

            self.input('matrix xiaindex-%s.mat' % lattice)
            self.input('newmat xiarefine.mat')

            self.input('beam %f %f' % beam)
            self.input('distance %f' % distance)

            # FIXED is this the correct form? - it is now.
            self.input('symmetry %s' % spacegroup_number)
            self.input('mosaic %f' % mosaic)

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
            self.input('refinement residual 10.0')

            # set up the cell refinement - allowing quite a lot of
            # refinement for tricky cases (e.g. 7.2 SRS insulin SAD
            # data collected on MAR IP)
            self.input('postref multi segments %d repeat 10' % \
                       len(self._mosflm_cell_ref_images))
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

            # how best to handle this, I don't know... could
            #
            # (1) raise an exception
            # (2) try to figure out the solution myself
            #
            # probably (1) is better, because this will allow the higher
            # level of intelligence to sort it out. don't worry too hard
            # about this in the initial version, since labelit indexing
            # is pretty damn robust.

            if not cell_refinement_ok:

                # in here try first to repair it, as described
                # in the inaccurate cell parameters block below...
                # in fact all errors should now be trapped below
                # so this section isn't a lot of use...

                # FIXME 06/DEC/06 is this appropriate???

                # raise DPAException, 'Cell refinement failed'

                pass

            # if it succeeded then populate the indexer output (myself)
            # with the new information - this can then be used
            # transparently in the integration.

            # here I need to get the refined distance, mosaic spread, unit
            # cell and matrix - should also look the yscale and so on, as
            # well as the final rms deviation in phi and distance

            # FIRST look for errors, and analysis stuff which may be
            # important...

            rmsd_range = None

            for i in range(len(output)):
                o = output[i]

                # FIXME 01/NOV/06 dump this stuff from the top (error trapping)
                # into a trap_cell_refinement_errors method which is called
                # before the rest of the output is parsed...

                # look for overall cell refinement failure
                if 'Processing will be aborted' in o:
                    raise RuntimeError, 'cell refinement failed'
                
                # look to store the rms deviations on a per-image basis
                # this may be used to decide what to do about "inaccurate
                # cell parameters" below...

                if 'Rms positional error (mm) as a function of' in o:
                    images = map(int, output[i + 1].split()[1:])
                    rms_values = { }
                    rms_values_last = []
                    j = i + 2
                    while output[j].split():
                        cycle = int(output[j].split()[1])
                        record = [output[j][k:k + 6] \
                                  for k in range(11, len(output[j]), 6)]

                        data = []
                        for r in record:
                            if r.strip():
                                data.append(r.strip())
                        record = data

                        try:
                            rms_values[cycle] = map(float,
                                                    record)
                            rms_values_last = map(float,
                                                  record)
                        except ValueError, e:
                            Chatter.write(
                                'Error parsing %s as floats' % \
                                output[j][12:])
                            
                        j += 1
                        
                    # by now we should have recorded everything so...print!
                    # Chatter.write('Final RMS deviations per image')
                    # for j in range(len(images)):
                    # Chatter.write('- %4d %5.3f' % (images[j],
                    # rms_values_last[j]))

                    if rms_values_last:
                        rmsd_range = max(rms_values_last), min(rms_values_last)
                    else:
                        # there must have been a bigger problem than this!
                        rmsd_range = 1.0, 1.0

                # look for "error" type problems
                if 'INACCURATE CELL PARAMETERS' in o:
                    
                    # get the inaccurate cell parameters in question
                    parameters = output[i + 3].lower().split()

                    # and the standard deviations - so we can decide
                    # if it really has failed

                    sd_record = output[i + 5].replace(
                        'A', ' ').replace(',', ' ').split()
                    sds = map(float, [sd_record[j] for j in range(1, 12, 2)])

                    Science.write('Standard deviations:')
                    Science.write('A     %4.2f  B     %4.2f  C     %4.2f' % \
                                  (tuple(sds[:3])))
                    Science.write('Alpha %4.2f  Beta  %4.2f  Gamma %4.2f' % \
                                  (tuple(sds[3:6])))
                                  
                    # FIXME 01/NOV/06 this needs to be toned down a little -
                    # perhaps looking at the relative error in the cell
                    # parameter, or a weighted "error" of the two combined,
                    # because this may give rise to an error: TS01 NATIVE LR
                    # failed in integration with this, because the error
                    # in a was > 0.1A in 228. Assert perhaps that the error
                    # should be less than 1.0e-3 * cell axis and less than
                    # 0.15A?

                    # inspect rmsd_range

                    if rmsd_range is None:
                        raise RuntimeError, 'no rms deviation information'

                    # interested if max > 2 * min... 2 - 1 / (2 + 1)= 1 / 3

                    large_rmsd_range = False

                    if ((rmsd_range[0] - rmsd_range[1]) /
                        (rmsd_range[0] + rmsd_range[1])) > 0.3333:
                        large_rmsd_range = True
                        Science.write(
                            'Large range in RMSD variation per image')

                    # and warn about them
                    Science.write(
                        'In cell refinement, the following cell parameters')
                    Science.write(
                        'have refined poorly:')
                    for p in parameters:
                        Science.write('... %s' % p)

                    # decide what to do about this...
                    # if this is all cell parameters, abort, else
		    # consider using more data...

                    # see how many wedges we are using - if it's 3 already
                    # then there is probably something more important
                    # wrong. If it is fewer than this then try again!

                    if len(self._mosflm_cell_ref_images) < 3:
                        # set this up to be more images
                        new_cell_ref_images = self._refine_select_images(
                            len(self._mosflm_cell_ref_images) + 1,
                            mosaic)
                        self._mosflm_cell_ref_images = new_cell_ref_images

                        # set a flag to say cell refinement needs rerunning
                        # c/f Integrator.py
                        self.set_integrater_prepare_done(False)

                        # tell the user what is going on

                        Science.write(
                            'Repeating cell refinement with more data.')

                        # don't update the indexer - the results could be
                        # wrong!

                        return

                    else:
                        if large_rmsd_range:

                            Science.write(
                                'Integration will be aborted because of this.')
                        
                            raise RuntimeError, 'cell refinement failed: ' + \
                                  'inaccurate cell parameters'
                        
                        Science.write(
                            'However, will continue to integration.')
                        

		if 'One or more cell parameters has changed by more' in o:
                    # this is a more severe example of the above problem...
                    Science.write(
                        'Cell refinement is unstable...')

                    # so decide what to do about it...

                    if len(self._mosflm_cell_ref_images) <= 3:
                        # set this up to be more images
                        new_cell_ref_images = self._refine_select_images(
                            len(self._mosflm_cell_ref_images) + 1,
                            mosaic)
                        self._mosflm_cell_ref_images = new_cell_ref_images

                        self.set_integrater_prepare_done(False)

                        Science.write(
                            'Repeating cell refinement with more data.')

                        return

                    else:

                        Science.write(
                            'Integration will be aborted because of this.')
                        
                        raise RuntimeError, 'cell refinement failed: ' + \
                              'unstable cell refinement'

                # other possible problems in the cell refinement - a
                # negative mosaic spread, for instance

                if 'Refined mosaic spread (excluding safety factor)' in o:
                    mosaic = float(o.split()[-1])
                    if mosaic < 0.0:
                        Science.write('Negative mosaic spread (%5.2f)' %
                                      mosaic)
                        # raise DPAException, 'negative refined mosaic spread'

                        if len(self._mosflm_cell_ref_images) <= 3:
                            # set this up to be more images
                            new_cell_ref_images = self._refine_select_images(
                                len(self._mosflm_cell_ref_images) + 1,
                                mosaic)
                            self._mosflm_cell_ref_images = new_cell_ref_images
                            
                            self.set_integrater_prepare_done(False)
                            
                            Science.write(
                                'Repeating cell refinement with more data.')

                            return

                        else:

                            Science.write(
                                'Integration will be aborted because of this.')
                        
                            raise RuntimeError, 'cell refinement failed: ' + \
                                  'negative mosaic spread'
                        

            # AFTER that, read the refined parameters
            
            for i in range(len(output)):
                o = output[i]

                # FIXME for all of these which follow - the refined values
                # for these parameters should only be stored if the cell
                # refinement were 100% successful - therefore gather
                # them up here and store them at the very end (e.g. once
                # success has been confirmed.) 01/NOV/06

                # FIXME will these get lost if the indexer in question is
                # not this program...? Find out... would be nice to write
                # this to Chatter too...
                
                if 'Refined cell' in o:
                    indxr._indxr_cell = tuple(map(float, o.split()[-6:]))
                    
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
            self._indxr_done = True
            
            # shouldn't need this.. remember that Python deals in pointers!
            self.set_indexer_payload('mosflm_orientation_matrix', open(
                os.path.join(self.get_working_directory(),
                             'xiarefine.mat'), 'r').readlines())
            indxr.set_indexer_payload('mosflm_orientation_matrix', open(
                os.path.join(self.get_working_directory(),
                             'xiarefine.mat'), 'r').readlines())

            return 

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
                    
            indxr.set_indexer_payload('mosflm_integration_params', None)

            # here need to check the LATTICE - which will be
            # something like tP etc. FIXME how to cope when the
            # spacegroup has been explicitly stated?

            lattice_to_spacegroup = {'aP':1,
                                     'mP':3,
                                     'mC':5,
                                     'oP':16,
                                     'oC':20,
                                     'oF':22,
                                     'oI':23,
                                     'tP':75,
                                     'tI':79,
                                     'hP':143,
                                     'hR':146,
                                     'cP':195,
                                     'cF':196,
                                     'cI':197}
                                     
            spacegroup_number = lattice_to_spacegroup[lattice]

            images = self.get_matching_images()

            f = open(os.path.join(self.get_working_directory(),
                                  'xiaintegrate.mat'), 'w')
            for m in matrix:
                f.write(m)
            f.close()

            # then start the integration

            task = 'Integrate frames %d to %d' % (min(images),
                                                  max(images))

            self.set_task(task)

            self.start()

            # if the integrater interface has the project, crystal, dataset
            # information available, pass this in to mosflm and also switch
            # on the harvesrng output. warning! if the harvesting is switched
            # on then this means that the files will all go to the same
            # place - for the moment move this to cwd.

            pname, xname, dname = self.get_integrater_project_information()

            if pname != None and xname != None and dname != None:
                Chatter.write('Harvesting: %s/%s/%s' % (pname, xname, dname))

                # harvest file name will be %s.mosflm_run_start_end % dname
            
                self.input('harvest on')
                self.input('pname %s' % pname)
                self.input('xname %s' % xname)
                self.input('dname %s' % dname)
                self.input('ucwd')

            self.input('template "%s"' % self.get_template())
            self.input('directory "%s"' % self.get_directory())

            self.input('matrix xiaintegrate.mat')

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

            self.input('gain %5.2f' % self._gain)

            # check for resolution limits
            if self._intgr_reso_high > 0.0:
                self.input('resolution %f' % self._intgr_reso_high)

            # set up the integration
            self.input('postref fix all')
            self.input('separation close')

            if not self._intgr_wedge:
                self.set_integrater_wedge(min(images),
                                          max(images))

            self.input('process %d %d' % self._intgr_wedge)
                
            self.input('go')

            # that should be everything 
            self.close_wait()

            # get the log file
            output = self.get_all_output()

            # look for things that we want to know...
            # that is, the output reflection file name, the updated
            # value for the gain (if present,) any warnings, errors,
            # or just interesting facts.

            integrated_images_first = 1.0e6
            integrated_images_last = -1.0e6

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
                            self.set_integrater_parameter('mosflm',
                                                          'gain',
                                                          gain)
                            self.set_integrater_export_parameter('mosflm',
                                                                 'gain',
                                                                 gain)
                            Science.write('GAIN found to be %f' % gain)

                            # this should probably override the input
                            self._gain = gain

                            self._mosflm_rerun_integration = True

                if 'Smoothed value for refined mosaic spread' in o:
                    mosaic = float(o.split()[-1])
                    if mosaic < 0.0:
                        raise RuntimeError, 'negative mosaic spread'

                if 'WRITTEN OUTPUT MTZ FILE' in o:
                    self._mosflm_hklout = os.path.join(
                        self.get_working_directory(),
                        output[i + 1].split()[-1])

                    Science.write('Integration output: %s' % \
                                  self._mosflm_hklout)

                if 'MOSFLM HAS TERMINATED EARLY' in o:
                    Chatter.write('Mosflm has failed in integration')
                    message = 'The input was:\n\n'
                    for input in self.get_all_input():
                        message += '  %s' % input
                    Chatter.write(message)
                    raise RuntimeError, \
                          'integration failed: reason unknown'

            self._intgr_batches_out = (integrated_images_first,
                                       integrated_images_last)

            Chatter.write('Processed batches %d to %d' % \
                          self._intgr_batches_out)

            # write the report for each image as .*-#$ to Chatter -
            # detailed report will be written automagically to science...

            spot_status = _happy_integrate_lp(
                _parse_mosflm_integration_output(output))

            # if we have not processed to a given resolution, fix
            # the limit for future reference

            if not self._intgr_reso_high:
                resolution = decide_integration_resolution_limit(output)
                self.set_integrater_high_resolution(resolution)
                Chatter.write('Set resolution limit: %5.2f' % resolution)
                
            Chatter.write('Integration status per image (60/record):')
            for chunk in [spot_status[i:i + 60] \
                          for i in range(0, len(spot_status), 60)]:
                Chatter.write(chunk)
            Chatter.write(
                '"o" => ok          "%" => iffy rmsd "!" => bad rmsd')
            Chatter.write(
                '"O" => overloaded  "#" => many bad  "." => blank') 

            return self._mosflm_hklout
    
    return MosflmWrapper()


if __name__ == '__main_old__':

    # run a demo test

    if not os.environ.has_key('XIA2_ROOT'):
        raise RuntimeError, 'XIA2_ROOT not defined'

    m = Mosflm()

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

    print 'Refined beam is: %6.2f %6.2f' % m.get_indexer_beam()
    print 'Distance:        %6.2f' % m.get_indexer_distance()
    print 'Cell: %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % m.get_indexer_cell()
    print 'Lattice: %s' % m.get_indexer_lattice()
    print 'Mosaic: %6.2f' % m.get_indexer_mosaic()

    print 'Matrix:'
    for l in m.get_indexer_payload('mosflm_orientation_matrix'):
        print l[:-1]

if __name__ == '__main__':

    # run a demo test

    if not os.environ.has_key('XIA2_ROOT'):
        raise RuntimeError, 'XIA2_ROOT not defined'

    m = Mosflm()

    directory = os.path.normpath(os.path.join('/', 'data', 'graeme', '12287'))

    # from Labelit
    m.set_beam((108.9, 105.0))

    m.setup_from_image(os.path.join(directory, '12287_1_E1_001.img'))

    # FIXME 16/AUG/06 this should be set automatically - there is no
    # reason to manually specify the images

    m.add_indexer_image_wedge(1)
    m.add_indexer_image_wedge(60)
    # m.set_indexer_input_lattice('aP')

    print 'Refined beam is: %6.2f %6.2f' % m.get_indexer_beam()
    print 'Distance:        %6.2f' % m.get_indexer_distance()
    print 'Cell: %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % m.get_indexer_cell()
    print 'Lattice: %s' % m.get_indexer_lattice()
    print 'Mosaic: %6.2f' % m.get_indexer_mosaic()

    print 'Matrix:'
    for l in m.get_indexer_payload('mosflm_orientation_matrix'):
        print l[:-1]

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

