#!/usr/bin/env python
# Scaleit.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.


#
# 27th October 2006
#
# A wrapper for the CCP4 program scaleit, for use when scaling together
# multiple data sets from a single crystal.
# 

import os
import sys

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                                 'Python'))

from Driver.DriverFactory import DriverFactory
from Decorators.DecoratorFactory import DecoratorFactory

# locally required wrappers

from Mtzdump import Mtzdump

# example input...
# scaleit hklin foo hklout bar
# nowt
# converge ncyc 4
# converge abs 0.001
# converge tolr -7
# refine anisotropic wilson
# auto
# labin FP=FP_first etc then FPH1 ... DPH1=DANO1 and SIGDPH1=SIGDANO1 etc.
# end
#
# then lots of interesting output will follow - most interestingly the
# overall scale and B factors...

def Scaleit(DriverType = None):
    '''A factory for ScaleitWrapper classes.'''

    DriverInstance = DriverFactory.Driver(DriverType)
    CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, 'ccp4')

    class ScaleitWrapper(CCP4DriverInstance.__class__):
        '''A wrapper for Scaleit, using the CCP4-ified Driver.'''

        def __init__(self):
            # generic things
            CCP4DriverInstance.__class__.__init__(self)
            self.set_executable('scaleit')



