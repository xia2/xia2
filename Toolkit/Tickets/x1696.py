import os
import sys

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Wrappers.CCP4.Pointless import Pointless

def x1696():
    p = Pointless()
    p.set_hklin(sys.argv[1])
    p.decide_pointgroup()
    print p.get_probably_twinned()

if __name__ == '__main__':

    x1696()

    


