import os
import sys

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Toolkit.Merger import merger

def SCI479(hklin):
    m = merger(hklin)
    
    m.calculate_resolution_ranges(nbins = 100)
    
    r_comp = m.resolution_completeness()
    r_rm = m.resolution_rmerge()
    r_uis = m.resolution_unmerged_isigma()
    r_mis = m.resolution_merged_isigma()
    
    print 'Resolution estimates'
    print 'Completeness:        %.2f' % r_comp
    print 'Rmerge:              %.2f' % r_rm
    print 'Unmerged I/sig:      %.2f' % r_uis
    print 'Merged I/sig:        %.2f' % r_mis
    
    return

if __name__ == '__main__':
    SCI479(sys.argv[1])
    
