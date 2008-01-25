#!/usr/bin/env python
import sys
import os
import time

sys.path.append(os.environ['XIA2_ROOT'])

from Wrappers.XIA.Printpeaks import Printpeaks

def screen():

    t0 = time.time()
    count = 0
    for image in sys.argv[1:]:
        count += 1
        p = Printpeaks()
        p.set_image(image)
        status = p.screen()
        print os.path.split(image)[-1], status
    t1 = time.time()
    
    print 'Total time: %.1f' % (t1 - t0)
    print 'Per image: %.3f' % ((t1 - t0) / count)

if __name__ == '__main__':
    screen()

    
    
