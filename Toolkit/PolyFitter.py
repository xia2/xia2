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

    e = flex.double([flex.sum(xp[j] * params) for j in range(c)])

    return flex.sum(flex.pow2(y - e))

def poly_gradients(xp, y, params):
    '''Compute the gradient of the residual w.r.t. the parameters, N.B.
    will be performed using a finite difference method. N.B. this should
    be trivial to do algebraicly.'''

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

def fit(x, y, order):
    '''Fit the values y(x) then return this fit. x, y should
    be iterables containing floats of the same size. The order is the order
    of polynomial to use for this fit. This will be useful for e.g. I/sigma.'''

    pf = poly_fitter(x, y, order)
    pf.refine()

    return [pf.evaluate(_x) for _x in x]

def log_fit(x, y, order):
    '''Fit the values log(y(x)) then return exp() to this fit. x, y should
    be iterables containing floats of the same size. The order is the order
    of polynomial to use for this fit. This will be useful for e.g. I/sigma.'''

    ly = [math.log(_y) for _y in y]

    pf = poly_fitter(x, ly, order)
    pf.refine()

    return [math.exp(pf.evaluate(_x)) for _x in x]

def log_inv_fit(x, y, order):
    '''Fit the values log(1 / y(x)) then return the inverse of this fit.
    x, y should be iterables, the order of the polynomial for the transformed
    fit needs to be specified. This will be useful for e.g. Rmerge.'''

    ly = [math.log(1.0 / _y) for _y in y]

    pf = poly_fitter(x, ly, order)
    pf.refine()

    return [(1.0 / math.exp(pf.evaluate(_x))) for _x in x]

def interpolate_value(x, y, t):
    '''Find the value of x: y(x) = t.'''

    if t > max(y) or t < min(y):
        raise RuntimeError, 't outside of [%f, %f]' % (min(y), max(y))

    for j in range(1, len(x)):
        x0 = x[j - 1]
        y0 = y[j - 1]

        x1 = x[j]
        y1 = y[j]

        if (y0 - t) * (y1 - t) < 0:
            return x0 + (t - y0) * (x1 - x0) / (y1 - y0)
        
if __name__ == '__main__':

    pass

