#!/usr/bin/env python
# Object.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 12th June 2006
# 
# A root "object" from which all other objects should be derived. This
# will be used to ensure that all objects have timestamps (which define
# their validity) and can be properly sorted.
# 
# FIXME 05/SEP/06 Two new features needed - one is a handle, so that you 
#                 can give an object a human readable name. The other
#                 if the ability to create read-only objects, that is 
#                 ones which cannot be changed once they have been set,
#                 where changes will result in an exception - e.g. 
#                 the user has said that the lattice is mC - the DPA
#                 thinks otherwise (that is, it is explicitly unhappy
#                 about the choice) the only option is then to exception.
# 
#                 Modelling this is going to require some care - for instance
#                 it will always be important to start at "the top" lattice-
#                 wise and work downwards, so that you can have something in
#                 the lattice management which will only raise an exception if
#                 the asserted lattice is lower or something.
# 
#                 Therefore add "_o_readonly" and "_o_handle" properties
#                 to the object, accessible through the constructor for
#                 the former and constructor or setter for the latter.
#                 No - set them only through the constructor.

import time
import random
import thread

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

    def __init__(self, o_handle = None, o_readonly = False):
        '''Initialise the objects timestamp - adding a small random
        amount to prevent two objects having exactly the same timestamp.
        For definitions of o_readonly, o_handle, see above in the
        FIXME for 05/SEP/06.'''

        self._timestamp = time.time() + 0.01 * random.random()

        self._o_handle = o_handle
        self._o_readonly = o_readonly

        # default to timestamp as the only real identity
        self._identity_attributes = ['_timestamp']
        self._properties = { }

        # record this object in the tracker
        ObjectTracker.add(self)

        # allow locking - this will be useful if threading is enabled.
        self._lock = thread.allocate_lock()

        # and implement a list to handle all of the "thoughts" that this
        # object has...

        self._stdout = []

        return

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        '''Generate a string representation based on the class ID and
        the identity list. Note that this can now also use the handle -
        FIXME this needs to be added to the representation.'''

        if self._o_handle:
            return self._o_handle

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

        # to allow comparison against None
        if other == None:
            return -1

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

    def reset(self):
        '''Reset the timestamp on this object to indicate that it
        has changed. If this is a readonly object, raise an exception.'''

        if self._o_readonly:
            raise RuntimeError, 'readonly object has been reset'

        self._timestamp = time.time() + 0.01 * random.random()
        return

    def lock(self):
        '''Lock this object so only one thread can use it.'''

        return self._lock.acquire()

    def unlock(self):
        '''Unlock this object to allow multiple threads to use it.'''

        return self._lock.release()

    def locked(self):
        '''See if this object is locked.'''

        return self._lock.locked()

    def write(self, string):
        '''Record a thought.'''

        self._stdout.append(string)
        return

    def readonly(self):
        return self._o_readonly

    def handle(self):
        return self._o_handle

if __name__ == '__main__':

    o1 = Object()
    o2 = Object()

    if o1 == o2:
        raise RuntimeError, 'these should not be the same'

    ObjectTracker.list()

    
