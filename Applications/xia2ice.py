#!/usr/bin/env python
import sys
import os
import time

sys.path.append(os.environ['XIA2_ROOT'])

from Modules.IceId import IceId

def xia2ice():

    n = 1
    beam = None

    if sys.argv[1] == '-beam':
        beam = tuple(map(float, sys.argv[2].split(',')))
        n = 3

    for image in sys.argv[n:]:
        i = IceId()
        i.set_image(image)

        if beam:
            i.set_beam(beam)

        name = os.path.split(image)[-1]

        print '%s %.3f' % (name, i.search())

if __name__ == '__main__':
    xia2ice()
