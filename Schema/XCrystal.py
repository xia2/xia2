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
# 
# FIXME 11/SEP/06 This needs to represent:
#
#  BEGIN CRYSTAL 12847
#  
#  BEGIN AA_SEQUENCE
#  
#  MKVKKWVTQDFPMVEESATVRECLHRMRQYQTNECIVKDREGHFRGVVNKEDLLDLDLDSSVFNKVSLPD
#  FFVHEEDNITHALLLFLEHQEPYLPVVDEEMRLKGAVSLHDFLEALIEALAMDVPGIRFSVLLEDKPGEL
#  RKVVDALALSNINILSVITTRSGDGKREVLIKVDAVDEGTLIKLFESLGIKIESIEKEEGF
#  
#  END AA_SEQUENCE
#  
#  BEGIN WAVELENGTH NATIVE
#  WAVELENGTH 0.99187
#  END WAVELENGTH NATIVE
#  
#  BEGIN SWEEP NATIVE_HR
#  WAVELENGTH NATIVE
#
#  ... &c. ...

import os
import sys
import math

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

        if len(self._allowed_lattice_order) == 1:
            raise RuntimeError, 'out of lattices'

        self._allowed_lattice_order = self._allowed_lattice_order[1:]
        self.reset()

class _aa_sequence(Object):
    '''A versioned object to represent the amino acid sequence.'''

    def __init__(self, sequence):
        self._sequence = sequence
        return

    def set_sequence(self, sequence):
        self._sequence = sequence
        self.reset()
        return

    def get_sequence(self):
        return self._sequence

class _ha_info(Object):
    '''A versioned class to represent the heavy atom information.'''

    # FIXME in theory we could have > 1 of these to represent e.g. different
    # metal ions naturally present in the molecule, but for the moment
    # just think in terms of a single one (though couldn't hurt to
    # keep them in a list.)

    def __init__(self, atom, number_per_monomer = 0, number_total = 0):
        self._atom = atom
        self._number_per_monomer = number_per_monomer
        self._number_total = number_total
        return

    def set_number_per_monomer(self, number_per_monomer):
        self._number_per_monomer = number_per_monomer
        self.reset()
        return

    def set_number_total(self, number_total):
        self._number_total = number_total
        self.reset()
        return

    def get_atom(self):
        return self._atom

    def get_number_per_monomer(self):
        return self._number_per_monomer

    def get_number_total(self):
        return self._number_total

def _print_lattice(lattice):
    print 'Cell: %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % lattice['cell']
    print 'Number: %s     Lattice: %s' % (lattice['number'], 
                                          lattice['lattice'])

class XCrystal(Object):
    '''An object to maintain all of the information about a crystal. This
    will contain the experimental information in XWavelength objects,
    and also amino acid sequence, heavy atom information.'''

    def __init__(self, name):
        self._name = name

        # these should be populated with the objects defined above
        self._aa_sequence = None

        # note that I am making allowances for > 1 heavy atom class...
        self._ha_info = []

        self._wavelengths = { }
        self._lattice_manager = None

        return

    def set_lattice(self, lattice, cell):
        '''Configure the cell - if it is already set, then manage this
        carefully...'''

        # FIXME this should also verify that the cell for the provided
        # lattice exactly matches the limitations provided in IUCR
        # tables A.

        if self._lattice_manager:
            self._update_lattice(lattice, cell)
        else:
            self._lattice_manager = _lattice_manager(lattice, cell)

        return

    def _update_lattice(self, lattice, cell):
        '''Inspect the available lattices and see if this matches
        one of them...'''

        # FIXME need to think in here in terms of the lattice
        # being higher than the current one...
        # though that shouldn't happen, because if this is the
        # next processing, this should have taken the top
        # lattice supplied earler as input...

        while lattice != self._lattice_manager.get_lattice()['lattice']:
            self._lattice_manager.kill_lattice()

        # this should now point to the correct lattice class...
        # check that the unit cell matches reasonably well...

        cell_orig = self._lattice_manager.get_lattice()['cell']

        dist = 0.0

        for j in range(6):
            dist += math.fabs(cell_orig[j] - cell[j])

        # allow average of 1 degree, 1 angstrom
        if dist > 6.0:
            raise RuntimeError, 'new lattice incompatible: %s vs. %s' % \
                  ('[%6.2f, %6.2f, %6.2f, %6.2f, %6.2f, %6.2f]' % \
                   tuple(cell),
                   '[%6.2f, %6.2f, %6.2f, %6.2f, %6.2f, %6.2f]' % \
                   tuple(cell_orig))

        # if we reach here we're satisfied that the new lattice matches...
        # FIXME write out some messages here to Chatter.

        return

    def get_lattice(self):
        if self._lattice_manager:
            return self._lattice_manager.get_lattice()

        return None

if __name__ == '__main__':
    # lm = _lattice_manager('aP', (43.62, 52.27, 116.4, 103, 100.7, 90.03))
    # _print_lattice(lm.get_lattice())
    # lm.kill_lattice()
    # _print_lattice(lm.get_lattice())

    xc = XCrystal('DEMO')

    # this should configure with all possible lattices, though
    # I think going through an explicit "init lattices" would help...
    xc.set_lattice('aP', (43.62, 52.27, 116.4, 103, 100.7, 90.03))
    _print_lattice(xc.get_lattice())

    # this should "drop" the lattice by one - the idea here is
    # that this is the output from e.g. pointless updating the lattice
    # used for processing
    xc.set_lattice('mC', (228.70, 43.62, 52.27, 90.00, 103.20, 90.00))
    _print_lattice(xc.get_lattice())

    # this should raise an exception - the unit cell is not compatible
    xc.set_lattice('mC', (221.0, 44.0, 57.0, 90.0, 106.0, 90.0))
