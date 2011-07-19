#!/usr/bin/env python
# Format.py
#   Copyright (C) 2011 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# A top-level class to represent image formats which does little else but
# (i) establish an abstract class for what needs to be implemented and
# (ii) include the format registration code for any image formats which
# inherit from this. This will also contain links to the static methods
# from the X(component)Factories which will allow construction of e.g.
# goniometers etc. from the headers and hence a format specific factory.

import os
import sys

assert('XIA2_ROOT' in os.environ)

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

# first - import access to all of the factories that we will be needing

from Schema.XGoniometer import XGoniometerFactory
from Schema.XDetector import XDetectorFactory
from Schema.XBeam import XBeamFactory

from Registry import Registry

class _MetaFormat(type):
    '''A metaclass for the Format base class (and hence all format classes)
    to allow autoregistration of the class implementations.'''

    def __init__(self, name, bases, attributes):
        super(_MetaFormat, self).__init__(name, bases, attributes)

        Registry.add(self)

        return

class Format:
    '''A base class for the representation and interrogation of diffraction
    image formats, from which all classes for reading the header should be
    inherited. This includes: autoregistration of implementation classes,
    stubs which need to be overridden and links to static factory methods
    which will prove to be useful in other implementations.'''

    __metaclass__ = _MetaFormat

    def __init__(self):
        pass

    
