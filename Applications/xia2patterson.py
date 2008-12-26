#!/usr/bin/env python
# xia2patterson
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.

import sys
import os
import math

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'
if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

from Experts.PattersonExpert import anomalous_patterson_jiffy

if __name__ == '__main__':

    # big change - move to a getopts style input which will allow me
    # to provide much more in the way of command-line arguments
    #
    # options are:
    # 
    # -m hklin 
    # -s symmetry
    # -l low resolution limit
    # -h high resolution limit
    # -r reference pdb
    #

    import getopt

    args = sys.argv[1:]

    hklin = None
    symmetry = None
    reference = None
    dmin = None
    dmax = None

    if len(sys.argv) < 2:
        raise RuntimeError, '%s hklin [symmetry]' % sys.argv[0]

    optlist, args = getopt.getopt(args, 'm:s:l:h:r:')

    if args:
        raise RuntimeError, 'unknown arguments: %s' % str(args)

    for opt in optlist:
        o = opt[0]
        v = opt[1]

        if o == '-m':
            hklin = v
        elif o == '-r':
            reference = v
        elif o == '-s':
            symmetry = v
        elif o == '-h':
            dmin = float(v)
        elif o == '-l':
            dmax = float(v)

    if (dmin and not dmax) or (dmax and not dmin):
        raise RuntimeError, 'only one resolution limit provided'

    peaks = anomalous_patterson_jiffy(hklin, symmetry,
                                      dmin = dmin, dmax = dmax)

    if not reference:

        for p in peaks:
            print '%6.2f %6.2f %6.2f %6.2f' % p

    else:

        # first parse the reference file

        reference_peaks = []

        for record in open(reference, 'r').readlines():
            if 'ATOM' in record:
                reference_peaks.append(
                    tuple(map(float, record.split()[5:8])))

        for p in peaks:
            x, y, z, o = p
            for r in reference_peaks:
                rx, ry, rz = r

                if math.sqrt((x - rx) * (x - rx) +
                             (y - ry) * (y - ry) +
                             (z - rz) * (z - rz)) < 2:
                    print '%6.2f %6.2f %6.2f %6.2f' % p
                             
                
    

