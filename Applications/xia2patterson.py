#!/usr/bin/env cctbx.python
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
from Wrappers.CCP4.Cad import Cad

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
    # -z rms

    import getopt

    args = sys.argv[1:]

    hklin = None
    symmetry = None
    reference = None
    dmin = None
    dmax = None
    rms = 5.0

    if len(sys.argv) < 2:
        raise RuntimeError, '%s hklin [symmetry]' % sys.argv[0]

    optlist, args = getopt.getopt(args, 'm:s:l:h:r:z:')

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
        elif o == '-z':
            rms = float(v)

    if (dmin and not dmax) or (dmax and not dmin):
        raise RuntimeError, 'only one resolution limit provided'

    # if an input PDB file has been given, extract and use the
    # unit cell constants for the calculation...

    if reference:

        unit_cell = None

        for record in open(reference, 'r').readlines():
            if 'CRYST1' in record[:6]:
                unit_cell = tuple(map(float, record[8:55].split()))

        if not unit_cell:
            raise RuntimeError, 'CRYST1 record not found in %s' % reference

        if not os.path.isabs(hklin):
            hklin = os.path.join(os.getcwd(), hklin)

        hklout = os.path.join(os.environ['CCP4_SCR'], 'x2p-cad.mtz')

        cad = Cad()
        cad.set_working_directory(os.environ['CCP4_SCR'])
        cad.add_hklin(hklin)
        cad.set_hklout(hklout)
        cad.set_new_cell(unit_cell)
        cad.update()

        hklin = hklout

    peaks = anomalous_patterson_jiffy(hklin, symmetry,
                                      dmin = dmin, dmax = dmax,
                                      rms = rms)

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

        occs = []

        for p in peaks:
            x, y, z, o = p
            for r in reference_peaks:
                rx, ry, rz = r

                if dmin:

                    if math.sqrt((x - rx) * (x - rx) +
                                 (y - ry) * (y - ry) +
                                 (z - rz) * (z - rz)) < dmin:
                        print '%6.2f %6.2f %6.2f %6.2f' % p
                        occs.append(p[-1])

                else:
                    if math.sqrt((x - rx) * (x - rx) +
                                 (y - ry) * (y - ry) +
                                 (z - rz) * (z - rz)) < 2:
                        print '%6.2f %6.2f %6.2f %6.2f' % p
                        occs.append(p[-1])
        if occs:
            print 'Average peak height: %6.2f (%d)' % \
                  (sum(occs) / len(occs), len(occs))
        else:
            print 'No matching peaks found'
