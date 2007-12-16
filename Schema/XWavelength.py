#!/usr/bin/env python
# XWavelength.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# A versioning object representing the wavelength level in the .xinfo
# hierarchy. This will include all of the methods for performing operations
# on a wavelength as well as stuff for integration with the rest of the
# .xinfo hierarchy.
# 
# The following are properties defined for an XWavelength object:
# 
# wavelength
# f_pr
# f_prpr
#
# However, these objects are not versioned, since they do not (in the current
# implementation) impact on the data reduction process. These are mostly
# passed through.
#
# FIXME 05/SEP/06 this also needs to be able to handle the information
#                 pertaining to the lattice, because it is critcial that
#                 all of the sweeps for a wavelength share the same
#                 lattice.
# 
# FIXME 05/SEP/06 also don't forget about ordering the sweeps in collection
#                 order for the data reduction, to make sure that we 
#                 reduce the least damaged data first.

from XSweep import XSweep

from Object import Object

class XWavelength(Object):
    '''An object representation of a wavelength, which will after data
    reduction correspond to an MTZ hierarchy dataset.'''

    def __init__(self, name, crystal, wavelength,
                 f_pr = 0.0, f_prpr = 0.0):
        '''Create a new wavelength named name, belonging to XCrystal object
        crystal, with wavelength and optionally f_pr, f_prpr assigned.'''

        Object.__init__(self)

        # check that the crystal is an XCrystal

        if not crystal.__class__.__name__ == 'XCrystal':
            pass

        # set up this object

        self._name = name
        self._crystal = crystal
        self._wavelength = wavelength
        self._f_pr = f_pr
        self._f_prpr = f_prpr
        
        # then create space to store things which are contained
        # in here - the sweeps

        self._sweeps = []

        return

    def __repr__(self):
        result = 'Wavelength name: %s\n' % self._name
        result += 'Wavelength %7.5f\n' % self._wavelength
        if self._f_pr != 0.0 and self._f_prpr != 0.0:
            result += 'F\', F\'\' = (%5.2f, %5.2f)\n' % (self._f_pr,
                                                         self._f_prpr)

        result += 'Sweeps:\n'
        for s in self._sweeps:
            result += '%s\n' % str(s)

        return result[:-1]

    def __str__(self):
        return self.__repr__()

    def get_wavelength(self):
        return self._wavelength

    def set_wavelength(self, wavelength):
        # FIXME 29/NOV/06 provide a facility to update this when it is
        # not provided in the .xinfo file - this will come from the
        # image header
        if self._wavelength != 0.0:
            raise RuntimeError, 'setting wavelength when already set'
        self._wavelength = wavelength
        return

    def get_f_pr(self):
        return self._f_pr

    def get_f_prpr(self):
        return self._f_prpr

    def get_crystal(self):
        return self._crystal

    def get_name(self):
        return self._name

    def get_all_image_names(self):
        '''Get a full list of all images in this wavelength...'''

        # for RD analysis ...

        result = []
        for sweep in self._sweeps:
            result.extend(sweep.get_all_image_names)
        return result

    def add_sweep(self, name, directory = None, image = None,
                  integrated_reflection_file = None,
                  beam = None, distance = None, resolution = None,
                  gain = 0.0, polarization = 0.0,
                  frames_to_process = None, epoch = 0):
        '''Add a sweep to this wavelength.'''

        self._sweeps.append(XSweep(name, self,
                                   directory = directory,
                                   image = image,
                                   integrated_reflection_file = \
                                   integrated_reflection_file,
                                   beam = beam,
                                   distance = distance,
                                   resolution = resolution,
                                   gain = gain,
                                   polarization = polarization,
                                   frames_to_process = frames_to_process,
                                   epoch = epoch))

        return

    def get_sweeps(self):
        return self._sweeps

    def _get_integraters(self):
        integraters = []
        for s in self._sweeps:
            integraters.append(s._get_integrater())

        return integraters
    
