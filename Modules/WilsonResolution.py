#!/usr/bin/env python
# WilsonResolution.py
#   Copyright (C) 2008 STFC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 11/AUG/08
#
# A module for calculating the limit of diffraction of a crystal based only
# on the results of integration. This is not worrying about the agreement of 
# the measurements, simply about the I/sigma of individual observations.
# To calculate the resolution, the distance and wavelength are necessary,
# as well as the beam position.
# 
# This will use either a recent version of pointless to sum the partial
# reflections or a spell using sortmtz, scala and mtzdump. The latter
# if obviously more painful...
#
#



def sum_partials(hklin, hklout, working):
    '''Sum partial reflections from HKLIN to HKLOUT using either pointless
    or sortmtz, scala & mtzdump. Write into reflection file the following:

    h k l batch i sigi phi x y

    where x, y are pixel positions.'''

    
