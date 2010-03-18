#!/usr/bin/env cctbx.python
# PolyFitter.py
# 
#   Copyright (C) 2010 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
# 
# A toolkit component for performing polynomial fits to an array of data,
# using the CCTBX lbfgs minimiser. For data from a general form, it may
# be helpful to transform the measurements to a "sensible" form - for example
# taking log(I/sigI).

import math

from cctbx.array_family import flex
from scitbx import lbfgs

def poly_residual(xp, y, params):
    '''Compute the residual between the observations y[i] and sum_j
    params[j] x[i]^j. For efficiency, x[i]^j are pre-calculated in xp.'''

    r = 0.0

    n = len(params)
    c = len(y)

    e = flex.double()

    for j in range(c):
        e.append(flex.sum(xp[j] * params))

    return flex.sum(flex.pow2(y - e))

def poly_gradients(xp, y, params):
    '''Compute the gradient of the residual w.r.t. the parameters, N.B.
    will be performed using a finite difference method.'''

    eps = 1.0e-6

    g = flex.double()

    n = len(params)

    for j in range(n):
        rs = []
        for signed_eps in [- eps, eps]:
            params_eps = params[:]
            params_eps[j] += signed_eps
            rs.append(poly_residual(xp, y, params_eps))
        g.append((rs[1] - rs[0]) / (2 * eps))

    return g

class poly_fitter:
    '''A class to do the polynomial fit. This will fit observations y
    at points x with a polynomial of order n.'''

    def __init__(self, points, values, order):
        self.x = flex.double([1.0 for j in range(order)])
        self._x = flex.double(points)
        self._y = flex.double(values)

        # precalculate x[j]^[0-(n - 1)] values

        self._xp = [flex.double([math.pow(x, j) for j in range(order)])
                    for x in self._x]

        return

    def refine(self):
        '''Actually perform the parameter refinement.'''

        return lbfgs.run(target_evaluator = self)

    def compute_functional_and_gradients(self):
        return poly_residual(self._xp, self._y, self.x), \
               poly_gradients(self._xp, self._y, self.x)

    def get_parameters(self):
        return list(self.x)

    def evaluate(self, x):
        '''Evaluate the resulting fit at point x.'''

        return sum([math.pow(x, k) * self.x[k] for k in range(len(self.x))])

if __name__ == '__main__':

    import random

    random.seed(1)

    def f(x):
        return math.sin(10 * x) + 1.0 + x + 2.0 * math.pow(x, 2) + \
               0.2 * random.random()

    x = [0.01 * j for j in range(100)]
    y = [f(_x) for _x in x]

    r = poly_fitter(x, y, 10)
    r.refine()

    for j, _x in enumerate(x):
        print '%.4f %.4f %.4f' % (_x, y[j], r.evaluate(_x))
        
