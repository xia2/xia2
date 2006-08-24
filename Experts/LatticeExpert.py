#!/usr/bin/env python
# LatticeExpert.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
# 
# 24th August 2006
# 
# An expert who knows all about lattices. This will handle the elimination
# of possible lattices as a result of:
# 
# - indexing
# - failed cell refinement
# - pointless
# - &c.
# 
# To give you what is left...
#

# Hard coded "expertise" - this is encoded by hand, because it is
# easier that way... or is it better to properly encode the
# symmetry constraints and calculate the rest from this? Quite possibly.
#
# Hmm.. perhaps an option here is to interrogate the ccp4 symmetry
# library in the usual way, to make these decisions based on subgroups.
# Subgroups could be defined by symmetry operators - would that make
# sense? This is making use of a mapping between lattice and most-simple
# spacegroup for that lattice... need to check if this is valid & behaves
# as expected...

allowed_lattices = ['aP', 'mP', 'mC', 'oP', 'oC', 'oI',
                    'oF', 'tP', 'tI', 'hR', 'hP', 'cP',
                    'cI', 'cF']

# How to do this:
# 
# (1) read all spacegroups, symmetries from symop.lib
# (2) for each symmetry element, pass through symop2mat to get a
#     numberical representation
# (3) draw a tree of subgroups & supergroups
# 
# Then see if this matches up what I would expect from the lattice
# symmetry constraints for the simplest lattices.
# 
# Have to think about...
# 
# (1) making sure that only immediate subgroups are calculated, to 
#     give a proper tree structure
# (2) representing the final tree structure in a manner which is actually
#     useful





    
