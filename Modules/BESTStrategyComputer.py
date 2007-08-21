#!/usr/bin/env python
# BESTStrategyComputer.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 21st August 2007
#
# A strategy computer implementation which makes use of Mosflm (for
# integration) and BEST to perform strategy calculations. Also available
# will be Chooch, to analyse scans and decide if we should perform a MAD
# or SAD experiment, and also decide the wavelengths. If the scan is
# not available then we just need to know the atom and we should gun for a
# high remote SAD experiment.
#
# Actually this decision is probably best left to another entity which can
# "wrap" the beamline or analyse the scans etc.
# 
