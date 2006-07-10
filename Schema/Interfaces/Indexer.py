#!/usr/bin/env python
# Indexer.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
# 
# An interface for programs which perform indexing - this will handle
# all of the aspects of the interface which are common between indexing
# progtrams, and which must be presented in order to satisfy the contract
# for the indexer interface.
# 
# The following are considered to be critical for this class:
# 
# Images to index
# Refined beam position
# Refined distance
# Mosaic spread
# 
# Input: Selected lattice
# Output: Selected lattice
# Output: Unit cell
# Output: Aux information - may include matrix files &c.
#
# Methods:
# 
# index() -> delegated to implementation._index()
# 
