#!/usr/bin/env python
# Scaler.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
#
# An interface for programs which do scaling - this will handle all of the
# input and output, delegating the actual implementation to a wrapper which
# implements this interface via inheritance.
# 
# This interface is designed to work with "high level" scaling, that
# is the case where all of the expertise about the scaling is delegated
# to the wrapper. 
# 
# The following cases need to be handled:
# 
# (1) multiple sweeps contributing to one wavelength of data (e.g.
#     1VR9 native data.)
# (2) multiple sweeps at different wavelengths for MAD data collection
#     (e.g. 1VR9 SeMet MAD data.)
#
# These cases need to be handled implicitly, which means that the collection
# order will have to be handled. A mechanism for separating out the data
# for different crystals will be needed, to allow the radiation damage
# handling stuff to do it's job.
#
# The overall data model will correspond to the CCP4 MTZ hierarchy, that
# is project/crystal/dataset. In this interface it is assumed that all
# data will correspond to a single project, since anything else is simply
# perverse!
# 
# Input data will take the form of handles to Integrater implementations, 
# which can provide the required data as and when it is asked for. At some
# point I will need to think about how to handle the issue that XSCALE does
# the best job of scaling data from XDS...
# 
# At least, I need to implement a mechanism for handling this. More effort
# is needed in the design of the Factories... Since this applies also for
# things like the Indexer in the xia2process implementation I should
# probably resolve this first.


