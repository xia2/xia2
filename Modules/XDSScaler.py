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

import os
import sys
import math

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

# the interface definition that this will conform to 
from Schema.Interfaces.Scaler import Scaler
from Modules.XDSPointgroup import XDSPointgroup

class XDSScaler(Scaler):
    '''An implementation of the xia2 Scaler interface implemented with
    xds and xscale, possibly with some help from a couple of CCP4
    programs like pointless and combat.'''

    def __init__(self):
        Scaler.__init__(self)

        self._sweep_information = { }

        self._common_pname = None
        self._common_xname = None
        self._common_dname = None

        return    

    # This will have to work as follows...
    #
    # PREPARE:
    # 
    # For all integraters - get INTEGRATE.HKL, run CORRECT, COMBAT,
    # POINTLESS, get any appropriate reindexing operator, perhaps
    # eliminate lattices, reget INTEGRATE.HKL, rerun CORRECT, store for
    # reference in SCALE.
    #
    # 23/MAY/07 this is now wrong! The reindexing and correct step etc.
    # will be done by the integrater as this has the appropriate
    # information - this will, however, feedback *what* reindexing etc.
    # needs to be done, including getting the indexing setting correct.
    #
    # This will therefore have to get the pointers to the XDS_ASCII files
    # for each sweep then copy them into the appropriate working directory
    # in here as say WAVENAME_SWEEPNAME.HKL. These will then be fed in to
    # the pointgroup determination etc.
    # 
    # SCALE:
    # 
    # Scale together all data, run results of XSCALE through COMBAT,
    # merge with SCALA, decide resolution limits from merging statistics,
    # feedback? Perhaps. Also include a POINTLESS run in here to get the 
    # best idea of the spacegroup from the updated CORRECT run, perhaps.
    # This should output merged MTZ and unmerged scalepack. Rest can be
    # derived by the scaler interface.
    # 
    
