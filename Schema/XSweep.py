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
# lattice
#
#

import sys
import os

# we all inherit from Object
from Object import Object

# allow output
if not os.environ.has_key('DPA_ROOT'):
    raise RuntimeError, 'DPA_ROOT not defined'

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

class XSweep(Object):
    '''An object representation of the sweep.'''

    def __init__(self, name, wavelength, directory, image, beam = None,
                 resolution = None):
        '''Create a new sweep named name, belonging to XWavelength object
        wavelength, representing the images in directory starting with image,
        with beam centre optionally defined.'''

        self._name = name
        self._wavelength = wavelength
        self._directory = directory
        self._image = image

        # + derive template, list of images
        # + check the wavelength is an XWavelength object
        # + get the lattice - can this be a pointer, so that when
        #   this object updates lattice it is globally-for-this-crystal
        #   updated?

        resolution_handle = '%s RESOLUTION' % name

        self._beam = beam
        self._resolution = _resolution(resolution = resolution,
                                       o_handle = resolution_handle)

    def getResolution(self):
        return self._resolution.get()

    def setResolution(self, resolution):
        if not self._resolution.get():
            self._resolution.set(resolution)
        else:
            Chatter.write('%s already set' % self._resolution.handle())

if __name__ == '__main__':
    xs = XSweep('DEMO', None, None, None)

    xs.setResolution(1.6)
    

        
