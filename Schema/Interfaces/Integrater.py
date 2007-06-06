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
from Schema.Exceptions.IntegrationError import IntegrationError

# image header reading functionality
from Wrappers.XIA.Printheader import Printheader

# symmetry operator management functionality
from Experts.SymmetryExpert import compose_matrices_r, compose_symops

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

        # required parameters 
        self._intgr_wedge = None

        # logging parameters
        self._intgr_sweep_name = None

        # implementation dependent parameters - these should be keyed by
        # say 'mosflm':{'yscale':0.9999} etc.
        self._intgr_program_parameters = { }

        # the same, but for export to other instances of this interface
        self._intgr_export_program_parameters = { }

        # batches to integrate, batches which were integrated - this is
        # to allow programs like rebatch to work c/f self._intgr_wedge
        # note well that this may have to be implemented via mtzdump?
        # or just record the images which were integrated...
        self._intgr_batches_out = [0, 0]

        self._intgr_done = False
        self._intgr_prepare_done = False
        self._intgr_finish_done = False

        self._intgr_hklout = None

        # a place to store the project, crystal, wavelength, sweep information
        # to interface with the scaling...
        self._intgr_pname = None
        self._intgr_xname = None
        self._intgr_dname = None
        self._intgr_epoch = 0

        # places to store refined values of the cell parameters etc - this
        # is more for returning that for use, as it is assumed that the
        # implementation will handle that... also add the total number of
        # reflections...

        self._intgr_cell = None
        self._intgr_n_ref = None

        # FIXME adding this link may remove the need for many other
        # explicit pieces of information as they can be directly
        # linked to...
        self._intgr_sweep = None

        # Towards FIXME for 18/MAY/07 - need to also be able to store
        # reindexing matrix or operator, which will be provided by the
        # scaling stage (perhaps) and should be applied to the reflections
        # returned by the integrater. Should also be able to assign the
        # spacegroup in this circumstance (e.g. 75 for P4, ignoring screw
        # axes) as this will affect the indexing. This would also help
        # Mosflm as the Rsym values from the integration wouuld be more
        # meaningful if the pointgroup, not just the lattice, is corect.
        # Note that this is mostly to allow the inclusion of the XDS CORRECT
        # stage in the integrater...

        # all of these will be the result of feedback from a later
        # scaling step... the anomalous flag is needed to allow CORRECT
        # to separate, or not, the anomalous pairs.
        
        self._intgr_spacegroup_number = 0
        self._intgr_reindex_operator = None
        self._intgr_reindex_matrix = None
        self._intgr_anomalous = None
                
        return

    def _integrate_prepare(self):
        raise RuntimeError, 'overload me'

    def _integrate(self):
        raise RuntimeError, 'overload me'

    def _integrate_finish(self):
        raise RuntimeError, 'overload me'

    def _integrater_reset_callback(self):
        '''Overload this if you have other things which need to be reset.'''
        pass
    

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

        # also call back to a user defined function
        self._integrater_reset_callback()
    
    def set_integrater_sweep(self, sweep):
        self._intgr_sweep = sweep
        return

    def get_integrater_sweep(self):
        return self._intgr_sweep

    def set_integrater_sweep_name(self, sweep_name):
        self._intgr_sweep_name = sweep_name
        return

    def get_integrater_sweep_name(self):
        return self._intgr_sweep_name

    def set_integrater_prepare_done(self, done = True):
        self._intgr_prepare_done = done
        return
        
    def set_integrater_done(self, done = True):
        self._intgr_done = done
        return

    def set_integrater_finish_done(self, done = True):
        self._intgr_finish_done = done
        return

    def get_integrater_cell(self):
        '''Get the (post) refined unit cell.'''

        self.integrate()
        return self._intgr_cell

    def get_integrater_n_ref(self):
        '''Get the number of reflections in the data set.'''

        self.integrate()
        return self._intgr_n_ref

    def get_integrater_prepare_done(self):

        # if the indexer is not up-to-date then this can't possibly
        # be - feedback from scaling, this implements - likewise
        # below in next method.

        if not self.get_integrater_indexer():
            return self._intgr_prepare_done
        
        if not self.get_integrater_indexer().get_indexer_done() \
               and self._intgr_prepare_done:
            Chatter.write('Resetting integrater as indexer updated.')
            self._integrater_reset()
            
        return self._intgr_prepare_done

    def get_integrater_done(self):
        # should also check if prepare is up-to-date here...
        # the indexer check will be performed via cascade...
        if not self.get_integrater_prepare_done():
            self._intgr_done = False

        return self._intgr_done

    def get_integrater_finish_done(self):
        # check integrater done

        if not self.get_integrater_done():
            self._intgr_finish_done = False

        return self._intgr_finish_done

    def set_integrater_project_info(self,
                                    project_name,
                                    crystal_name,
                                    dataset_name):
        '''Set the metadata information, to allow passing on of information
        both into the reflection files (if possible) or to the scaling stages
        for dataset administration.'''

        # for mosflm, pname & dname can be used as part of the harvesting
        # interface, and should therefore end up in the mtz file?
        # add this as harvest pname [pname] dname [dname] and three separate
        # keywords...
        
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

        # FIXME update the epoch of the start of data collection
        # in here...
        # this will involve - get full file name from start, get header
        # from full file name, parse & pull out start date. this may be
        # NULL, in which case too bad!

        first_image_in_wedge = self.get_image_name(start)
        ph = Printheader()
        ph.set_image(first_image_in_wedge)
        header = ph.readheader()

        # only update the epoch if we (1) have a new value
        # and (2) do not have a user supplied value...
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

        # check that this indexer implements the Indexer interface
        if not inherits_from(indexer.__class__, 'Indexer'):
            raise RuntimeError, 'input %s is not an Indexer implementation' % \
                  indexer.__name__

        self._intgr_indexer = indexer

        self.set_integrater_prepare_done(False)
        self.set_integrater_done(False)
        return

    def integrate(self):
        '''Actually perform integration until we think we are done...'''

        # FIXED 20/OCT/06 need to be sure that this will work correctly...
        # FIXED could the repeated integration needed in Mosflm be entirely
        # handled from here??? Apparently yes!

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

                        # Should be all specific errors which indicate
                        # a known problem
                
                    except BadLatticeError, e:
                        Chatter.write('BadLattice! %s' % str(e))
                        self._intgr_indexer.eliminate()
                        self.set_integrater_prepare_done(False)

                    except IntegrationError, e:
                        Chatter.write('Integration! %s' % str(e))
                        self._intgr_indexer.eliminate()
                        self.set_integrater_prepare_done(False)
                    

                # FIXED 01/NOV/06 what happens if the integration decides
                # that the lattice is wrong - this would mean that the indexing
                # would be reperformed, which would in turn mean that the
                # preparation may need to be repeated...

                # aha - move the preparation "loop" inside integration loop,
                # so this can be implemented (this case could then reset the
                # intgr_prepare_done flag to False. DONE!

                # assert: this needs to behave exactly as it did before.

                Chatter.write('Doing some integration...')
            
                # assert that it is indeed done
                self.set_integrater_done(True)
            
                # but it may not be - if the integrate itself decides something
                # needs redoing

                try:

                    self._intgr_hklout = self._integrate()

                except BadLatticeError, e:
                    Chatter.write('Uh oh! %s' % str(e))
                    self._intgr_indexer.eliminate()
                    self.set_integrater_prepare_done(False)
                    self.set_integrater_done(False)

            # next the finish step - this may perform the reindexing (e.g.
            # with CCP4/Mosflm) or CORRECT in XDS.

            self.set_integrater_finish_done(True)
            self._integrate_finish()

        # ok, we are indeed "done"...
            
        return self._intgr_hklout
    
    def get_integrater_indexer(self):
        return self._intgr_indexer

    def get_integrater_reflections(self):
        # in here check if integration has already been performed, if
        # it has and everything is happy, just return the reflections,
        # else repeat the calculations.

        # if not self._intgr_done:

        self.integrate()

        return self._intgr_hklout
            
    def get_integrater_batches(self):
        # if not self._intgr_done:

        self.integrate()
        
        return self._intgr_batches_out

    # additional methods needed from FIXME of 18/MAY/07...
    # these are to do with inclusion of XDS, and therefore
    # more detailed feedback from scaling to CORRECT.
    # this information may be ignored by e.g. Mosflm which does
    # not care...

    def set_integrater_anomalous(self, anomalous):
        self._intgr_anomalous = anomalous
        return

    def get_integrater_anomalous(self):
        return self._intgr_anomalous

    # these methods which follow should probably be respected by
    # the Mosflm implementation of integrater

    def set_integrater_spacegroup_number(self, spacegroup_number):

        # check that this is compatible with the indexer's current
        # lattice, and if not raise an exception - or indeed should
        # this handle the eliminate guff?

        # this should also include a list of allowed spacegroup
        # numbers as they should, at best, define a point group.

        Debug.write('Set spacegroup as %d' % spacegroup_number)

        # FIXME need to check against the indexer that this is
        # appropriate...

        self.set_integrater_finish_done(False)        
        self._intgr_spacegroup_number = spacegroup_number
        return

    def get_integrater_spacegroup_number(self):
        return self._intgr_spacegroup_number
        
    def set_integrater_reindex_operator(self, reindex_operator):
        '''Assign a symmetry operator to the reflections - note
        that this is cumulative...'''

        reindex_operator = reindex_operator.lower().strip()

        if reindex_operator != 'h,k,l':
            self.set_integrater_finish_done(False)

        if self._intgr_reindex_operator is None:
            self._intgr_reindex_operator = reindex_operator
        else:
            
            # need to compose the two operations...

            old = self._intgr_reindex_operator
            new = compose_symops(reindex_operator, old)
            Debug.write('Composing %s and %s -> %s' % \
                        (old, reindex_operator, new))
            self._intgr_reindex_operator = new

        # allow a callback in case something wants to update itself...
        self._set_integrater_reindex_operator_callback()

        return

    def _set_integrater_reindex_operator_callback(self):
        pass

    def get_integrater_reindex_operator(self):
        return self._intgr_reindex_operator
        
    def set_integrater_reindex_matrix(self, reindex_matrix):

        # this is a sequence of 9 integers e.g. 1 0 0 0 1 0 0 0 1
        # which could come from e.g. pointless...

        # this is to ensure that the results from integration are
        # in a standard setting, and so it may be necessary that
        # the Mosflm implementation respects this through a call
        # to reindex. Note well that this is closely tied with the
        # pointgroup (set spacegroup number) above.

        # check to see if this is an identity...

        identity = True

        for i in range(3):
            for j in range(3):
                if i == j:
                    if math.fabs(reindex_matrix(3 * i + j) - 1) > 0.01:
                        identity = False
                else:
                    if math.fabs(reindex_matrix(3 * i + j)) > 0.01:
                        identity = False
                        
        if not identity:
            self.set_integrater_finish_done(False)

        if self._intgr_reindex_matrix is None:
            self._intgr_reindex_matrix = reindex_matrix

        else:
            # compose the two operations
            self._intgr_reindex_matrix = compose_matrices_r(
                reindex_matrix, self._intgr_reindex_matrix)

        # allow a callback in case something wants to update itself...
        self._set_integrater_reindex_matrix_callback()

        return

    def _set_integrater_reindex_matrix_callback(self):
        pass

    def get_integrater_reindex_matrix(self):
        return self._intgr_reindex_matrix
        
    # end additional methods 18/MAY/07
