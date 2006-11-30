#!/usr/bin/env python
# CCP4ScalerImplementationHelpers.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
#
# 3rd November 2006
# 
# Helpers for the "CCP4" Scaler implementation - this contains little
# functions which wrap the wrappers which are needed. It will also contain
# small functions for computing e.g. resolution limits.
#

import os
import sys

from Wrappers.CCP4.Mtzdump import Mtzdump
from Wrappers.CCP4.Rebatch import Rebatch
from lib.Guff import auto_logfiler
from Handlers.Streams import Chatter

def _resolution_estimate(ordered_pair_list, cutoff):
    '''Come up with a linearly interpolated estimate of resolution at
    cutoff cutoff from input data [(resolution, i_sigma)].'''

    x = []
    y = []

    for o in ordered_pair_list:
        x.append(o[0])
        y.append(o[1])

    if max(y) < cutoff:
        # there is no resolution where this exceeds the I/sigma
        # cutoff
        return -1.0

    # this means that there is a place where the resolution cutof
    # can be reached - get there by working backwards

    x.reverse()
    y.reverse()

    if y[0] >= cutoff:
        # this exceeds the resolution limit requested
        return x[0]

    j = 0
    while y[j] < cutoff:
        j += 1

    resolution = x[j] + (cutoff - y[j]) * (x[j - 1] - x[j]) / \
                 (y[j - 1] - y[j])

    return resolution

def _prepare_pointless_hklin(working_directory,
                             hklin,
                             phi_width):
    '''Prepare some data for pointless - this will take only 180 degrees
    of data if there is more than this (through a "rebatch" command) else
    will simply return hklin.'''

    # find the number of batches

    md = Mtzdump()
    md.set_working_directory(working_directory)
    auto_logfiler(md)
    md.set_hklin(hklin)
    md.dump()

    batches = max(md.get_batches()) - min(md.get_batches())

    phi_limit = 180

    if batches * phi_width < phi_limit:
        return hklin

    hklout = os.path.join(
        working_directory,
        '%s_prepointless.mtz' % (os.path.split(hklin)[-1][:-4]))

    rb = Rebatch()
    rb.set_working_directory(working_directory)
    auto_logfiler(rb)
    rb.set_hklin(hklin)
    rb.set_hklout(hklout)

    first = min(md.get_batches())
    last = first + int(phi_limit / phi_width)

    Chatter.write('Preparing data for pointless - %d batches (%d degrees)' % \
                  ((last - first), phi_limit))

    rb.limit_batches(first, last)

    return hklout
