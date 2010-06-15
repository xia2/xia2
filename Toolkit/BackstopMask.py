#!/usr/bin/env cctbx.python
# BackstopMask.py
# 
#   Copyright (C) 2010 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# The kernel of code to start to calculate backstop masks for Mosflm and
# XDS from a list of coordinates read off from ADXV of the corners of the
# backstop. Initially this will be coded for the backstop on Diamond Light
# Source beamline I03

import math
import os
import sys

def mmcc(ds, xs, ys):
    '''Fit a straight line

    (x, y) = (mx, my) *  d + (cx, cy)
    
    to ordinates x, y in xs, ys as a function of d in ds.'''

    assert(len(ds) == len(xs))
    assert(len(ds) == len(ys))

    ds = map(float, ds)
    xs = map(float, xs)
    ys = map(float, ys)

    _d = sum(ds) / len(ds)
    _x = sum(xs) / len(xs)
    _y = sum(ys) / len(ys)

    mx = sum([(d - _d) * (x - _x) for d, x in zip(ds, xs)]) / \
         sum([(d - _d) * (d - _d) for d in ds])

    my = sum([(d - _d) * (y - _y) for d, y in zip(ds, ys)]) / \
         sum([(d - _d) * (d - _d) for d in ds])

    cx = _x - mx * _d
    cy = _y - my * _d

    return mx, my, cx, cy

def compute_fit(distances, coordinates):

    xs = [c[0] for c in coordinates]
    ys = [c[1] for c in coordinates]

    return mmcc(distances, xs, ys)

def directions(o, t):
    '''Compute a list of directions o -> t unit length.'''

    assert(len(o) == len(t))

    result = []

    for j in range(len(o)):
        dx = t[j][0] - o[j][0]
        dy = t[j][1] - o[j][1]
        l = math.sqrt(dx * dx + dy * dy)
        result.append((dx / l, dy / l))

    return result

def read_site_file(site_file):
    '''Parse a site file containing records which begin:

    distance x1 y1 x2 y2 x3 y3 x4 y4 (nonsense)

    where distance is in mm, coordinates are in pixels. Will return origins and
    directions for positions 2 and 3, and directions for the vectors 2 -> 1
    and 3 -> 4.'''

    # first read out the file

    distances = []
    coordinates = {}

    for record in open(site_file):
        values = map(float, record.split()[:9])
        distances.append(values[0])
        for j in range(4):
            if not j in coordinates:
                coordinates[j] = []
            coordinates[j].append((values[2 * j + 1], values[2 * j + 2]))

    # now compute directions and so on for 2, 3 first

    mx2, my2, cx2, cy2 = compute_fit(distances, coordinates[1])
    mx3, my3, cx3, cy3 = compute_fit(distances, coordinates[2])
    
    # then directions for 2 -> 1, 3 -> 4

    d21 = directions(coordinates[1], coordinates[0])
    d34 = directions(coordinates[2], coordinates[3])

    # and a fit for this

    mx21, my21, cx21, cy21 = compute_fit(distances, d21)
    mx34, my34, cx34, cy34 = compute_fit(distances, d34)

    # now print fits etc

    for j in range(len(distances)):
        d = distances[j]
        p2 = (mx2 * d + cx2, my2 * d + cy2)
        p3 = (mx3 * d + cx3, my3 * d + cy3)

        o2 = coordinates[1][j]
        o3 = coordinates[2][j]

        print '%6.1f %6.1f %6.1f - %6.1f %6.1f %6.1f %6.1f - %6.1f %6.1f' % \
              (d, o2[0], o2[1], p2[0], p2[1], o3[0], o3[1], p3[0], p3[1])

if __name__ == '__main__':

    read_site_file(sys.argv[1])
    
    
