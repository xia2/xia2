#!/usr/bin/env python
# Integrater.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
# 
# An interface for programs which do integration - this will handle
# all of the input and output, delegating the actual processing to an
# implementation of this interfacing.
# 
# The following are considered critical: 
# 
# Input:
# An implementation of the indexer class.
# 
# Output:
# [processed reflections?]
#
# This is a complex problem to solve...
# 
# Assumptions & Assertions:
# 
# (1) Integration includes any cell and orientation refinement.
#     This should be handled under the prepare phase.
# (2) If there is no indexer implementation provided as input,
#     it's ok to go make one, or raise an exception (maybe.)
# 
# This means...
# 
# (1) That this needs to have the posibility of specifying images for
#     use in both cell refinement (as a list of wedges, similar to 
#     the indexer interface) and as a SINGLE WEDGE for use in integration.
# (2) This may default to a local implementation using the same program,
#     e.g. XDS or Mosflm - will not necessarily select the best one.
#     This is left to the implementation to sort out.
#
# Useful standard options:
# 
# Resolution limits (low, high)
# ?Gain? - can this be determined automatically
# ?Areas to exclude? - this may be a local problem e.g. for mosflm just exclude
#                      appropriate areas by detector class
#
# Error Conditions:
# 
# FIXED 25/AUG/06 need a way to get the output reflection file from this
#                 interface, so that it can be passed in to a scaler
#                 implementation for ... scaling.
# 
# FIXED 05/SEP/06 also need to make this more like the indexer interface,
#                 providing access to everything only through getters and
#                 setters - no action methods. the tracking & calculations
#                 must be performed explicitly... FIXED - access through
#                 integrate_get_reflections, though tracking is not yet
#                 implemented FIXED - it is now..
# 
# FIXED 06/SEP/06 need to replace integrate_set with set_integrater as per
#                 the indexer interface, likewise getters. Done.
# 
# FIXED 08/SEP/06 need to record the number of batches in each run, so that
#                 rebatch may be used to reassign batch numbers in multi-
#                 sweep scaling.
# 
#                 Also - need to be able to assign the range of images
#                 to integrate, in particular single images if I intend to
#                 bolt this into DNA. Also for people who record three
#                 wavelengths with the same image prefix, for instance.
#                 Done done done....
#
# FIXED 27/SEP/06 need to be able to pass integration parameters, e.g. GAIN,
#                 from one instance of Integrater to another - e.g. via some
#                 kind of export parameters/import parameters framework.
#                 Note well that this will be complicated by the need to
#                 make sure that those parameters are relevent.
# 
#                 This is complicated - I need to figure out how to get the 
#                 exported parameters to all of the other integrater instances
#                 which will make life rather complicated. Aha - need to key it
#                 in some global dictionary someplace by the current crystal
#                 identity, and switch it off if this is not available.
# 
# FIXED 20/OCT/06 need to be able to rerun integration as much as we like
#                 until everyone is happy with the results (e.g. a good
#                 resolution limit, sensible GAIN, etc. has been set.)
#                 This will mean that the cell refinement implementation
#                 for some programs may need to be separated off, so perhaps
#                 there should be a prepare_to_integrate method, which needs
#                 to be run once, followed by a "proper" integrate method,
#                 which will be run repeatedly...
#
#                 Implement this change - call prepare_to_integrate followed
#                 by integrate...
#
# FIXED 02/NOV/06 want to hide the "done" flags inside getter/setter methods.
#  
# FIXED 28/NOV/06 need to enable the connection between the Scaler and the
#                 Indexer to pass back and forth (discuss) pointgroup options.
#
# FIXME 18/MAY/07 need to be able to support feedback of options to the XDS 
#                 correct step, viz:
#                 (i)   reindex operator & matrix (both should be set)
#                 (ii)  pointgroup (e.g. spacegroup number, in consultation
#                       with the indexer)
#                 (iii) lattice, again in consultation with the indexer.
#
#                 examples for these are 1VK8 (TS02) 1VPJ (TS03) and BA0296.
#  
#                 This brings the need to move the reindexing operations in
#                 to the Integrater interface and therefore we need to add
#                 an extra "method" to this for integrater finish - think of
#                 it as the opposite to integrate prepare. Have also done this
#                 for the Indexer.

import os
import sys
import exceptions
import math

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

from lib.Guff import inherits_from
from Handlers.Streams import Chatter, Debug

from Schema.Exceptions.BadLatticeError import BadLatticeError

# image header reading functionality
from Wrappers.XIA.Diffdump import Diffdump

# symmetry operator management functionality
from Experts.SymmetryExpert import compose_matrices_r, compose_symops
from Experts.SymmetryExpert import symop_to_mat

class Integrater:
    '''An interface to present integration functionality in a similar
    way to the indexer interface.'''

    def __init__(self):

        # a pointer to an implementation of the indexer class from which
        # to get orientation (maybe) and unit cell, lattice (definately)
        self._intgr_indexer = None

        # optional parameters
        self._intgr_reso_high = 0.0
        self._intgr_reso_low = 0.0

        # anomalous separation may be important for e.g. CORRECT.
        self._intgr_anomalous = None

        # required parameters 
        self._intgr_wedge = None

        # implementation dependent parameters - these should be keyed by
        # say 'mosflm':{'yscale':0.9999} etc.
        self._intgr_program_parameters = { }

        # the same, but for export to other instances of this interface
        # via the .xinfo hierarchy
        self._intgr_export_program_parameters = { }

        # batches to integrate, batches which were integrated - this is
        # to allow programs like rebatch to work c/f self._intgr_wedge
        # note well that this may have to be implemented via mtzdump?
        # or just record the images which were integrated...
        self._intgr_batches_out = [0, 0]

        # flags which control how the execution is performed
        # in the main integrate() method below.
        self._intgr_done = False
        self._intgr_prepare_done = False
        self._intgr_finish_done = False

        # the output reflections
        self._intgr_hklout = None

        # a place to store the project, crystal, wavelength, sweep information
        # to interface with the scaling...
        self._intgr_epoch = 0
        self._intgr_pname = None
        self._intgr_xname = None
        self._intgr_dname = None
        self._intgr_sweep = None
        self._intgr_sweep_name = None

        # results - refined cell and number of reflections
        self._intgr_cell = None
        self._intgr_n_ref = None

        # reindexing operations etc. these will come from feedback
        # from the scaling to ensure that the setting is uniform
        self._intgr_spacegroup_number = 0
        self._intgr_reindex_operator = None
        self._intgr_reindex_matrix = None
                
        return

    # ------------------------------------------------------------------
    # These methods need to be overloaded by the actual implementation - 
    # they are all called from within the main integrate() method. The
    # roles of each of these could be as follows -
    #
    # prepare - prerefine the unit cell
    # integrate - measure the intensities of all reflections
    # finish - reindex these to the correct setting
    #
    # though this is just one interpretation...
    # ------------------------------------------------------------------

    def _integrate_prepare(self):
        raise RuntimeError, 'overload me'

    def _integrate(self):
        raise RuntimeError, 'overload me'

    def _integrate_finish(self):
        raise RuntimeError, 'overload me'

    # ------------------------------------
    # end methods which MUST be overloaded
    # ------------------------------------

    def _integrater_reset(self):
        '''Reset the integrater, e.g. if the autoindexing solution
        has changed.'''

        # reset the status flags
        self.set_integrater_prepare_done(False)
        self.set_integrater_done(False)        
        self.set_integrater_finish_done(False)        

        # reset the "knowledge" from the data
        # note well - if we have set a resolution limit
        # externally then this will have to be respected...
        self._intgr_reso_high = 0.0
        self._intgr_reso_low = 0.0
        self._intgr_hklout = None
        self._intgr_program_parameters = { }

        self._integrater_reset_callback()
        return
    
    def set_integrater_sweep(self, sweep):
        self._intgr_sweep = sweep
        self._integrater_reset()
        return

    def get_integrater_sweep(self):
        return self._intgr_sweep

    # setters and getters for the "done"-ness of different operations
    # note that this cascades

    def set_integrater_prepare_done(self, done = True):
        self._intgr_prepare_done = done
        if not done:
            self.set_integrater_done(False)
        return
        
    def set_integrater_done(self, done = True):
        self._intgr_done = done
        if not done:
            self.set_integrater_finish_done(False)
        return

    def set_integrater_finish_done(self, done = True):
        self._intgr_finish_done = done
        return

    # getters of the status - note how these cascade the get to ensure
    # that everything is up-to-date...

    def get_integrater_prepare_done(self):
        if not self.get_integrater_indexer():
            return self._intgr_prepare_done
        
        if not self.get_integrater_indexer().get_indexer_done() \
               and self._intgr_prepare_done:
            Debug.write('Resetting integrater as indexer updated.')
            self._integrater_reset()
            
        return self._intgr_prepare_done

    def get_integrater_done(self):

        if not self.get_integrater_prepare_done():
            Debug.write('Resetting integrater done as prepare not done')
            self.set_integrater_done(False)
        
        return self._intgr_done

    def get_integrater_finish_done(self):

        if not self.get_integrater_done():
            Debug.write(
                'Resetting integrater finish done as integrate not done')
            self.set_integrater_finish_done(False)
        
        return self._intgr_finish_done

    # end job control stuff - next getters for results

    def get_integrater_cell(self):
        '''Get the (post) refined unit cell.'''

        self.integrate()
        return self._intgr_cell

    def get_integrater_n_ref(self):
        '''Get the number of reflections in the data set.'''

        self.integrate()
        return self._intgr_n_ref

    # getters and setters of administrative information

    def set_integrater_sweep_name(self, sweep_name):
        self._intgr_sweep_name = sweep_name
        return

    def get_integrater_sweep_name(self):
        return self._intgr_sweep_name

    def set_integrater_project_info(self,
                                    project_name,
                                    crystal_name,
                                    dataset_name):
        '''Set the metadata information, to allow passing on of information
        both into the reflection files (if possible) or to the scaling stages
        for dataset administration.'''

        self._intgr_pname = project_name
        self._intgr_xname = crystal_name
        self._intgr_dname = dataset_name
        
        return

    def get_integrater_project_info(self):
        return self._intgr_pname, self._intgr_xname, self._intgr_dname

    def get_integrater_epoch(self):
        return self._intgr_epoch

    def set_integrater_epoch(self, epoch):
        self._intgr_epoch = epoch
        return

    def set_integrater_wedge(self, start, end):
        '''Set the wedge of images to process.'''
        
        self._intgr_wedge = (start, end)

        # get the epoch for the sweep if not already defined

        first_image_in_wedge = self.get_image_name(start)
        dd = Diffdump()
        dd.set_image(first_image_in_wedge)
        header = dd.readheader()

        if header['epoch'] > 0 and self._intgr_epoch == 0:
            self._intgr_epoch = int(header['epoch'])

        Chatter.write('Sweep epoch: %d' % self._intgr_epoch)
        
        self.set_integrater_done(False)
        
        return

    def get_integrater_resolution(self):
        '''Get both resolution limits, high then low.'''
        return self._intgr_reso_high, self._intgr_reso_low

    def get_integrater_high_resolution(self):
        return self._intgr_reso_high

    def set_integrater_resolution(self, dmin, dmax):
        '''Set both resolution limits.'''

        self._intgr_reso_high = min(dmin, dmax)
        self._intgr_reso_low = max(dmin, dmax)
        self.set_integrater_done(False)

        return

    def set_integrater_high_resolution(self, dmin):
        '''Set high resolution limit.'''

        self._intgr_reso_high = dmin
        self.set_integrater_done(False)
        return

    def set_integrater_low_resolution(self, dmax):
        '''Set low resolution limit.'''

        self._intgr_reso_low = dmax
        self.set_integrater_done(False)
        return

    # getters and setters for program specific parameters
    # => values kept in dictionary

    def set_integrater_parameter(self, program, parameter, value):
        '''Set an arbitrary parameter for the program specified to
        use in integration, e.g. the YSCALE or GAIN values in Mosflm.'''

        if not self._intgr_program_parameters.has_key(program):
            self._intgr_program_parameters[program] = { }

        self._intgr_program_parameters[program][parameter] = value
        return

    def get_integrater_parameter(self, program, parameter):
        '''Get a parameter value.'''

        try:
            return self._intgr_program_parameters[program][parameter]
        except:
            return None
        
    def get_integrater_parameters(self, program):
        '''Get all parameters and values.'''

        try:
            return self._intgr_program_parameters[program]
        except:
            return { }

    def set_integrater_parameters(self, parameters):
        '''Set all parameters and values.'''

        self._intgr_program_parameters = parameters
        self.set_integrater_done(False)

        return

    def set_integrater_export_parameter(self, program, parameter, value):
        '''Set an arbitrary parameter for the program specified to
        use in integration, e.g. the YSCALE or GAIN values in Mosflm.'''

        if not self._intgr_export_program_parameters.has_key(program):
            self._intgr_export_program_parameters[program] = { }

        self._intgr_export_program_parameters[program][parameter] = value
        return

    def get_integrater_export_parameter(self, program, parameter):
        '''Get a parameter value.'''

        try:
            return self._intgr_export_program_parameters[program][parameter]
        except:
            return None
        
    def get_integrater_export_parameters(self):
        '''Get all parameters and values.'''

        try:
            return self._intgr_export_program_parameters
        except:
            return { }

    def set_integrater_indexer(self, indexer):
        '''Set the indexer implementation to use for this integration.'''

        if not inherits_from(indexer.__class__, 'Indexer'):
            raise RuntimeError, 'input %s is not an Indexer implementation' % \
                  indexer.__name__

        self._intgr_indexer = indexer
        self.set_integrater_prepare_done(False)
        return

    def integrate(self):
        '''Actually perform integration until we think we are done...'''

        while not self.get_integrater_finish_done():
            while not self.get_integrater_done():

                while not self.get_integrater_prepare_done():

                    Chatter.write('Preparing to do some integration...')
                    self.set_integrater_prepare_done(True)

                    # if this raises an exception, perhaps the autoindexing
                    # solution has too high symmetry. if this the case, then
                    # perform a self._intgr_indexer.eliminate() - this should
                    # reset the indexing system

                    try:
                        self._integrate_prepare()

                    except BadLatticeError, e:
                        Chatter.write('BadLattice! %s' % str(e))
                        self._intgr_indexer.eliminate()
                        self.set_integrater_prepare_done(False)

                Chatter.write('Doing some integration...')
            
                self.set_integrater_done(True)

                try:

                    self._intgr_hklout = self._integrate()

                except BadLatticeError, e:
                    Chatter.write('Uh oh! %s' % str(e))
                    self._intgr_indexer.eliminate()
                    self.set_integrater_prepare_done(False)
                    self.set_integrater_done(False)

            self.set_integrater_finish_done(True)
            
            try:
                # allow for the fact that postrefinement may be used
                # to reject the lattice...
                
                self._integrate_finish()
                
            except BadLatticeError, e:
                Chatter.write('Uh oh! %s' % str(e))
                self._intgr_indexer.eliminate()
                self.set_integrater_prepare_done(False)
                self.set_integrater_done(False)
                self.set_integrater_finish_done(False)

        return self._intgr_hklout
    
    def get_integrater_indexer(self):
        return self._intgr_indexer

    def get_integrater_reflections(self):
        self.integrate()
        return self._intgr_hklout
            
    def get_integrater_batches(self):
        self.integrate()        
        return self._intgr_batches_out

    # Should anomalous pairs be treated separately? Implementations
    # of Integrater are free to ignore this.

    def set_integrater_anomalous(self, anomalous):
        self._intgr_anomalous = anomalous
        return

    def get_integrater_anomalous(self):
        return self._intgr_anomalous

    # these methods which follow should probably be respected by
    # the Mosflm implementation of integrater

    def set_integrater_spacegroup_number(self, spacegroup_number):
        # FIXME check that this is appropriate with what the
        # indexer things is currently correct. Also - should this
        # really just refer to a point group??

        Debug.write('Set spacegroup as %d' % spacegroup_number)

        self._intgr_spacegroup_number = spacegroup_number
        self.set_integrater_finish_done(False)        

        return

    def get_integrater_spacegroup_number(self):
        return self._intgr_spacegroup_number
        
    def set_integrater_reindex_operator(self, reindex_operator):
        '''Assign a symmetry operator to the reflections - note
        that this is cumulative...'''

        reindex_operator = reindex_operator.lower().strip()

        # see if we really need to do anything
        if reindex_operator == 'h,k,l' and \
           self._intgr_reindex_operator is None:
            return

        if reindex_operator == 'h,k,l' and \
           self._intgr_reindex_operator == 'h,k,l':
            return

        # ok we need to do something - either just record the new
        # operation or compose it with the existing operation

        self.set_integrater_finish_done(False)

        if self._intgr_reindex_operator is None:
            self._intgr_reindex_operator = reindex_operator
            
        else:            
            old_operator = self._intgr_reindex_operator
            self._intgr_reindex_operator = compose_symops(
                reindex_operator, old_operator)
            
            Debug.write('Composing %s and %s -> %s' % \
                        (old_operator, reindex_operator,
                         self._intgr_reindex_operator))

        # convert this to a 3x3 matrix form for e.g. XDS CORRECT
        self._intgr_reindex_matrix = symop_to_mat(
            self._intgr_reindex_operator)

        self._set_integrater_reindex_operator_callback()

        return

    def get_integrater_reindex_operator(self):
        return self._intgr_reindex_operator
        
    def get_integrater_reindex_matrix(self):
        return self._intgr_reindex_matrix
        
    # ------------------------------------------------
    # callback methods - overloading these is optional
    # ------------------------------------------------
    
    def _integrater_reset_callback(self):
        '''Overload this if you have other things which need to be reset.'''
        pass
    
    def _set_integrater_reindex_operator_callback(self):
        pass



