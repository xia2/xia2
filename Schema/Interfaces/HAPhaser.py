#!/usr/bin/env python
# HAPhaser.py
#   Copyright (C) 2007 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# An interface to represent high level interaction with heavy atom phasing
# (particularly MAD and SAD) packages which will incorporate links to 
# interfaces for substructure determination, phase calculation and phase
# improvement but - this is critical - not *insist* that they are used.
# However, the links to heavy atom phasing from the XCrystal will be through
# this interface.
#
# This means for systems like shelxc/d/e where e does the phase calculation
# and improvement the details may be hidden. Likewise solve/resolve.
# This interface will take as input:
#
# - A scaler - which will have a list of possible spacegroups.
# - A spacegroup to test, if the enantiomorph-flattened list of spacegroups
#   has more than one possibility (will assume that the implementation can
#   decide between e.g. P41 and P43.)
# - Number and species of heavy atoms.
# - Wavelength metadata, anomalous scattering form factors and names.
# - Estimated solvent content.
#
# it is assumed that the names in the wavelength metadata will be enough to 
# identify the files provided by the scaler - either the files for separate
# wavelengths (e.g. .sca files) or columns within a complex, composite file
# (e.g. .mtz files.)
#
# The results will contain the following:
# 
# - Success or failure indication.
# - In the event of success:
# -- Improved, phased reflection files.
# -- Refined cordinates for heavy atoms.
# -- The correct spacegroup.
# 
# Decisions about success or failure will be left to the implementation, as
# that is very program-dependent. The selected form for the reflection
# files will also be left to the implementation.

import sys
import os

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from SubstructureFinder import SubstructureFinder
from PhaseComputer import PhaseComputer
from PhaseImprover import PhaseImprover

class HAPhaser(SubstructureFinder,
               PhaseComputer,
               PhaseImprover):
    '''A composite interface presenting all of the interfaces for substructure
    determination, phasing and density modification.'''

    def __init__(self):
        SubstructureFinder.__init__(self)
        PhaseComputer.__init__(self)
        PhaseImprover.__init__(self)

        # this will need no local variables - the working directory
        # stuff will be inherited from one of the ancestor classes,
        # while the job control stuff can be stitched together
        # by the implementation of this interface.

        return

    def _ha_phase(self):
        '''Do the phasing - overload this.'''

        raise RuntimeError, 'overload me'

    def ha_phase(self):
        '''Call the internal implementation.'''

        return self._ha_phase()


    

