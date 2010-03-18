#!/usr/bin/env cctbx.python
# PolyFitter.py
# 
#   Copyright (C) 2010 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
# 
# A toolkit component for performing polynomial fits to an array of data,
# using the CCTBX lbfgs minimiser.

import math

from cctbx.array_family import flex
from scitbx import lbfgs

def poly_residual(x, y, params):
    '''Compute the residual between the observations y[i] and sum_j
    params[j] x[i]^j.'''

    r = 0.0

    n = len(params)

    for j, _x in enumerate(x):
        o = y[j]
        e = sum([math.pow(_x, k) * params[k] for k in range(n)])
        r += (o - e) * (o - e)

    return r

def poly_gradients(x, y, params):
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
            rs.append(poly_residual(x, y, params_eps))
        g.append((rs[1] - rs[0]) / (2 * eps))

    return g

class PolyFitter:
    '''A class to do the polynomial fit. This will fit observations y
    at points x with a polynomial of order n.'''

    def __init__(self, points, values, order):
        self.x = flex.double([1.0 for j in range(order)])
        self._x = flex.double(points)
        self._y = flex.double(values)

        return

    def refine(self):
        '''Actually perform the parameter refinement.'''

        return lbfgs.run(target_evaluator = self)

    def compute_functional_and_gradients(self):
        return poly_residual(self._x, self._y, self.x), \
               poly_gradients(self._x, self._y, self.x)

    def get_parameters(self):
        return list(self.x)

if __name__ == '__main__':

    import random

    def f(x):
        return 1.0 + x + 2.0 * math.pow(x, 2) + 0.01 * random.random()

    x = [0.01 * j for j in range(100)]
    y = [f(_x) for _x in x]

    r = PolyFitter(x, y, 3)
    r.refine()
    print r.get_parameters()
