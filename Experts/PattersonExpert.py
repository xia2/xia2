#!/usr/bin/env cctbx.python
# PattersonExpert.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 24th July 2007
#
# A small expert to handle patterson map calculations. This will factor in
# things like the symmetry of the crystal in the analysis.

import os
import sys
import math
from cctbx import crystal

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Wrappers.CCP4.Fft import Fft
from Wrappers.CCP4.Cad import Cad
from Wrappers.CCP4.Mtzdump import Mtzdump
from Wrappers.CCP4.Peakmax import Peakmax
from Wrappers.CCP4.Mapmask import Mapmask
from Wrappers.CCP4.Scaleit import Scaleit

def anomalous_patterson_jiffy(hklin, symmetry = None,
                              working_directory = os.getcwd(),
                              scratch = 'patterson-temp',
                              dmin = None,
                              dmax = None,
                              rms = 5.0):
    '''Run a Patterson calculation: scaleit -> fft -> mapmask -> peakmax
    with the intention of getting a meaningful list of peaks out. Scratch
    is a temporary name for temporary map files etc.'''

    # get the resolution limits out etc.

    mtzdump = Mtzdump()
    mtzdump.set_hklin(hklin)
    mtzdump.dump()
    _dmin, _dmax = mtzdump.get_resolution_range()
    datasets = mtzdump.get_datasets()


    if not dmin:
        dmin = _dmin
    if not dmax:
        dmax = _dmax

    if symmetry is None:
        symmetry = mtzdump.get_spacegroup()

    if len(datasets) > 1:
        raise RuntimeError, 'more than one dataset for anomalous Patterson'

    dataset = datasets[0].split('/')[-1]

    # best guess for the unit cell?
    cell = mtzdump.get_dataset_info(datasets[0])['cell']

    dano = ('DANO_%s' % dataset, 'D')
    if dano in mtzdump.get_columns():
        pass
    else:
        dataset = None

    hklout = os.path.join(os.environ['CCP4_SCR'], '%s-scaleit.mtz' % scratch)

    # find the maximum aceptable difference

    scaleit = Scaleit()
    scaleit.set_working_directory(working_directory)
    scaleit.set_hklin(hklin)
    scaleit.set_hklout(hklout)
    scaleit.set_anomalous(True)
    scaleit.scaleit()
    max_diff = scaleit.get_statistics()['max_difference']

    mapout = os.path.join(os.environ['CCP4_SCR'], '%s-fft.map' % scratch)

    # calculate the full anomalous difference Patterson

    fft = Fft()
    fft.set_working_directory(working_directory)
    fft.set_symmetry(symmetry)
    fft.set_hklin(hklin)
    fft.set_mapout(mapout)
    fft.set_resolution_range(dmin, dmax)
    fft.set_exclude_term(max_diff * max_diff)
    fft.set_dataset(dataset)
    fft.patterson()

    # cut the map down to the ASU - no, maybe not

    cut = False

    if cut:

        mapin = mapout
        mapout = os.path.join(os.environ['CCP4_SCR'],
                              '%s-mapmask.map' % scratch)

        mapmask = Mapmask()
        mapmask.set_working_directory(working_directory)
        mapmask.set_mapin(mapin)
        mapmask.set_mapout(mapout)
        mapmask.set_symmetry(symmetry)
        mapmask.mask_asu()

    mapin = mapout
    xyzout = os.path.join(os.environ['CCP4_SCR'], '%s-peakmax.pdb' % scratch)

    # now run a peak search

    peakmax = Peakmax()
    peakmax.set_working_directory(working_directory)
    peakmax.set_mapin(mapin)
    peakmax.set_xyzout(xyzout)
    peakmax.set_rms(rms)
    peakmax.peaksearch()

    # now read the peak list

    all_peaks = []

    for record in open(xyzout, 'r').readlines():
        if 'ATOM' in record[:4]:
            x = float(record[30:38].strip())
            y = float(record[38:46].strip())
            z = float(record[46:54].strip())
            o = float(record[54:60].strip())

            all_peaks.append((x, y, z, o))

    # now reduce these using spells from CCTBX!

    cs = crystal.symmetry(
        unit_cell = cell,
        space_group_symbol = symmetry)

    ds = cs.direct_space_asu()
    sg = cs.space_group()

    am = crystal.direct_space_asu.asu_mappings(
        space_group = sg,
        asu = ds.as_float_asu(),
        buffer_thickness = 0.0)

    for p in all_peaks:
        am.process(cs.unit_cell().fractionalize(p[:3]))

    asu_sites = [m[0].mapped_site() for m in am.mappings()]

    peaks = []

    for j, s in enumerate(asu_sites):
        x, y, z = cs.unit_cell().fractionalize(s)
        o = all_peaks[j][3]
        peaks.append((o, x, y, z))

    return sorted(peaks)

if __name__ == '__main__':

    scratch = 'test'
    working_directory = os.getcwd()
    symmetry = 'P212121'
    hklin = '/Users/graeme/Projects/Patterson/ppe/analyse/PPE_X150A_free.mtz'

    peaks = anomalous_patterson_jiffy(hklin, symmetry,
                                      working_directory, scratch)

    for p in peaks:
        print '%6.3f %6.3f %6.3f %6.2f' % p
