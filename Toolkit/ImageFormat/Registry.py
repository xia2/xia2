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

class _Registry:
    '''A class to handle all of the recognised image formats within xia2
    working towards the generalization project in #1555 and specifically
    to address the requirements in #1573.'''

    def __init__(self):
        self._formats = []
        return

    def add(self, format):
        '''Register a new image format with the registry.'''

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

    

        
            
        
        
