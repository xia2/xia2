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

import os, sys

if not os.environ.has_key('DPA_ROOT'):
    raise RuntimeError, 'DPA_ROOT not defined'

if not os.environ['DPA_ROOT'] in sys.path:
    sys.path.append(os.environ['DPA_ROOT'])

from Object import Object

from Wrappers.CCP4.Othercell import Othercell

def sort_o_dict(dict, metric):
    '''A generic sorter for dictionaries - will return the keys in
    the correct order for sorting by the input metric.'''
    result = []
    jiffy = []

    class sort_o_thing:
        def __init__(self, tag, guff):
            self.tag = tag
            for key in guff.keys():
                setattr(self, key, guff[key])
        
        def __cmp__(self, other):
            return getattr(self, metric) < getattr(other, metric)

    for key in dict.keys():
        jiffy.append(sort_o_thing(key, dict[key]))

    jiffy.sort()

    for j in jiffy:
        result.append(j.tag)

    return result

class _lattice_manager(Object):
    '''A class to manage lattice representations.'''

    def __init__(self, index_lattice, index_cell):
        '''Initialise the whole system from the original indexing
        results.'''
        
        Object.__init__(self)

        self._allowed_lattices = { }
        self._allowed_lattice_order = []
        
        o = Othercell()
        o.set_cell(index_cell)
        o.set_lattice(index_lattice[1])

        o.generate()

        self._allowed_lattices = o.get_possible_lattices()
        self._allowed_lattice_order = sort_o_dict(self._allowed_lattices,
                                                  'number')
        self._allowed_lattice_order.reverse()

    def get_lattice(self):
        return self._allowed_lattices[self._allowed_lattice_order[0]]

    def kill_lattice(self):
        # remove the top one from the list
        self._allowed_lattice_order = self._allowed_lattice_order[1:]
        self.reset()

def _print_lattice(lattice):
    print 'Cell: %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % lattice['cell']
    print 'Number: %s' % lattice['number']

if __name__ == '__main__':
    lm = _lattice_manager('aP', (43.62, 52.27, 116.4, 103, 100.7, 90.03))

    _print_lattice(lm.get_lattice())
    lm.kill_lattice()
    _print_lattice(lm.get_lattice())

    
        
