#!/usr/bin/env python
# Object.py
# Maintained by G.Winter
# 12th June 2006
# 
# A root "object" from which all other objects should be derived. This
# will be used to ensure that all objects have timestamps (which define
# their validity) and can be properly sorted.
# 

import time
import random

class _ObjectTracker:
    
    def __init__(self):
        self._objects = []

    def add(self, object):
        '''Add an object to the tracker.'''
        self._objects.append(object)

    def list(self):
        '''List all of the objects we have created.'''
        for o in self._objects:
            print '%s (%s)' % (o, o.__class__.__name__)

    def __del__(self):
        # could do...
        # self.list()
        pass

ObjectTracker = _ObjectTracker()

class Object:
    '''The DPA root object.'''

    def __init__(self):
        '''Initialise the objects timestamp - adding a small random
        amount to prevent two objects having exactly the same timestamp.'''

        self._timestamp = time.time() + 0.01 * random.random()

        # default to timestamp as the only real identity
        self._identity_attributes = ['_timestamp']
        self._properties = { }

        # record this object in the tracker
        ObjectTracker.add(self)

        return

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        '''Generate a string representation based on the class ID and
        the identity list.'''

        id = '"%s" id:' % self.__class__.__name__
        for attribute in self._identity_attributes:
            id += ' %s=%s' % (attribute, str(getattr(self, attribute)))

        return id

    def __cmp__(self, other):
        '''Comparison function - will use the class name and anything
        in _identity attributes (for example the timestamp) to verify
        identity. If the classes are the same, base the
        comparison on the defined elements. If they are different,
        base the results on the timestamps.'''

        if self.__class__.__name__ != other.__class__.__name__:
            # then base the comparison entirely on the timestamps
            # raise RuntimeError, 'objects of different classes: %s vs. %s' % \
            # (self.__class__.__name__, other.__class__.__name__)
            # this is to allow things like if results < input: repeat
            # calculation

            if self._timestamp < other._timestamp:
                return -1
            if self._timestamp > other._timestamp:
                return 1

            return 0

        # work through the list in order - the first different attribute
        # is used to decide the ordering

        for attribute in self._identity_attributes:
            if getattr(self, attribute) < getattr(other, attribute):
                return -1
            if getattr(self, attribute) > getattr(other, attribute):
                return 1

        return 0

if __name__ == '__main__':

    o1 = Object()
    o2 = Object()

    if o1 == o2:
        raise RuntimeError, 'these should not be the same'

    ObjectTracker.list()
