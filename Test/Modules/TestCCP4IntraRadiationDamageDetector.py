# TestCCP4IntraRadiationDamageDetector.py
# Maintained by G.Winter
# 
# Does exactly what it says on the tin, you pass it the scaled reflection 
# file and the sweep information and it will do the rest...

import os
import sys

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Modules.CCP4IntraRadiationDamageDetector import \
     CCP4IntraRadiationDamageDetector

def run(mtz, sweep_info):
    irdd = CCP4IntraRadiationDamageDetector()

    irdd.set_hklin(mtz)
    irdd.set_sweep_information(eval(open(sweep_info, 'r').read().strip()))
    return irdd.analyse()

if __name__ == '__main__':
    if len(sys.argv) < 3:
        raise RuntimeError, '%s mtz sweep_info' % sys.argv[0]

    run(sys.argv[1], sys.argv[2])

    
