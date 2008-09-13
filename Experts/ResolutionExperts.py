#!/usr/bin/env python
# ResolutionExperts.py
# 
#   Copyright (C) 2008 STFC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
# 
# A couple of classes to assist with resolution calculations - these
# are for calculating resolution (d, s) for either distance / beam /
# wavelength / position or h, k, l, / unit cell.
#

import os
import sys
import math
import random

# jiffy functions

def real_to_reciprocal(a, b, c, alpha, beta, gamma):
    '''Convert real cell parameters to reciprocal space.'''

    # convert angles to radians

    rtod = math.pi / 180.0

    alpha *= rtod
    beta *= rtod
    gamma *= rtod

    # set up some useful variables

    ca = math.cos(alpha)
    cb = math.cos(beta)
    cg = math.cos(gamma)

    sa = math.sin(alpha)
    sb = math.sin(beta)
    sg = math.sin(gamma)

    # compute volume

    V = a * b * c * math.sqrt(
        1 - ca * ca - cb * cb - cg * cg + 2 * ca * cb * cg)

    # compute reciprocal lengths

    as = b * c * sa / V
    bs = c * a * sb / V
    cs = a * b * sg / V

    # compute reciprocal angles

    cas = (cb * cg - ca) / (sb * sg)
    cbs = (ca * cg - cb) / (sa * sg)
    cgs = (ca * cb - cg) / (sa * sb)

    alphas = math.acos(cas) / rtod
    betas = math.acos(cbs) / rtod
    gammas = math.acos(cgs) / rtod
   
    return as, bs, cs, alphas, betas, gammas

def B(a, b, c, alpha, beta, gamma):
    '''Compute a B matrix from reciprocal cell parameters.'''

    # convert angles to radians

    rtod = math.pi / 180.0

    alpha *= rtod
    beta *= rtod
    gamma *= rtod

    # set up some useful variables

    ca = math.cos(alpha)
    cb = math.cos(beta)
    cg = math.cos(gamma)

    sa = math.sin(alpha)
    sb = math.sin(beta)
    sg = math.sin(gamma)

    # compute volume

    V = a * b * c * math.sqrt(
        1 - ca * ca - cb * cb - cg * cg + 2 * ca * cb * cg)

    car = (cb * cg - ca) / (sb * sg)
    sar = V / (a * b * c * sb * sg)

    a_ = (a, 0.0, 0.0)
    b_ = (b * cg, b * sg, 0.0)
    c_ = (c * cb, - c * sb * car, c * sb * sar)

    # verify...

    la = math.sqrt(dot(a_, a_))
    lb = math.sqrt(dot(b_, b_))
    lc = math.sqrt(dot(c_, c_))

    if (math.fabs(la - a) / la) > 0.001:
        raise RuntimeError, 'inversion error'

    if (math.fabs(lb - b) / lb) > 0.001:
        raise RuntimeError, 'inversion error'

    if (math.fabs(lc - c) / lc) > 0.001:
        raise RuntimeError, 'inversion error'

    return a_, b_, c_

def dot(a, b):
    '''Compute a.b.'''

    d = 0.0

    for j in range(3):
        d += a[j] * b[j]

    return d

def mult_vs(v_, s):
    return [v * s for v in v_]

def sum_vv(a_, b_):
    r_ = []
    for j in range(3):
        r_.append(a_[j] + b_[j])
    return r_

def resolution(h, k, l, a_, b_, c_):
    '''Compute resolution of reflection h, k, l. Returns 1.0 / d^2.'''

    ha_ = mult_vs(a_, h)
    kb_ = mult_vs(b_, k)
    lc_ = mult_vs(c_, l)

    d = sum_vv(ha_, sum_vv(kb_, lc_))

    return dot(d, d)

def meansd(values):
    mean = sum(values) / len(values)
    sd = 0.0

    if len(values) == 0:
        return 0.0, 0.0

    if len(values) == 1:
        return values[0], 0.0

    for v in values:
        sd += (v - mean) * (v - mean)

    sd /= len(values)

    return mean, math.sqrt(sd)

def generate(number, isigma):
    '''Generete a population of numbers (from a Gaussian distribution)
    with the specified I/sigma. For this purpose, I == 1.0 while sigma is
    1.0 / required I/sigma.'''

    result = []
    for j in range(number):
        result.append(random.gauss(1.0, 1.0 / isigma))

    return result

def wilson(nu, nm, isigma):
    '''Generate nu separate reflections each with given nm
    which have an I/sigma as given. Mean value will be set as 1.0
    with intensities assigned from a Winson distribution.'''

    reflections = []
    for c in range(nu):
        imean = random.expovariate(1.0)
        result = []
        for m in range(nm):
            result.append((random.gauss(imean, imean / isigma),
                           imean / isigma))
        reflections.append(result)

    return reflections

def cc(a_, b_):
    a2_ = [a * a for a in a_]
    b2_ = [b * b for b in b_]

    ab_ = []
    for j in range(len(a_)):
        ab_.append(a_[j] * b_[j])

    ab = sum(ab_) / len(ab_)
    a = sum(a_) / len(a_)
    b = sum(b_) / len(b_)
    a2 = sum(a2_) / len(a2_)
    b2 = sum(b2_) / len(b2_)

    return (ab - a * b) / math.sqrt(
        (a2 - a * a) * (b2 - b * b))

def main(mtzdump):
    '''Work through the mtzdump output and calculate resolutions for
    all reflections, from the unit cell for the data set.'''

    cell = None

    for j in range(len(mtzdump)):
        if 'project/crystal/dataset names' in mtzdump[j]:
            cell = map(float, mtzdump[j + 5].split())
            break

    a, b, c, alpha, beta, gamma = cell

    as, bs, cs, alphas, betas, gammas = real_to_reciprocal(
        a, b, c, alpha, beta, gamma)

    a_, b_, c_ = B(as, bs, cs, alphas, betas, gammas)

    j = 0

    while not 'LIST OF REFLECTIONS' in mtzdump[j]:
        j += 1

    j += 2

    reflections = []

    while not 'FONT' in mtzdump[j]:
        lst = mtzdump[j].split()
        if not lst:
            j += 1
            continue
        h, k, l = map(int, lst[:3])
        s = resolution(h, k, l, a_, b_, c_)
        f, sf = map(float, lst[3:5])

        reflections.append((s, f, sf))
       
        j += 1

    reflections.sort()

    binsize = 250

    j = 0

    while j < len(reflections):
        bin = reflections[j:j + binsize]

        f = []
        sf = []
        ffs = []
        s = []
        isigma = []
        for b in bin:
            s.append(b[0])
            f.append(b[1])
            sf.append(b[2])
            ffs.append(b[1] + b[2])
            isigma.append(b[1] / b[2])

        c = cc(f, ffs)
        mean, sd = meansd(isigma)
        mf = meansd(f)[0]
        ms = meansd(sf)[0]
        print 1.0 / math.sqrt(sum(s) / len(s)), c, len(bin), mean, sd, mf / ms

        j += binsize

def model():

    for isigma in [0.5, 1.0, 1.5, 2.0, 3.0]:

        ccl = []

        for q in range(100):

            refl = []
           
            all = wilson(200, 1, isigma)
           
            for a in all:
                refl.append(a[0])
               
            i = []
            sigma = []
            i_sigma = []
           
            for r in refl:
                i.append(r[0])
                sigma.append(r[1])
                i_sigma.append(r[0] + r[1])

            ccl.append(cc(i, i_sigma))

        za, zb = meansd(ccl)
        print isigma, za, zb
        sys.stdout.flush()

class ResolutionCell:
    '''A class to use for calculating the resolution from the unit cell
    parameters and h, k, l. Cell constants are numbers in real space.'''

    def __init__(self, a, b, c, alpha, beta, gamma):
        _a, _b, _c, _alpha, _beta, _gamma = real_to_reciprocal(
            a, b, c, alpha, beta, gamma)

        self._A, self._B, self._C = B(_a, _b, _c, _alpha, _beta, _gamma)

        return

    def resolution(self, h, k, l):
        s = resolution(h, k, l, self._A, self._B, self._C)
        return s, 1.0 / math.sqrt(s)

class ResolutionGeometry:
    '''A class for calculating the resolution of a reflection from the
    position on the detector, wavelength, beam centre and distance.'''

    def __init__(self, distance, wavelength, beam_x, beam_y):
        self._distance = distance
        self._wavelength = wavelength
        self._beam_x = beam_x
        self._beam_y = beam_y
        return

    def resolution(self, x, y):

        d = math.sqrt((x - self._beam_x) * (x - self._beam_x) +
                      (y - self._beam_y) * (y - self._beam_y))

        t = 0.5 * math.atan(d / self._distance)

        r = self._wavelength / (2.0 * math.sin(t))

        s = 1.0 / (r * r)

        return s, r

def xds_integrate_header_read(xds_hkl):
    '''Read the contents of an XDS INTEGRATE.HKL file to get the header
    information, namely the detector origin, cell constants, wavelength
    and pixel size.'''

    # fixme do I need to calculate the beam centre? probably

    cell = None
    pixel = None
    distance = None
    wavelength = None
    origin = None
    beam = None

    for record in open(xds_hkl, 'r').readlines():
        if not record[0] == '!':
            break

        lst = record[1:].split()

        if lst[0] == 'UNIT_CELL_CONSTANTS=':
            cell = tuple(map(float, lst[1:]))
            continue

        if lst[0] == 'DETECTOR_DISTANCE=':
            distance = float(lst[-1])
            continue

        if lst[0] == 'X-RAY_WAVELENGTH=':
            wavelength = float(lst[-1])
            continue

        if lst[0] == 'NX=':
            pixel_x = float(lst[5])
            pixel_y = float(lst[7])
            pixel = pixel_x, pixel_y
            continue

        if lst[0] == 'ORGX=':
            origin_x = float(lst[1])
            origin_y = float(lst[3])
            origin = origin_x, origin_y
            continue

        if lst[0] == 'INCIDENT_BEAM_DIRECTION=':
            beam = tuple(map(float, lst[1:]))

    if not pixel:
        raise RuntimeError, 'pixel size not found'
    
    if not cell:
        raise RuntimeError, 'cell not found'
    
    if not origin:
        raise RuntimeError, 'origin not found'

    if not distance:
        raise RuntimeError, 'distance not found'
    
    if not wavelength:
        raise RuntimeError, 'wavelength not found'

    if not beam:
        raise RuntimeError, 'beam vector not found'

    # no calculate the beam centre offset

    beam = (wavelength * beam[0],
            wavelength * beam[1],
            wavelength * beam[2])

    q = distance / beam[2]

    delta = beam[0] * q / pixel[0], beam[1] * q / pixel[1]

    origin = (origin[0] + delta[0],
              origin[1] + delta[1])

    return cell, pixel, origin, distance, wavelength

def xds_integrate_hkl_to_list(xds_hkl):
    '''Convert the output from XDS INTEGRATE to a list of (s, i, sigma)
    records. Check the s calculations as an aside.'''

    cell, pixel, origin, distance, wavelength = xds_integrate_header_read(
        xds_hkl)

    a, b, c, alpha, beta, gamma = cell

    rc = ResolutionCell(a, b, c, alpha, beta, gamma)

    result = []

    for record in open(xds_hkl, 'r').readlines():
        if record[:1] == '!':
            continue

        lst = record.split()

        if not lst:
            continue

        h, k, l = tuple(map(int, lst[:3]))

        i, sigma, x, y = tuple(map(float, lst[3:7]))

        src, rrc = rc.resolution(h, k, l)

        result.append((src, i, sigma))

    return result

def bin_o_tron(sisigma):
    '''Bin the incoming list of (s, i, sigma) and return a list of bins
    of width 0.001 in S.'''

    bins = {}

    for j in range(2000):
        bins[j] = []
                 
    for sis in sisigma:
        s, i, sigma = sis

        qs = nint(1000 * s)

        bins[qs].append((i / sigma))

    result = { }

    for j in range(2000):
        result[0.001 * j] = meansd(bins[j])

    return result
    

if __name__ == '__main__':
    xds_integrate_hkl_to_list(sys.argv[1])

if __name__ == '__moon__':
    rc = ResolutionCell(90.24, 90.24, 45.24, 90.0, 90.0, 120.0)

    for l in range(1, 35):
        s, r = rc.resolution(0, 0, l)
        print '%d %.4f %.2f' % (l, s, r)

    for k in range(1, 65):
        s, r, = rc.resolution(0, k, 0)
        print '%d %.4f %.2f' % (k, s, r)

    rg = ResolutionGeometry(200.0, 0.97975, 109.0, 105.0)

    for xy in [(100, 100), (200, 200)]:
        s, r = rg.resolution(xy[0], xy[1])
        print '%.1f %.1f %.4f %.4f' % (xy[0], xy[1], s, r)
        

if __name__ == '__malin__':

    main(open('infl.log', 'r').readlines())

    # model()

    # import random

    # a = [random.random() for j in range(100)]
    # b = [random.random() for j in range(100)]

    # print cc(a, b)
   
