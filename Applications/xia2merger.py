#!/usr/bin/env python
# xia2merger.py
#   Copyright (C) 2011 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Wrapper to allow code written to merge reflections to be externalised...
#
# 03/MAR/16
# To resolve the naming conflict between this file and the entire xia2 module
# any xia2.* imports in this directory must instead be imported as ..*

from __future__ import absolute_import, division, print_function

from xia2.Toolkit.Merger import merger

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument("hklin", type=str, help="input reflection file")
    parser.add_argument("-n", "--nbins", type=float, help="number of resolution bins")
    parser.add_argument("-r", "--rmerge", type=float, help="limit on Rmerge")
    parser.add_argument(
        "-c", "--completeness", type=float, help="limit on completeness [0,1]"
    )
    parser.add_argument("-i", "--isigma", type=float, help="limit on I/sigma")
    parser.add_argument("-m", "--misigma", type=float, help="limit on Mn(I/sigma)")
    args = parser.parse_args()

    if args.nbins:
        nbins = args.nbins
    else:
        nbins = 100

    m = merger(args.hklin)
    m.calculate_resolution_ranges(nbins=nbins)

    if args.completeness:
        print("COMPLETENESS %f" % m.resolution_completeness(limit=args.completeness))

    if args.rmerge:
        print("RMERGE %f" % m.resolution_rmerge(limit=args.rmerge))

    if args.isigma:
        print("ISIGMA %f" % m.resolution_unmerged_isigma(limit=args.isigma))

    if args.misigma:
        print("MISIGMA %f" % m.resolution_merged_isigma(limit=args.misigma))
