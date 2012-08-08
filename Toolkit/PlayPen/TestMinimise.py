#!/usr/bin/env cctbx.python
#
# TestMinimise.py - test the use of the minimisers in CCTBX, namely LBFGS.
#

import math
import random

from cctbx.array_family import flex
from scitbx import lbfgs

def myfunc(x, _a, _b, _c):
    return _c * math.pow(x, 2) + _b * x + _a

def residual(obs, params):

    r = 0.0

    a = params[0]
    b = params[1]
    c = params[2]

    for j in range(10):
        e = myfunc(j, a, b, c)
        o = obs[j]
        r += (o - e) * (o - e)

    return r

def gradients(obs, params):

    g = flex.double()

    for j in range(3):
        rs = []
        for signed_eps in [-1.0e-6, 1.0e-6]:
            params_eps = params[:]
            params_eps[j] += signed_eps
            rs.append(residual(obs, params_eps))
        g.append((rs[1] - rs[0]) / 2.0e-6)

    return g

class refinery:

    def __init__(self):
        self.x = flex.double([1.0, 1.0, 1.0])
        self.y = flex.double()

        self._a = random.random()
        self._b = random.random()
        self._c = random.random()

        for j in range(10):
            self.y.append(myfunc(j, self._a, self._b, self._c))

    def refine(self):
        l = lbfgs.run(target_evaluator = self)
        return

    def report(self):

        print '%.3f %.3f %.3f' % (self.x[0], self.x[1], self.x[2])
        print '%.3f %.3f %.3f' % (self._a, self._b, self._c)

        return

    def compute_functional_and_gradients(self):
        return residual(self.y, self.x), gradients(self.y, self.x)

if __name__ == '__main__':
    r = refinery()
    r.refine()
    r.report()
