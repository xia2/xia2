#!/usr/bin/env python
# Autoindex.py
#
#   Copyright (C) 2013 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Autoindex from a prepared spot list, from a previous run of Findspots. This 
# needs to handle the cases where:
# 
# - unit cell / symmetry are unknown
# - unit cell / symmetry are known (or at least asserted)
#
# third case (symmetry known but unit cell not) will be handled at the higher
# level.

def Autoindex(DriverType = None):
    '''A factory for AutoindexWrapper(ipmosflm) classes.'''

    from Driver.DriverFactory import DriverFactory
    DriverInstance = DriverFactory.Driver(DriverType)

    class AutoindexWrapper(DriverInstance.__class__):

        def __init__(self):
            DriverInstance.__class__.__init__(self)

            from Handlers.Executables import Executables
            if Executables.get('ipmosflm'):
                self.set_executable(Executables.get('ipmosflm'))
            else:
                import os
                self.set_executable(os.path.join(
                    os.environ['CCP4'], 'bin', 'ipmosflm'))

            self._input_cell = None
            self._input_symmetry = None
            self._spot_file = None
                
            return

        def set_input_cell(self, input_cell):
            self._input_cell = input_cell
            return

        def set_input_symmetry(self, input_symmetry):
            self._input_symmetry = input_symmetry
            return

        def set_spot_file(self, spot_file):
            self._spot_file = spot_file
            return
        
        def __call__(self, fp, images):
            from Handlers.Streams import Debug

            images_str = ' '.join(map(str, images))
            
            if self._spot_file:
                Debug.write('Running mosflm to autoindex from %s' % 
                            self._spot_file)
            else:
                Debug.write('Running mosflm to autoindex from images %s' % 
                            images_str)
                    
            self.start()
            self.input('template "%s"' % fp.get_template())
            self.input('directory "%s"' % fp.get_directory())
            self.input('beam %f %f' % fp.get_beam())
            self.input('distance %f' % fp.get_distance())
            self.input('wavelength %f' % fp.get_wavelength())

            if spot_file:
                self.input('autoindex dps refine image %s file %s' % 
                           (images_str, spot_file))
            else:
                self.input('autoindex dps refine image %s' % images_str)
                
            self.input('go')
            self.close_wait()
        
    return AutoindexWrapper()
