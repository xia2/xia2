#!/usr/bin/env python
# XBeam.py
#   Copyright (C) 2011 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#  
# A model for the beam for the "updated experimental model" project documented
# in internal ticket #1555. This is not designed to be used outside of the 
# XSweep classes.

import math
import pycbf
from scitbx import matrix
from scitbx.math import r3_rotation_axis_and_angle_from_matrix

class XBeam:
    '''A class to represent the X-ray primary beam for a standard rotation
    geometry diffraction experiment. We assume (i) that the beam is
    monochromatic (ii) that the beam is reasonably parallel. In the first
    instance the only parameters are direction and wavelength, however over
    time the intention is to add polarization, size, divergence, transmission
    etc. Turns out we need the polarization plane and fraction in the first
    instance.'''

    def __init__(self, direction, polarization_fraction, polarization_plane,
                 wavelength):
        '''Initialize the beam model, with the direction of the beam (i.e.
        towards the source) given in the CBF coordinate frame and the
        wavelength in Angstroms.'''

        assert(len(direction) == 3)
        assert(len(polarization_plane) == 3)
        
        self._direction = matrix.col(direction)
        self._polarization_plane = matrix.col(polarization_plane)
        self._polarization_fraction = polarization_fraction
        self._wavelength = wavelength
        
        return

    def __repr__(self):
        '''Generate a useful-to-print representation.'''

        f_axis = '%6.3f %6.3f %6.3f\n'

        return f_axis % self._direction.elems + \
               f_axis % self._polarization_plane.elems + \
               '%.6f\n' % self._wavelength

    def get_direction(self):
        '''Get the beam direction.'''
        
        return self._direction.elems

    def get_direction_c(self):
        '''Get the beam direction as a cctbx vector.'''

        return self._direction

    def get_wavelength(self):
        '''Get the wavelength in Angstroms.'''

        return self._wavelength

class XBeamFactory:
    '''A factory class for beam objects, which encapsulate standard beam
    models. In cases where a full cbf desctiption is available this
    will be used, otherwise simplified descriptions can be applied.'''

    def __init__(self):
        pass

    @staticmethod
    def Simple(wavelength):
        '''Construct a beam object on the principle that the beam is aligned
        with the +z axis, as is quite normal. Also assume the beam has
        polarization fraction 0.999 and is polarized in the x-z plane.'''

        return XBeam((0.0, 0.0, 1.0), 0.999, (0.0, 1.0, 0.0), wavelength)

    @staticmethod
    def Complex(beam_direction, polarization_fraction,
                polarization_plane_normal, wavelength):
        '''Full access to the constructor for cases where we do know everything
        that we need...'''

        return XBeam(beam_direction, polarization_fraction,
                     polarization_plane_normal, wavelength)

    @staticmethod
    def imgCIF(cif_file):
        '''Initialize a detector model from an imgCIF file. N.B. the
        definition of the polarization plane is not completely helpful
        in this - it is the angle between the polarization plane and the
        +Y laboratory frame vector.'''

        d2r = math.pi / 180.0

        cbf_handle = pycbf.cbf_handle_struct()
        cbf_handle.read_file(cif_file, pycbf.MSG_DIGEST)

        cbf_handle.find_category('axis')

        # find record with equipment = source
        cbf_handle.find_column('equipment')
        cbf_handle.find_row('source')
        
        # then get the vector and offset from this
        direction = []
        
        for j in range(3):
            cbf_handle.find_column('vector[%d]' % (j + 1))
            direction.append(cbf_handle.get_doublevalue())

        # and the wavelength
        wavelength = cbf_handle.get_wavelength()

        # and information about the polarization - FIXME this should probably
        # be a rotation about the beam not about the Z axis.
        
        polar_fraction, polar_angle = cbf_handle.get_polarization()
        polar_plane_normal = (
            math.sin(polar_angle * d2r), math.cos(polar_angle * d2r), 0.0)
        
        return XBeam(direction, polar_fraction, polar_plane_normal, wavelength)

    @staticmethod
    def imgCIF_H(cbf_handle):
        '''Initialize a detector model from an imgCIF file. N.B. the
        definition of the polarization plane is not completely helpful
        in this - it is the angle between the polarization plane and the
        +Y laboratory frame vector. This example works from a cbf_handle,
        which is already configured.'''

        d2r = math.pi / 180.0

        cbf_handle.find_category('axis')

        # find record with equipment = source
        cbf_handle.find_column('equipment')
        cbf_handle.find_row('source')
        
        # then get the vector and offset from this
        direction = []
        
        for j in range(3):
            cbf_handle.find_column('vector[%d]' % (j + 1))
            direction.append(cbf_handle.get_doublevalue())

        # and the wavelength
        wavelength = cbf_handle.get_wavelength()

        # and information about the polarization - FIXME this should probably
        # be a rotation about the beam not about the Z axis.
        
        polar_fraction, polar_angle = cbf_handle.get_polarization()
        polar_plane_normal = (
            math.sin(polar_angle * d2r), math.cos(polar_angle * d2r), 0.0)
        
        return XBeam(direction, polar_fraction, polar_plane_normal, wavelength)

        
