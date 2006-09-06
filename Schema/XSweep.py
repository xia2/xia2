#!/usr/bin/env python
# XSweep.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
#  
# A versioning object representation of the sweep. This will include
# methods for handling the required actions which may be performed
# on a sweep, and will also include integration with the rest of the
# .xinfo hierarchy. 
# 
# The following properties are defined for sweep:
# 
# resolution
# 
# The following properties defined elsewhere impact in the definition
# of the sweep:
#
# lattice - contained in XCrystal, to levels above XSweep.
#
# FIXME this needs to be defined!
#
# Headnote 001: LatticeInfo & Stuff.
# 
# Ok, so this is complicated. The crystal lattice will apply to all sweeps
# measured from that crystal (*1) so that they should share the same
# orientation matrix. This means that this could best contain a pointer
# to an Indexer implementation. This can then decide what to do - for 
# instance, we want to make sure that the indexing is kept common. That
# would mean that Mosflm would do a better job for indexing second and
# subsequent sets than labelit, perhaps, since the matrix can be passed
# as input - though this will need to be communicated to the factory.
# 
# Index 1st sweep - store indexer pointer, pass info also to crystal. Next
# sweep will update this information at the top level, with the original
# Indexer still "watching". Next get() may trigger a recalculation.
# By the time the second sweep is analysed, the first should be pretty
# solidly sorted with the correct pointgroup &c.
# 
# The upshot of all of this is that this will maintain a link to the 
# indexer which was used, which need to keep an eye on the top level
# lattice, which in turn will be updated as a weighted average of
# Indexer results. Finally, the top level will maintain a more high-tech
# "Lattice handler" object, which can deal with lattice -- and lattice ++.
# 
# (*1) This assumes, of course, that the kappa information or whatever
#      is properly handled.
#
# Bugger - slight complication! Want to make sure that multiple sweeps
# in the same wavelength have "identical" unit cells (since the error
# on the wavelength should be small) which means that the XWavelength
# level also needs to be able to handle this kind of information. Note
# well - this is an old thought, since the overall crystal unit cell
# is a kind of average from the wavelengths, which is in turn a kind
# of average from all of the sweeps. Don't miss out the wavelength
# level.
# 
# This means that the lattice information will have to cascade up and
# down the tree, to make sure that everything is kept up-to-date. This
# should be no more difficult, just a little more complicated.

import sys
import os
import math

# we all inherit from Object
from Object import Object

# allow output
if not os.environ.has_key('DPA_ROOT'):
    raise RuntimeError, 'DPA_ROOT not defined'
if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.environ['DPA_ROOT'] in sys.path:
    sys.path.append(os.environ['DPA_ROOT'])

from Handlers.Streams import Chatter

# helper class definitions
# in _resolution, need to think about how a user defined resolution
# will be handled - should this be a readonly attribute?

class _resolution(Object):
    '''An object to represent resolution for the XSweep object.'''

    def __init__(self, resolution = None,
                 o_handle = None,
                 o_readonly = False):
        Object.__init__(self, o_handle, o_readonly)

        if not resolution is None:
            Chatter.write('%s set to %5.2f' % (self.handle(), resolution))
        self._resolution = resolution

        return

    def get(self):
        return self._resolution

    def set(self, resolution):
        self._resolution = resolution
        Chatter.write('%s set to %5.2f' % (self.handle(), resolution))
        self.reset()
        return

# Notes on XSweep
# 
# This points through wavelength to crystal, so the lattice information
# (in particular, the lattice class e.g. tP) will be kept in
# self.getWavelength().getCrystal().getLattice() - this itself will be 
# a versioning object, so should be tested for overdateness.
# 
# The only dynamic object property that this has is the resolution, which 
# may be set during processing or by the user. If it is set by the 
# user then this should be used and not updated. It should also only 
# be asserted once during processing => only update if currently None.

# Things which are needed to populate this object from the pointer to a
# single image.

from Experts.FindImages import image2template, find_matching_images, \
     template_directory_number2image, image2template_directory

# image header reading functionality
from Wrappers.XIA.Printheader import Printheader

# access to factory classes
import Modules.IndexerFactory

class XSweep(Object):
    '''An object representation of the sweep.'''

    def __init__(self, name, wavelength, directory, image, beam = None,
                 resolution = None):
        '''Create a new sweep named name, belonging to XWavelength object
        wavelength, representing the images in directory starting with image,
        with beam centre optionally defined.'''

        # + check the wavelength is an XWavelength object
        #   raise an exception if not...

        if not wavelength.__class__.__name__ == 'XWavelength':
            pass

        self._name = name
        self._wavelength = wavelength
        self._directory = directory
        self._image = image

        # + derive template, list of images

        self._template, self._directory = \
                        image2template_directory(os.path.join(directory,
                                                              image))

        self._images = find_matching_images(self._template,
                                            self._directory)

        # + read the image header information into here?
        #   or don't I need it? it would be useful for checking
        #   against wavelength.getWavelength() I guess to make
        #   sure that the plumbing is all sound.

        ph = Printheader()
        ph.setImage(os.path.join(directory, image))
        header = ph.readheader()

        # check that they match by closer than 0.0001A, if wavelength
        # is not None

        if not wavelength == None:
            if math.fabs(header['wavelength'] -
                         wavelength.getWavelength()) > 0.0001:
                raise RuntimeError, 'wavelength for sweep %s does not ' + \
                      'match wavelength %s' % (name, wavelength.getName())
            
        self._header = header

        # + get the lattice - can this be a pointer, so that when
        #   this object updates lattice it is globally-for-this-crystal
        #   updated? The lattice included directly in here includes an
        #   exact unit cell for data reduction, the crystal lattice
        #   contains an approximate unit cell which should be
        #   from the unit cells from all sweeps contained in the
        #   XCrystal. FIXME should I be using a LatticeInfo object
        #   in here? See what the Indexer interface produces. ALT:
        #   just provide an Indexer implementation "hook".
        #   See Headnote 001 above. See also _get_indexer,
        #   _get_integrater below.

        self._indexer = None
        self._integrater = None

        # I don't need this - it is equivalent to self.getWavelength(
        # ).getCrystal().getLattice()
        # self._crystal_lattice = None

        #   this means that this module will have to present largely the
        #   same interface as Indexer and Integrater so that the calls
        #   can be appropriately forwarded.

        # set up the resolution object

        resolution_handle = '%s RESOLUTION' % name
        self._resolution = _resolution(resolution = resolution,
                                       o_handle = resolution_handle)

        # finally configure the beam if set

        self._beam = beam
        return

    def get_resolution(self):
        return self._resolution.get()

    def set_resolution(self, resolution):
        if not self._resolution.get():
            self._resolution.set(resolution)
        # else:
        # Chatter.write('%s already set' % self._resolution.handle())

        return

    # Real "action" methods - note though that these should never be
    # run directly, only implicitly...

    # These methods will be delegated down to Indexer and Integrater
    # implementations, through the defined method names. This should
    # make life interesting!

    # Note well - to get this to do things, ask for the
    # integrate_get_reflection() - this will kickstart everything.

    def _get_indexer(self):
        '''Get my indexer, if set, else create a new one from the
        factory.'''

        if self._indexer = None:
            # FIXME the indexer factory should probably be able to
            # take self [this object] as input, to help with deciding
            # the most appropriate indexer to use... this will certainly
            # be the case for the integrater. Maintaining this link
            # will also help the system cope with updates (which
            # was going to be one of the big problems...)
            self._indexer = IndexerFactory.Indexer()
            
        return self._indexer

    def get_crystal_lattice(self):
        '''Get the parent crystal lattice pointer.'''
        try:
            latitce = self.get_wavelength().get_crystal().get_lattice()
        except:
            lattice = None

        return lattice
    

if __name__ == '__main__':

    directory = os.path.join(os.environ['DPA_ROOT'],
                             'Data', 'Test', 'Images')    
    image = '12287_1_E1_001.img'

    xs = XSweep('DEMO', None, directory, image)

    xs.set_resolution(1.6)

        
