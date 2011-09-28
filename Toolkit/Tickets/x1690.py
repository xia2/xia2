# debugging work for Diamond Trac #1690

import os
import sys

if not 'XIA2_ROOT' in os.environ:
    raise RuntimeError, 'cannot test without environment'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Modules.Scaler.CCP4ScalerHelpers import erzatz_resolution

def x1690():
    batches = [(1, 240),
               (1001, 1240),
               (2001, 2240),
               (3001, 3120),
               (4001, 4119),
               (5001, 5120),
               (6001, 6240)]

    hklin = '/dls/mx-scratch/gw56/processing/tests/SVNSMOKETEST/10230-2d/DEFAULT/scale/AUTOMATIC_DEFAULT_sorted.mtz'

    resolutions = erzatz_resolution(hklin, batches)

    for b in batches:
        print '%4d %4d' % b, '%.2f' % resolutions[b]

if __name__ == '__main__':

    x1690()
