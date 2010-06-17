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

def dot(a, b):
    return a[0] * b[0] + a[1] * b[1]

def line_intersect_rectangle(o, d, nx, ny):
    '''Calculate where a line starting at origin o and heading in direction d
    intersects rectangle bounded by (0,0), (nx, 0), (nx, ny), (0, ny).'''

    # requirements are:
    #
    # direction not perpendicular to axis:
    #  intersection is within range:
    #    direction to intersection point is positive:
    #      return this

    assert(math.fabs(dot(d, d) - 1) < 0.001)

    if d[0] != 0.0:
        intersection = o[1] - (o[0] / d[0]) * d[1]
        if 0 <= intersection <= ny:
            if dot((0.0 - o[0], intersection - o[1]), d) > 0.0:
                return (0.0, intersection)
                   
        intersection = o[1] - ((o[0] - nx) / d[0]) * d[1]
        if 0 <= intersection <= ny:
            if dot((nx - o[0], intersection - o[1]), d) > 0.0:
                return (nx, intersection)

    if d[1] != 0.0:
        intersection = o[0] - (o[1] / d[1]) * d[0]
        if 0 <= intersection <= nx:
            if dot((intersection - o[0], 0.0 - o[1]), d) > 0.0:
                return (intersection, 0.0)

        intersection = o[0] - ((o[1] - ny) / d[1]) * d[0]
        if 0 <= intersection <= nx:
            if dot((intersection - o[0], ny - o[1]), d) > 0.0:
                return (intersection, ny)

    raise RuntimeError, 'intersection not found'

def read_site_file(site_file, distance, nx = 3072, ny = 3072):
    '''Parse a site file containing records which begin:

    distance x1 y1 x2 y2 x3 y3 x4 y4 (nonsense)

    where distance is in mm, coordinates are in pixels. Will return origins and
    directions for positions 2 and 3, and directions for the vectors 2 -> 1
    and 3 -> 4. Currently hard-coded for a Q315 - could do much better by
    passing in an actual image as an argument. Now returns four corners of
    the backstop region.'''

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

    # now compute the fits

    p2 = (mx2 * distance + cx2, my2 * distance + cy2)
    p3 = (mx3 * distance + cx3, my3 * distance + cy3)

    d21 = (mx21 * distance + cx21, my21 * distance + cy21)
    d34 = (mx34 * distance + cx34, my34 * distance + cy34)

    # now extrapolate the directions

    p1 = line_intersect_rectangle(p2, d21, nx, ny)
    p4 = line_intersect_rectangle(p3, d34, nx, ny)

    return p1, p2, p3, p4

def work_line_intersect_angle():

    import random

    for j in range(1000):
        o = (2.0 * random.random(), 2.0 * random.random())
        t = 2.0 * math.pi * random.random()
        d = (math.cos(t), math.sin(t))

        i = line_intersect_rectangle(o, d, 2, 2)

        x = (i[0] - o[0], i[1] - o[1])

        assert(0.0 <= i[0] <= 2.0)
        assert(0.0 <= i[1] <= 2.0)

        assert(math.fabs(
            (dot(x, d) / math.sqrt(dot(x, x) * dot(d, d))) - 1) < 0.001)

    return

def to_mosflm_frame(p, dx, dy):
    '''Convert coordinate p in ADSC frame to Mosflm frame in mm.'''

    return (p[1] * dy, p[0] * dx)

if __name__ == '__main__':

    for p in read_site_file(sys.argv[1], float(sys.argv[2])):
        print '%6.2f %6.2f' % to_mosflm_frame(p, 0.1026, 0.1026)
