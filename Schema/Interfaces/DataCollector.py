#!/usr/bin/env python
# DataCollector.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 8th May 2007
#
# An interface definition for an entity which will perform data collection - 
# this can either be a human being (e.g. they are told "collect this then
# press return") or a DNA-style BCM, or a program which controls a lab
# source..
#
# This will be closely coupled with the StrategyComputer.
#
# This will need the following information to collect each sweep:
# 
# wavelength (i.e. the lambda value of the XWavelength a sweep produced
#             by this will belong to? The latter is probably better.)
# directory and template for the image
# image number range (may be 1-1)
# distance
# phi width
# exposure time
#
# This should also be capable of issuing instructions to measure an
# energy scan, which may also be used by the strategy calculation, e.g. for
# identifying wavelengths for MAD/SAD experiments.
#
# 
