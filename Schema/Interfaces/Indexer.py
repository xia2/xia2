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

import os
import sys

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

from Handlers.Streams import Debug, Chatter
from Handlers.Phil import PhilIndex

from Experts.LatticeExpert import SortLattices

class _IndexerHelper:
    '''A class to manage autoindexing results in a useful way, to ensure
    that the indexing solutions are properly managed, c/f TS01:1VR9.'''

    def __init__(self, lattice_cell_dict):
        '''Initialise myself from a dictionary keyed by crystal lattice
        classes (e.g. tP) containing unit cells for these lattices.'''

        # transform them into a list, then sort the solutions and
        # store the sorted version

        lattices = [(k, lattice_cell_dict[k])
                    for k in lattice_cell_dict.keys()]

        self._sorted_list = SortLattices(lattices)

        return

    def get(self):
        '''Get the highest currently allowed lattice.'''
        return self._sorted_list[0]

    def get_all(self):
        '''Return a list of all allowed lattices, as [(lattice, cell)].'''
        return self._sorted_list

    def repr(self):
        '''Return a string representation.'''

        return ['%s %s' % (l[0], '%6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % l[1])
                for l in self._sorted_list]

    def insert(self, lattice, cell):
        '''Insert a new solution, e.g. from some postprocessing from
        the indexer. N.B. this will be re-sorted.'''

        lattices = [(lattice, cell)]

        for l in self._sorted_list:
            lattices.append(l)

        self._sorted_list = SortLattices(lattices)
        return

    def eliminate(self, indxr_print = True):
        '''Eliminate the highest currently allowed lattice.'''

        if len(self._sorted_list) <= 1:
            raise RuntimeError, 'cannot eliminate only solution'

        if indxr_print:
            Chatter.write('Eliminating indexing solution:')
            Chatter.write(self.repr()[0])

        self._sorted_list = self._sorted_list[1:]

        return

class Indexer:
    '''A class interface to present autoindexing functionality in a standard
    way for all indexing programs. Note that this interface defines the
    contract - what the implementation actually does is a matter for the
    implementation.'''

    LATTICE_POSSIBLE = 'LATTICE_POSSIBLE'
    LATTICE_IMPOSSIBLE = 'LATTICE_IMPOSSIBLE'
    LATTICE_CORRECT = 'LATTICE_CORRECT'

    def __init__(self):

        # (optional) input parameters
        self._indxr_images = []
        self._indxr_input_lattice = None
        self._indxr_input_cell = None
        self._indxr_user_input_lattice = False

        # job management parameters
        self._indxr_done = False
        self._indxr_prepare_done = False
        self._indxr_finish_done = False
        self._indxr_sweep_name = None

        # links to where my data is coming from
        self._indxr_sweep = None

        # the helper to manage the solutions table
        self._indxr_helper = None

        # output items - best solution
        self._indxr_lattice = None
        self._indxr_cell = None

        # an idea of how icy the image is
        self._indxr_ice = 0

        # a place to store other plausible solutions - used
        # for populating the helper in the main index() method
        self._indxr_other_lattice_cell = { }

        # refined experimental parameters
        self._indxr_mosaic = None
        self._indxr_refined_beam = None
        self._indxr_refined_distance = None
        self._indxr_resolution_estimate = 0.0
        self._indxr_low_resolution = 0.0

        # spot list in an as yet to be defined standard reference frame
        self._indxr_spot_list = None

        # error information
        self._indxr_error = None

        # extra indexing guff - a dictionary which the implementation
        # can store things in
        self._indxr_payload = { }

        self._indxr_print = True

        self.LATTICE_CORRECT = Indexer.LATTICE_CORRECT
        self.LATTICE_POSSIBLE = Indexer.LATTICE_POSSIBLE
        self.LATTICE_IMPOSSIBLE = Indexer.LATTICE_IMPOSSIBLE

        return

    # ----------------------------------------------------------------
    # These are functions which will want to be overloaded for the
    # actual implementation - preparation may do things like gathering
    # spots on the images, index to perform the actual autoindexing
    # and then finish to do any finishing up you want... see the
    # method index() below for how these are used
    # ----------------------------------------------------------------

    def _index_prepare(self):
        '''Prepare to index, e.g. finding spots on the images.'''
        raise RuntimeError, 'overload me'

    def _index(self):
        '''Actually perform the autoindexing calculations.'''
        raise RuntimeError, 'overload me'

    def _index_finish(self):
        '''This may be a no-op if you have no use for it...'''
        pass

    # setters and getters of the status of the tasks - note that
    # these will cascade, so setting an early task not done will
    # set later tasks not done.

    def set_indexer_prepare_done(self, done = True):
        self._indxr_prepare_done = done

        if not done:
            self.set_indexer_done(False)

        return

    def set_indexer_done(self, done = True):
        self._indxr_done = done

        if not done:
            self.set_indexer_finish_done(False)

        return

    def set_indexer_finish_done(self, done = True):
        self._indxr_finish_done = done
        return

    def set_indexer_sweep(self, sweep):
        self._indxr_sweep = sweep
        return

    def get_indexer_sweep(self):
        return self._indxr_sweep

    def set_indexer_sweep_name(self, sweep_name):
        self._indxr_sweep_name = sweep_name
        return

    def get_indexer_sweep_name(self):
        return self._indxr_sweep_name

    # getters of the status - note well that these need to cascade
    # the status... note that for the prepare get there is no previous
    # step we could cascade to...

    def get_indexer_prepare_done(self):
        return self._indxr_prepare_done

    def get_indexer_done(self):

        if not self.get_indexer_prepare_done():
            Debug.write('Resetting indexer done as prepare not done')
            self.set_indexer_done(False)

        return self._indxr_done

    def get_indexer_finish_done(self):

        if not self.get_indexer_done():
            Debug.write(
                'Resetting indexer finish done as index not done')
            self.set_indexer_finish_done(False)

        return self._indxr_finish_done

    # ----------------------------------------------------------
    # "real" methods which actually do something interesting -
    # eliminate() will remove a solution from the indexing table
    # and reset the done, such that the next get() will return
    # the next solution down.
    # ----------------------------------------------------------

    def eliminate(self, indxr_print = True):
        '''Eliminate the current solution for autoindexing.'''

        if not self._indxr_helper:
            raise RuntimeError, 'no indexing done yet'

        # not allowed to eliminate a solution provided by the
        # user via set_indexer_lattice... - this is determined by
        # the fact that the set lattice has user = true as
        # an argument

        if self._indxr_user_input_lattice:
            raise RuntimeError, 'eliminating user supplied lattice'

        self._indxr_helper.eliminate(indxr_print = indxr_print)
        self.set_indexer_done(False)

        return

    def _indxr_replace(self, lattice, cell, indxr_print = True):
        '''Replace the highest symmetry in the solution table with this...
        Only use this method if you REALLY know what you are doing!'''

        self._indxr_helper.eliminate(indxr_print = indxr_print)
        self._indxr_helper.insert(lattice, cell)


    def index(self):

        while not self.get_indexer_finish_done():
            while not self.get_indexer_done():
                while not self.get_indexer_prepare_done():

                    # --------------
                    # call prepare()
                    # --------------

                    self.set_indexer_prepare_done(True)
                    self._index_prepare()

                # --------------------------------------------
                # then do the proper indexing - using the best
                # solution already stored if available (c/f
                # eliminate above)
                # --------------------------------------------

                self.set_indexer_done(True)

                template = self.get_indexer_sweep().get_template()

                if self._indxr_sweep_name:
                    if PhilIndex.params.xia2.settings.show_template:
                        Chatter.banner('Autoindexing %s (%s)' % \
                                       (self._indxr_sweep_name, template))
                    else:
                        Chatter.banner('Autoindexing %s' % \
                                       (self._indxr_sweep_name))


                if not self._indxr_helper:

                    result = self._index()

                    if not self._indxr_done:
                        Debug.write(
                            'Looks like indexing failed - try again!')
                        continue

                    solutions = { }
                    for k in self._indxr_other_lattice_cell.keys():
                        solutions[k] = self._indxr_other_lattice_cell[k][
                            'cell']

                    # create a helper for the indexer to manage solutions
                    self._indxr_helper = _IndexerHelper(solutions)

                    solution = self._indxr_helper.get()

                    # compare these against the final solution, if different
                    # reject solution and return - correct solution will
                    # be used next cycle

                    if self._indxr_lattice != solution[0] and \
                           not self._indxr_input_cell:
                        Debug.write(
                            'Rerunning indexing with target lattice %s' % \
                            solution[0])
                        self.set_indexer_done(False)

                else:
                    # rerun autoindexing with the best known current solution

                    solution = self._indxr_helper.get()
                    self._indxr_input_lattice = solution[0]
                    self._indxr_input_cell = solution[1]
                    result = self._index()

            # next finish up...

            self.set_indexer_finish_done(True)
            self._index_finish()

            if self._indxr_print:
                Chatter.write('All possible indexing solutions:')
                for l in self._indxr_helper.repr():
                    Chatter.write(l)

            # FIXED 23/OCT/06 at this stage I need to look at the list of
            # reasonable solutions and try to figure out if the indexing
            # program has picked the highest - if not, then constrain the
            # unit cell (need to implement this somewhere, sure it's
            # around!) then rerun the autoindexing (perhaps?) with this
            # new target - this means that we are always working from the
            # top downwards with these things. Once we decide somewhere
            # else (e.g. in cell refinement) that this cell isn't good
            # then we can eliminate it from the list, select the next
            # lower symmetry solution and continue. This solution is a
            # general one, so may be implemented in the general indexer
            # interface rather than in specific code...

            if self._indxr_print:
                Chatter.write('Indexing solution:')
                Chatter.write('%s %s' % (
                    self._indxr_lattice,
                    '%6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % \
                    self._indxr_cell))

        return

    # setter methods for the input - most of these will reset the
    # indexer in one way or another

    def add_indexer_image_wedge(self, image, reset = True):
        '''Add some images for autoindexing (optional) input is a 2-tuple
        or an integer.'''

        if type(image) == type(()):
            self._indxr_images.append(image)
        if type(image) == type(1):
            self._indxr_images.append((image, image))

        if reset:
            self.set_indexer_prepare_done(False)

        return

    def set_indexer_image_wedges(self, indexer_image_wedges, reset = True):
        '''Assign images to use for autoindexing, will clobber existing
        values. Use with interactive indexing...'''

        self._indxr_images = []

        for image in indexer_image_wedges:

            if type(image) == type(()):
                self._indxr_images.append(image)
            if type(image) == type(1):
                self._indxr_images.append((image, image))

        if reset:
            self.set_indexer_prepare_done(False)

        return

    def get_indexer_images(self):
        return self._indxr_images

    # these relate to propogation of the fact that this is user assigned ->
    # so if we try to eliminate raise an exception... must be coordinated
    # with lattice setting below

    def set_indexer_user_input_lattice(self, user):
        self._indxr_user_input_lattice = user
        return

    def get_indexer_user_input_lattice(self):
        return self._indxr_user_input_lattice

    def set_indexer_input_lattice(self, lattice):
        '''Set the input lattice for this indexing job. Exactly how this
        is handled depends on the implementation. FIXED decide on the
        format for the lattice. This will be say tP.'''

        self._indxr_input_lattice = lattice
        self.set_indexer_done(False)

        return

    def get_indexer_input_lattice(self):
        return self._indxr_input_lattice

    def set_indexer_input_cell(self, cell):
        '''Set the input unit cell (optional.)'''

        if not type(cell) == type(()):
            raise RuntimeError, 'cell must be a 6-tuple of floats'

        if len(cell) != 6:
            raise RuntimeError, 'cell must be a 6-tuple of floats'

        self._indxr_input_cell = tuple(map(float, cell))
        self.set_indexer_done(False)

        return

    # getter methods for the output - all of these will call index()
    # which will guarantee that the results are up to date (recall
    # while structure above)

    def get_indexer_cell(self):
        '''Get the selected unit cell.'''

        self.index()
        return self._indxr_cell

    def get_indexer_lattice(self):
        '''Get the selected lattice as tP form.'''

        self.index()
        return self._indxr_lattice

    def get_indexer_mosaic(self):
        '''Get the estimated mosaic spread in degrees.'''

        self.index()
        return self._indxr_mosaic

    def get_indexer_spot_list(self):
        '''Get the list of spots from autoindexing in the standard reference
        frame.'''

        self.index()
        return self._indxr_spot_list

    def get_indexer_ice(self):
        '''Get an idea of whether this is icy - 0, no - 1, yes.'''

        self.index()
        return self._indxr_ice

    def get_indexer_distance(self):
        '''Get the refined distance.'''

        self.index()
        return self._indxr_refined_distance

    def set_indexer_beam(self, beam):
        '''Set the beam centre.'''

        self._indxr_refined_beam = beam
        return

    def get_indexer_beam(self):
        '''Get the refined beam.'''

        self.index()
        return self._indxr_refined_beam

    def get_indexer_payload(self, this):
        '''Attempt to get something from the indexer payload.'''

        self.index()
        return self._indxr_payload.get(this, None)

    def get_indexer_resolution(self):
        '''Get an estimate of the diffracting resolution.'''

        self.index()
        return self._indxr_resolution_estimate

    def get_indexer_low_resolution(self):
        '''Get an estimate of the low resolution limit of the data.'''

        self.index()
        return self._indxr_low_resolution

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
        may ensue, otherwise nothing will happen.'''

        assert(self._indxr_helper)

        all_lattices = self._indxr_helper.get_all()

        if not asserted_lattice in [l[0] for l in all_lattices]:
            return self.LATTICE_IMPOSSIBLE

        # check if this is the top one - if so we don't need to
        # do anything

        if asserted_lattice == all_lattices[0][0]:
            return self.LATTICE_CORRECT

        # ok this means that we need to do something - work through
        # eliminating lattices until the "correct" one is found...

        while self._indxr_helper.get()[0] != asserted_lattice:
            self._indxr_helper.eliminate()
            self.set_indexer_done(False)

        return self.LATTICE_POSSIBLE
