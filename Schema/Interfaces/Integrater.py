#!/usr/bin/env python
# Integrater.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
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
# FIXME 25/AUG/06 need a way to get the output reflection file from this
#                 interface, so that it can be passed in to a scaler
#                 implementation for ... scaling.
# 
# FIXED 05/SEP/06 also need to make this more like the indexer interface,
#                 providing access to everything only through getters and
#                 setters - no action methods. the tracking & calculations
#                 must be performed explicitly... FIXED - access through
#                 integrate_get_reflections, though tracking is not yet
#                 implemented FIXME.
# 
# FIXED 06/SEP/06 need to replace integrate_set with set_integrater as per
#                 the indexer interface, likewise getters.
# 
# FIXME 08/SEP/06 need to record the number of batches in each run, so that
#                 rebatch may be used to reassign batch numbers in multi-
#                 sweep scaling.
# 
#                 Also - need to be able to assign the range of images
#                 to integrate, in particular single images if I intend to
#                 bolt this into DNA. Also for people who record three
#                 wavelengths with the same image prefix, for instance.

import os
import sys

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.environ['XIA2CORE_ROOT'] in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                                 'Python', 'Decorators'))

# this should go in a proper library someplace
from DecoratorHelper import inherits_from

if not os.environ.has_key('DPA_ROOT'):
    raise RuntimeError, 'DPA_ROOT not defined'

if not os.environ['DPA_ROOT'] in sys.path:
    sys.path.append(os.path.join(os.environ['DPA_ROOT']))

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

        # implementation dependent parameters - these should be keyed by
        # say 'mosflm':{'yscale':0.9999} etc.
        self._intgr_program_parameters = { }
        
        return

    def set_integrater_wedge(self, start, end):
        '''Set the wedge of images to process.'''
        
        self._intgr_wedge = (start, end)
        
        return

    def set_integrater_resolution(self, dmin, dmax):
        '''Set both resolution limits.'''

        self._intgr_reso_high = min(dmin, dmax)
        self._intgr_reso_low = max(dmin, dmax)
        return

    def set_integrater_high_resolution(self, dmin):
        '''Set high resolution limit.'''

        self._intgr_reso_high = dmin
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

    def set_integrater_indexer(self, indexer):
        '''Set the indexer implementation to use for this integration.'''

        # check that this indexer implements the Indexer interface
        if not inherits_from(indexer.__class__, 'Indexer'):
            raise RuntimeError, 'input %s is not an Indexer implementation' % \
                  indexer.__name__

        self._intgr_indexer = indexer

        return

    def get_integrater_indexer(self):
        return self._intgr_indexer

    def get_integrater_reflections(self, fast = False):
        # in here check if integration has already been performed, if
        # it has and everything is happy, just return the reflections,
        # else repeat the calculations.
        return self._integrate(fast)
            
