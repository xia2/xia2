#!/usr/bin/env python
# XCrystal.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
#
# A versioning object representation of the toplevel crystal object,
# which presents much of the overall interface of xia2dpa to the 
# outside world.
# 
# This will contain some information about the sequence, some information
# about heavy atoms, some stuff about wavelengths. This will also, most
# substantially, contain some really important stuff to do with 
# managing the crystal lattice, for instance computing the correct
# "average" value and also handling lattice changes during the data
# reduction.
# 
# This latter function is delegated to a lower level object, the 
# lattice manager which is contained in this module.
# 
# This depends on:
# 
# DPA/Wrappers/CCP4/Othercell
# 
# FIXME 05/SEP/06 question - do I want to maintain a link to the unit cells
#                 of am I better off just handling the possible lattices and
#                 treating the unit cells as a separate problem? Maintaining
#                 the actual unit cell during processing may be complex -
#                 perhaps I am better off doing this after the event?

from Object import Object

class _lattice_manager(Object):
    '''A class to manage lattice representations.'''

    def __init__(self, index_lattice, index_cell):
        '''Initialise the whole system from the original indexing
        results.'''
        
        Object.__init__(self)

        self._allowed_lattices = { }
        self._allowed_lattice_order = []

        
        
