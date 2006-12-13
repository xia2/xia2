#!/usr/bin/env python
# Indexer.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
# 
# An interface for programs which perform indexing - this will handle
# all of the aspects of the interface which are common between indexing
# progtrams, and which must be presented in order to satisfy the contract
# for the indexer interface.
# 
# The following are considered to be critical for this class:
# 
# Images to index - optional this could be decided by the implementation
# Refined beam position
# Refined distance
# Mosaic spread
# 
# Input: ?Selected lattice?
# Input: ?Cell?
# Output: Selected lattice
# Output: Unit cell
# Output: Aux information - may include matrix files &c. This is going to
#         be in the "payload" and will be program specific.
# 
# Methods:
# 
# index() -> delegated to implementation._index()
#
# FIXED: getter methods should, if the results are NULL, initiate the index
#        process to allow pure constructor based (functional?) programming.
#        4/AUG/06 this is done.
# 
# Notes:
# 
# All properties of this class are prefixed with either indxr for protected
# things or Indexer for public things.
#
# Error Conditions:
# 
# A couple of conditions will give indexing errors -
# (1) if no solution matching the input was found
# (2) if the images were blank
# (3) if the indexing just failed (bad beam, etc.)
# 
# These need to be handled properly with helpful error messages.
# 
# FIXME 11/SEP/06 Also want to check that the resolution of the data is
#                 better than (say) 3.5A, because below that Mosflm has 
#                 trouble refining the cell etc. Could add a resolution 
#                 estimate to the output of Indexer, which could either
#                 invoke labelit.stats_distl or grep the results from 
#                 the Mosflm output...
#
#                 Look for record "99% have resolution less than"...
#                 or the resolution numbers in labelit.stats_distl.
#                 use best numbers of all images used in indexing.
#
# FIXED 23/OCT/06 interesting new feature - want to be able to handle
#                 storing all of the other solutions from indexing as
#                 well as the chosen one, and also want to be able to
#                 select the "best" solution in a more sensible manner...
#
#                 This means that the indexing should work as follows:
#
#                 - autoindex the diffraction pattern, allow the wrapper
#                   or the program to assert a correct solution
#                 - compare this correct solution against the highest symmetry
#                   acceptable solution, and if it is not (e.g. because
#                   something made a duff decision) then assert that the
#                   cell, lattice is the higher symmetry and repeat
#                 - record all possible indexing solutions somewhere
#                 - provide a mechanism to say "this indexing solution
#                   sucks" and repeat indexing with the next solution down
#
#                 Not trivial, but appropriate behaviour for an expert system!
#                 This will require an _IndexerHelper class or some such,
#                 to take over management of the list of possible lattices,
#                 solution selection & elimination of "duff" choices.
#
#                 This is now done and appears to work pretty well...
#
# FIXED 03/NOV/06 need to add the standard "interface" loop structure to
#                 the Indexer interface - move all of the image picking
#                 stuff to a prepare method and everything else to an
#                 index loop which will need to keep track of flags. This
#                 has been pushed by the new improved Labelit which screws 
#                 up on the beam centre selection...
# 
# FIXME 28/NOV/06 need to provide connnections so that the Indexer can 
#                 "discuss" with the scaler what the most suitable lattice
#                 is, e.g. including the pointgroup determination.
#                 Implement this through something like
#
#                 set_indexer_asserted_lattice('tP')
# 
#                                              => will reset if this is
#                                                 different (incompatible)
#                                                 but reasonable and 
#                                                 return True
#                                              => will do nothing if this
#                                                 is what we have already
#                                                 and return True
#                                              => will return False if
#                                                 already eliminated
#                                              => will raise exception if
#                                                 impossible *
# 
#                 this could work with the aid of set_indexer_input_lattice
#                 and the indexer helper get_all method (new.)
# 
#                 * actually it won't, because you cannot tell the difference
#                   between eliminated and impossible!
#
#                 Ok, this is now implemented so what I now need is a test
#                 case which will make use of this. Turns out that including
#                 the new unit cell is too tricky and shouldn't be needed
#                 anyway - removing...
#
#                 Update 05/DEC/06 actually this should return the resulting
#                 lattice if it is changed or "None" if it isn't happy with
#                 it - if something has changed we need to know, so that
#                 we can leave the scaling and return to the data reduction.

import os
import sys

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

from Handlers.Streams import Science

from Experts.LatticeExpert import SortLattices

class _IndexerHelper:
    '''A class to manage autoindexing results in a useful way, to ensure
    that the indexing solutions are properly managed, c/f TS01:1VR9.'''

    # FIXME 28/NOV/06 need to add a method in here to handle the
    # lattice assertions...

    def __init__(self, lattice_cell_dict):
        '''Initialise myself from a dictionary keyed by crystal lattice
        classes (e.g. tP) containing unit cells for these lattices.'''

        # transform them into a list

        list = [(k, lattice_cell_dict[k]) for k in lattice_cell_dict.keys()]

        # sort them on the symmetry, highest first

        self._sorted_list = SortLattices(list)

        return

    def get(self):
        '''Get the highest currently allowed lattice.'''

        return self._sorted_list[0]

    def get_all(self):
        '''Return a list of all allowed lattices, as [(lattice, cell)].'''

        return self._sorted_list

    def repr(self):
        '''Return a string representation.'''

        result = []

        for l in self._sorted_list:
            result.append('%s %s' % (l[0],
                                     '%6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % \
                                     l[1]))

        return result

    def eliminate(self):
        '''Eliminate the highest currently allowed lattice.'''

        if len(self._sorted_list) <= 1:
            raise RuntimeError, 'not enough lattices'

        Science.write('Eliminating indexing solution %s' % self.repr()[0])

        self._sorted_list = self._sorted_list[1:]

        return

class Indexer:
    '''A class interface to present autoindexing functionality in a standard
    way for all indexing programs. Note that this interface defines the
    contract - what the implementation actually does is a matter for the
    implementation.'''

    def __init__(self):

        # (optional) input gubbinzes
        self._indxr_images = []
        self._indxr_input_lattice = None
        self._indxr_input_cell = None

        # job management parameters
        self._indxr_done = False
        self._indxr_prepare_done = False
        
        # output items
        self._indxr_lattice = None
        self._indxr_cell = None

        # other possible indexing solutions - see 23/OCT/06 FIXME
        # has keys for each entry of cell, goodness for goodness of fit.
        self._indxr_other_lattice_cell = { }

        self._indxr_helper = None

        self._indxr_mosaic = None
        self._indxr_refined_beam = None
        self._indxr_refined_distance = None

        # error information
        self._indxr_error = None

        # extra indexing guff - a dictionary which the implementation
        # can store things in
        self._indxr_payload = { }

        # an idea of the resolution of the data
        self._indxr_resolution_estimate = 0.0

        return

    def _index(self):
        raise RuntimeError, 'overload me'

    def _index_prepare(self):
        raise RuntimeError, 'overload me'

    def _index_select_images(self):
        '''This is something the implementation needs to implement.
        For instance, Labelit & Mosflm work well with 2 frames 90
        degrees separated, d*TREK & XDS with a couple of wedges.'''

        raise RuntimeError, 'overload me'

    def set_indexer_prepare_done(self, done = True):
        self._indxr_prepare_done = done
        return
        
    def set_indexer_done(self, done = True):
        self._indxr_done = done
        return

    def get_indexer_prepare_done(self):
        return self._indxr_prepare_done

    def get_indexer_done(self):
        return self._indxr_done

    # FIXME 28/NOV/06 this is obsolete and should be removed
    
    def no_longer_index_select_images(self):
        '''Call the local implementation...'''

        # FIXME 03/NOV/06 this should be replaced with a call to something
        # like _index_prepare in a similar way to _integrate_prepare...

        self._index_select_images()

        # reset the indexer - we need to rerun to get updated
        # results - not sure if this helps, since this will only
        # be called when the images aren't set...
        
        self._indxr_done = False

        return 

    def eliminate(self):
        '''Eliminate the current solution for autoindexing.'''

        if not self._indxr_helper:
            raise RuntimeError, 'no indexing done yet'

        # remove the top indexing solution and reset the "done" flag - this
        # will mean that the next "get" will cause the indexing to be rerun.

        self._indxr_helper.eliminate()
        self._indxr_done = False

        return

    def _index(self):
        '''This is what the implementation needs to implement.'''

        raise RuntimeError, 'overload me'

    def index(self):

        # FIXME this should be moved to _index_prepare - and also the
        # flags for self._indxr_done, self._indxr_prepare_done
        # should be used, and this should be while loop-ified...

        while not self._indxr_done:
            while not self._indxr_prepare_done:
                self._indxr_prepare_done = True
                self._index_prepare()
                
            # if there is already a list of "known" spacegroups, select the
            # highest and try to index with this...

            # FIXME this needs to check the indexer helper...
            # if the index helper does not exist, then it should be created
            # and populated here, perhaps? then the highest solution picked
            # and if different to the selected one then this should be
            # reimposed and rerun.
            
            self._indxr_done = True

            if not self._indxr_helper:

                result = self._index()

                if not self._indxr_done:
                    Science.write('Looks like indexing failed - try again!')
                    continue

                solutions = { }
                for k in self._indxr_other_lattice_cell.keys():
                    solutions[k] = self._indxr_other_lattice_cell[k]['cell']

                self._indxr_helper = _IndexerHelper(solutions)

                solution = self._indxr_helper.get()
        
                # compare these against the final solution, if different then
                # rerun indexing - oh - no longer need to do this explicitly
                # since I can just set the indxr_done flag to False...

                if self._indxr_lattice != solution[0]:
                    Science.write('Rerunning indexing with target lattice %s' \
                                  % solution[0])
                    # self._indxr_input_lattice = solution[0]
                    # self._indxr_input_cell = solution[1]
                    # result = self._index()
                    self._indxr_done = False

            else:
                # rerun autoindexing with the best known current solution
            
                solution = self._indxr_helper.get()
                self._indxr_input_lattice = solution[0]
                self._indxr_input_cell = solution[1]
                result = self._index()
            
                # self._indxr_done = True

        Science.write('All possible indexing solutions:')
        for l in self._indxr_helper.repr():
            Science.write(l)

        # FIXME 23/OCT/06 at this stage I need to look at the list of
        # reasonable solutions and try to figure out if the indexing
        # program has picked the highest - if not, then constrain the
        # unit cell (need to implement this somewhere, sure it's
        # around!) then rerun the autoindexing (perhaps?) with this
        # new target - this means that we are always working from the
        # top downwards with these things. Once we decide somewhere
        # else (e.g. in cell refinement) that this cell is not appropriate
        # then we can eliminate it from the list, select the next
        # lower symmetry solution and continue. This solution is a
        # general one, so may be implemented in the general indexer
        # interface rather than in specific code...

        # write about this

        Science.write('Indexing solution:')
        Science.write('%s %s' % (self._indxr_lattice,
                                 '%6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % \
                                 self._indxr_cell))
        
        return result

    # setter methods for the input

    def add_indexer_image_wedge(self, image):
        '''Add some images for autoindexing (optional) input is a 2-tuple
        or an integer.'''

        if type(image) == type(()):
            self._indxr_images.append(image)
        if type(image) == type(1):
            self._indxr_images.append((image, image))

        # reset the indexer - we need to rerun to get updated
        # results
        self._indxr_done = False
        
        return

    def set_indexer_input_lattice(self, lattice):
        '''Set the input lattice for this indexing job. Exactly how this
        is handled depends on the implementation. FIXED decide on the
        format for the lattice. This will be say tP.'''

        self._indxr_input_lattice = lattice

        # reset the indexer - we need to rerun to get updated
        # results
        self._indxr_done = False

        return

    def set_indexer_input_cell(self, cell):
        '''Set the input unit cell (optional.)'''

        if not type(cell) == type(()):
            raise RuntimeError, 'cell must be a 6-tuple de floats'

        if len(cell) != 6:
            raise RuntimeError, 'cell must be a 6-tuple de floats'

        self._indxr_input_cell = tuple(map(float, cell))

        # reset the indexer - we need to rerun to get updated
        # results
        self._indxr_done = False

        return

    # getter methods for the output
    def get_indexer_cell(self):
        '''Get the selected unit cell.'''

        # if not already run, run
        if not self._indxr_done:
            self.index()

        return self._indxr_cell

    def get_indexer_lattice(self):
        '''Get the selected lattice as tP form.'''

        # if not already run, run
        if not self._indxr_done:
            self.index()

        return self._indxr_lattice

    def get_indexer_mosaic(self):
        '''Get the estimated mosaic spread in degrees.'''

        # if not already run, run
        if not self._indxr_done:
            self.index()

        return self._indxr_mosaic

    def get_indexer_distance(self):
        '''Get the refined distance.'''

        # if not already run, run
        if not self._indxr_done:
            self.index()

        return self._indxr_refined_distance

    def set_indexer_beam(self, beam):
        '''Set the beam centre.'''

        self._indxr_refined_beam = beam
        

    def get_indexer_beam(self):
        '''Get the refined beam.'''

        # if not already run, run
        if not self._indxr_done:
            self.index()

        return self._indxr_refined_beam

    def get_indexer_payload(self, this):
        '''Attempt to get something from the indexer payload.'''

        # if not already run, run
        if not self._indxr_done:
            self.index()

        return self._indxr_payload.get(this, None)

    def get_indexer_resolution(self):
        '''Get an estimate of the diffracting resolution.'''

        # if not already run, run
        if not self._indxr_done:
            self.index()

        return self._indxr_resolution_estimate       

    def set_indexer_payload(self, this, value):
        '''Set something in the payload.'''
        
        self._indxr_payload[this] = value
        
        return

    # new method to handle interaction with the pointgroup determination
    # much later on in the process - this allows a dialogue to be established.

    def set_indexer_asserted_lattice(self, asserted_lattice):
        '''Assert that this lattice is correct - if this is allowed (i.e.
        is in the helpers list of kosher lattices) then it will be enabled.
        If this is different to the current favourite then processing
        may ensue, otherwise nothing will happen, and True will be returned.
        If the asserted lattice is not in the current list then False will
        be returned and nothing will change.'''

        if not self._indxr_helper:
            raise RuntimeError, 'no indexing performed yet'

        all_lattices = self._indxr_helper.get_all()

        lattices = []

        for l in all_lattices:
            lattices.append(l[0])

        if not asserted_lattice in lattices:
            return 'impossible'

        # check if this is the top one - if so we don't need to
        # do anything

        if asserted_lattice == all_lattices[0][0]:
            return 'correct'

        # ok this means that we need to do something - work through
        # eliminating lattices until the "correct" one is found...

        while self._indxr_helper.get()[0] != asserted_lattice:
            self._indxr_helper.eliminate()
            self._indxr_done = False

        # ok by now everything should be ready for the recycling...

        return 'possible'

    # end of interface
