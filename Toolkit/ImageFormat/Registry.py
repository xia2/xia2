#!/usr/bin/env python
# Registry.py
#   Copyright (C) 2011 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# A registry class to handle Format classes and provide lists of them when
# this is useful for i.e. identifying the best tool to read a given range 
# of image formats.

import os
import imp

from RegistryHelpers import InheritsFromFormat
from RegistryHelpers import LookForFormatClasses
from RegistryHelpers import LoadFormatClass

class _Registry:
    '''A class to handle all of the recognised image formats within xia2
    working towards the generalization project in #1555 and specifically
    to address the requirements in #1573.'''

    def __init__(self):
        '''Set myself up - N.B. this could trigger a directory search for
        different Format classes to auto-register them.'''

        self._formats = []

        return

    def setup(self):
        '''Look to import format defining modules from around the place -
        this will look in $XIA2_ROOT/Toolkit/ImageFormat and $HOME/.xia2/
        for files starting with Format and ending in .py to allow user
        extensibility.'''

        for format_class in LookForFormatClasses():
            LoadFormatClass(format_class)

        return

    def add(self, format):
        '''Register a new image format with the registry. N.B. to work
        this object must be inherited from the base Format class.'''

        assert(InheritsFromFormat(format))

        if not format in self._formats:
            self._formats.append(format)

        return

    def get(self):
        '''Get a list of image formats registered here.'''
        
        return tuple(self._formats)

    def find(self, image_file):
        '''More useful - find the best format handler in the registry for your
        image file. N.B. this is in principle a factory function.'''

        scores = []

        for format in self._formats:
            scores.append((format.understand(image_file), format))

        scores.sort()

        return scores[-1][1]

Registry = _Registry()
Registry.setup()

        
        
