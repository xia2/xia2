#!/usr/bin/env python
# XDSScaler.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 2nd January 2007
#
# This will provide the Scaler interface using just XDS - a hybrid including
# pointless &c. will be developed at a later stage.
#
# This will run XDS CORRECT and XSCALE.
#
# Process (based on CCP4 Scaler)
# 
# _scale_prepare:
# 
# gather sweep information
# [check integraters are xds]
# check sweep information
# generate reference set: pointless -> sort -> quick scale
# reindex all data to reference: pointless -> eliminate lattices-> pointless
# verify pointgroups
# ?return if lattice in integration too high?
# reindex, rebatch
# sort
# pointless (spacegroup)
#
# _scale:
# 
# decide resolution limits / wavelength
# ?return to integration?
# refine parameters of scaling
# record best resolution limit
# do scaling
# truncate
# standardise unit cell
# update all reflection files
# cad together 
# add freer flags
# 
# In XDS terms this will be a little different. CORRECT provides GXPARM.XDS
# which could be recycled. A pointgroup determination routine will be needed.
# XDS reindexing needs to be sussed, as well as getting comparative R factors
# - how easy is this?
