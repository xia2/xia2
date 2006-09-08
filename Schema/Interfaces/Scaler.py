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
# 
# Update 08/SEP/06
# ----------------
# 
# Factory for Integrater takes Indexer as argument. By analogy, a Scaler
# Factory will take one or more Integraters as input. These will then 
# allow the best scaler to be selected.
# 
# The scaling step should implicitly include scaling & reindexing to the 
# "standard" setting. This should raise an exception if the diferent sweeps
# have been integrated with different programs.
#
# In XModel terms, this will be available from:
# 
# XSweep - for characterization of a single sweep, looking for in sweep 
#          radiation damage, resolution limits & so on.
# XWavelength - for scaling together multiple passes which belong to the 
#               same wavelength, e.g. low and high resolution pass.
#               Also for looking for radiation damage.
# XCrystal - for scaling together all of the data measured for a given
#            crystal, e.g. multiwavelength, multi passes as for XWavelength,
#            looking for multi-set radiation damage. This is assumed to
#            provide the final reflection output.
#
# Note well: The XCrystal level scaling will also be responsible for producing
# the specialised data sets, e.g. for phasing & refinement. The former should
# optimise the "signal", while the latter should optimise the "resolution"
# and "quality" (this is to be assessed, for the moment think in terms of
# limiting radiation damage.)
#
# This will be most complicated, and will depend to a critical extent on the
# way in which the scaling is managed.
# 
# The scaling process should allow the following to be obtained:
# 
# merged reflections for phasing
# merged reflections for refinement
# unmerged reflections for phasing
# unmerged reflections for refinement
# r_merge
# r_pim
# resolution
# "anomalous signal/difference"
# "anomalous dispersion"
# twinning information (implies that Truncate will be included)
# 
# probably other things but they will have to wait.
# 
# As input, the following will be appropriate:
# 
# A managed list of Integrater implementations. These should be grouped
# into wavelengths &c. All must be integrated with a compatible unit cell.
# A resolution limit.
# Anomalous true, false.
# "standard" unit cell (optional)
# 
# Output formats:
# 
# The output will be available as MTZ, providing that the proper mtz hierarchy
# is available (need to make sure there is a way of providing this as input.) 
# Scalepack format files will be provided for unmerged. These will be named
# according to something which matches the MTZ hierarchy, e.g.
# crystal_dataset.sca.
# 
# Refinement data will be merged native.









