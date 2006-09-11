#!/usr/bin/env python
# Mosflm.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
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

import os
import sys

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'
if not os.environ.has_key('DPA_ROOT'):
    raise RuntimeError, 'DPA_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                                 'Python'))
if not os.environ['DPA_ROOT'] in sys.path:
    sys.path.append(os.environ['DPA_ROOT'])

from Driver.DriverFactory import DriverFactory
from Decorators.DecoratorFactory import DecoratorFactory

# interfaces that this will present
from Schema.Interfaces.FrameProcessor import FrameProcessor
from Schema.Interfaces.Indexer import Indexer
from Schema.Interfaces.Integrater import Integrater

# output streams

from Handlers.Streams import Admin, Science, Status, Chatter

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

            # local parameters used in integration
            self._mosflm_rerun_integration = False

            return

        def _index_select_images(self):
            '''Select correct images based on image headers.'''

            # FIXME perhaps this should be somewhere central, because
            # LabelitScreen will share the same implementation

            phi_width = self.get_header_item('phi_width')
            images = self.get_matching_images()

            self.add_indexer_image_wedge(images[0])
            if int(90.0 / phi_width) in images:
                self.add_indexer_image_wedge(int(90.0 / phi_width))
            else:
                self.add_indexer_image_wedge(images[-1])

            return
                            
        def _index(self):
            '''Implement the indexer interface.'''

            self.reset()
            self.write_log_file('mosflm-index.log')

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

            self.start()

            self.input('template "%s"' % self.get_template())
            self.input('directory "%s"' % self.get_directory())
            self.input('newmat xiaindex.mat')

            if self.get_beam_prov() == 'user':
                self.input('beam %f %f' % self.get_beam())

            if self.get_wavelength_prov() == 'user':
                self.input('wavelength %f %f' % self.get_wavelength())

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

            if self._indxr_lattice != None:
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
                                         'cP':195,
                                         'cF':196,
                                         'cI':197}
                                     
                spacegroup_number = lattice_to_spacegroup[self._indxr_lattice]
                self.input('symmetry %d' % spacegroup_number)

            for i in _images:
                self.input('autoindex dps refine image %d' % i)

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
                if 'Symmetry:' in o:
                    self._indxr_lattice = o.split(':')[1].split()[0]
                    
                # in here I need to check if the mosaic spread estimation
                # has failed. If it has it is likely that the selected
                # lattice has too high symmetry, and the "next one down"
                # is needed

                if 'The mosaicity has been estimated' in o:
                    self._indxr_mosaic = float(o.split('>')[1].split()[0])

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

            # FIXME this needs to be picked up by the integrater
            # interface which uses this Indexer, if it's a mosflm
            # implementation
            
            self._indxr_payload['mosflm_integration_parameters'] = intgr_params
                                                                 
            self._indxr_payload['mosflm_orientation_matrix'] = open(
                'xiaindex.mat', 'r').readlines()

            return

        def _integrate(self, fast = False):
            '''Implement the integrater interface.'''

            # FIXME in here I want to be able to work "fast" or "slow"
            # if fast, ignore cell refinement (i.e. to get the pointless
            # output quickly.)

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

            if not fast:
                self.reset()
                self.write_log_file('mosflm-cellrefinement.log')
                self._mosflm_refine_cell()
                
            self.reset()
            self.write_log_file('mosflm-integration.log')
            hklout = self._mosflm_integrate()

            if self._mosflm_rerun_integration and not fast:
                # FIXME this needs to be passed to the admin stream
                # print 'Rerunning integration...'
	        self.reset()
                self.write_log_file('mosflm-reintegration.log')
                hklout = self._mosflm_integrate()

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

            # first select the images to use for cell refinement
            # if spacegroup >= 75 use one wedge of 2-3 * mosaic spread, min
            # 3 images, else use two wedges of this size as near as possible
            # to 90 degrees separated. However, is this reliable enough?
            # FIXME this needs to be established, in particular in the case
            # where the lattice is wrongly assigned

            # WARNING this will fail if phi width was 0 - should
            # never happen though

            phi_width = self.get_header_item('phi_width')
            min_images = max(3, int(2 * mosaic / phi_width))

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
            # cell refinement makes things better...

            if spacegroup_number >= 75:
                num_wedges = 1
            else:
                num_wedges = 2

            # next select what we need from the list...

            images = self.get_matching_images()

            if len(images) < num_wedges * min_images:
                raise RuntimeError, 'not enough images to refine unit cell'

            cell_ref_images = []
            cell_ref_images.append((images[0], images[min_images]))

            if num_wedges == 2:
                ideal_last = int(90.0 / phi_width) + min_images
                if ideal_last in images:
                    cell_ref_images.append((images[ideal_last - min_images],
                                            images[ideal_last]))
                else:
                    # there aren't 90 degrees of images
                    cell_ref_images.append((images[-min_images],
                                            images[-1]))

            # write the matrix file in xiaindex.mat

            f = open('xiaindex.mat', 'w')
            for m in matrix:
                f.write(m)
            f.close()

            # then start the cell refinement

            task = 'Refine cell from %d wedges' % len(cell_ref_images)

            self.set_task(task)

            self.start()

            self.input('template "%s"' % self.get_template())
            self.input('directory "%s"' % self.get_directory())

            self.input('matrix xiaindex.mat')
            self.input('newmat xiarefine.mat')

            self.input('beam %f %f' % beam)
            self.input('distance %f' % distance)

            # FIXED is this the correct form? - it is now.
            self.input('symmetry %s' % spacegroup_number)
            self.input('mosaic %f' % mosaic)

            # note well that the beam centre is coming from indexing so
            # should be already properly handled
            if self.get_wavelength_prov() == 'user':
                self.input('wavelength %f %f' % self.get_wavelength())

            # get all of the stored parameter values
            parameters = self.get_integrater_parameters('mosflm')
            self.input('!parameters from autoindex run')
            for p in parameters.keys():
                self.input('%s %s' % (p, str(parameters[p])))

            # set up the cell refinement
            self.input('postref multi segments %d' % len(cell_ref_images))
            for cri in cell_ref_images:
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
                # FIXME this should do something useful
                pass

            # if it succeeded then populate the indexer output (myself)
            # with the new information - this can then be used
            # transparently in the integration.

            # here I need to get the refined distance, mosaic spread, unit
            # cell and matrix - should also look the yscale and so on, as
            # well as the final rms deviation in phi and distance

            for i in range(len(output)):
                o = output[i]

                # look for "error" type problems
                if 'INACCURATE CELL PARAMETERS' in o:
                    # get the inaccurate cell parameters in question
                    parameters = output[i + 3].lower().split()

                    # and warn about them
                    Science.write(
                        'In cell refinement, the following cell parameters')
                    Science.write(
                        'have refined poorly:')
                    for p in parameters:
                        Science.write('    %s' % p)

                    # decide what to do about this...		    
                    # if this is all cell parameters, abort, else
		    # consider using more data...
                    Science.write(
                        'Integration will be aborted because of this.')

		    raise RuntimeError, 'cell refinement failed'

                # FIXME will these get lost if the indexer in question is
                # not this program...? Find out...
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
            self._indxr_run = True
            
            # shouldn't need this.. remember that Python deals in pointers!
            self.set_indexer_payload('mosflm_orientation_matrix', open(
                'xiarefine.mat', 'r').readlines())
            indxr.set_indexer_payload('mosflm_orientation_matrix', open(
                'xiarefine.mat', 'r').readlines())

            return 

        def _mosflm_integrate(self):
            '''Perform the actual integration, based on the results of the
            cell refinement or indexing (they have the equivalent form.)'''

            # self.reset()

            # the only way to get here is through the cell refinement,
            # unless we're trying to go fast - which means that we may
            # have to create an indexer if fast - if we're going slow
            # then this should have been done by the cel refinement
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
                                     'cP':195,
                                     'cF':196,
                                     'cI':197}
                                     
            spacegroup_number = lattice_to_spacegroup[lattice]

            images = self.get_matching_images()

            f = open('xiaintegrate.mat', 'w')
            for m in matrix:
                f.write(m)
            f.close()

            # then start the integration

            task = 'Integrate frames %d to %d' % (min(images),
                                                  max(images))

            self.set_task(task)

            self.start()

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
                self.input('wavelength %f %f' % self.get_wavelength())

            # get all of the stored parameter values
            parameters = self.get_integrater_parameters('mosflm')
            for p in parameters.keys():
                self.input('%s %s' % (p, str(parameters[p])))

            # check for resolution limits
            if self._intgr_reso_high > 0.0:
                self.input('resolution %f' % self._intgr_reso_high)

            # set up the integration
            self.input('postref fix all')
            self.input('separation close')
            if not self._intgr_wedge:
                self.input('process %d %d' % (min(images),
                                              max(images)))
            else:
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

            for i in range(len(output)):
                o = output[i]

                if 'ERROR IN DETECTOR GAIN' in o:
                    # look for the correct gain
                    for j in range(i, i + 10):
                        if output[j].split()[:2] == ['set', 'to']:
                            gain = float(output[j].split()[-1][:-1])
                            self.set_integrater_parameter('mosflm',
                                                         'gain',
                                                         gain)
                            # FIXME this needs to be written to the
                            # "science stream"
                            # print 'Correct gain: %f' % gain
                            # this is worth rerunning
                            self._mosflm_rerun_integration = True

                if 'WRITTEN OUTPUT MTZ FILE' in o:
                    self._mosflm_hklout = output[i + 1].split()[-1]

            return self._mosflm_hklout

    
    return MosflmWrapper()


if __name__ == '__main_old__':

    # run a demo test

    if not os.environ.has_key('DPA_ROOT'):
        raise RuntimeError, 'DPA_ROOT not defined'

    m = Mosflm()

    directory = os.path.join(os.environ['DPA_ROOT'],
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

    if not os.environ.has_key('DPA_ROOT'):
        raise RuntimeError, 'DPA_ROOT not defined'

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

