#!/usr/bin/env cctbx.python
# KBScale.py
#
#   Copyright (C) 2010 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# A rough implementation of local scaling for partial data sets, using kB
# scaling. Includes linear and log scaling, and uses CCTBX minimization
# which seems to work nicely. Used in MultiMerger.
#

import math

from cctbx.array_family import flex
from scitbx import lbfgs

def kb(s, k, b):
    return k * math.exp(-1 * b * s)

def residual_kb(ref, work, params):

    k, b = params

    res = sum([math.fabs(r[1] - w[1] * kb(w[0], k, b)) \
               for r, w in zip(ref, work)]) / \
               sum([math.fabs(r[1]) for r in ref])

    return res

def gradients_kb(ref, work, params):

    eps = 1.0e-6

    g = flex.double()

    for j in range(2):
        rs = []
        for signed_eps in [- eps, eps]:
            params_eps = params[:]
            params_eps[j] += signed_eps
            rs.append(residual_kb(ref, work, params_eps))
        g.append((rs[1] - rs[0]) / (2 * eps))

    return g

class kb_scaler:

    def __init__(self, ref, work):

        self.x = flex.double([1.0, 0.0])
        self._ref = ref
        self._work = work

        return

    def refine(self):

        return lbfgs.run(target_evaluator = self)

    def compute_functional_and_gradients(self):

        return residual_kb(self._ref, self._work, self.x), \
               gradients_kb(self._ref, self._work, self.x)

    def get_kb(self):
        return tuple(self.x)

# log versions

def lkb(s, k, b):
    return k - b * s

def residual_lkb(ref, work, params):

    k, b = params

    res = sum([math.pow(r[1] - w[1] - lkb(w[0], k, b), 2) \
               for r, w in zip(ref, work)])

    return res

def gradients_lkb(ref, work, params):

    eps = 1.0e-6

    g = flex.double()

    for j in range(2):
        rs = []
        for signed_eps in [- eps, eps]:
            params_eps = params[:]
            params_eps[j] += signed_eps
            rs.append(residual_lkb(ref, work, params_eps))
        g.append((rs[1] - rs[0]) / (2 * eps))

    return g

class lkb_scaler:

    def __init__(self, ref, work):

        self.x = flex.double([0.0, 0.0])
        self._ref = [(r[0], math.log(r[1])) for r in ref]
        self._work = [(w[0], math.log(w[1])) for w in work]

        return

    def refine(self):

        return lbfgs.run(target_evaluator = self)

    def compute_functional_and_gradients(self):

        return residual_lkb(self._ref, self._work, self.x), \
               gradients_lkb(self._ref, self._work, self.x)

    def get_kb(self):
        return math.exp(self.x[0]), self.x[1]

def lkb_scale(ref, work):
    '''Scale work to reference via scale factor of the form

    Ir = Iw * K * exp(-Bs)

    returning k, B.'''

    lkbs = lkb_scaler(ref, work)
    lkbs.refine()

    return lkbs.get_kb()


if __name__ == '__main__':

    import random

    for size in [10 ** r for r in range(1, 5)]:

        print size

        k = 5
        b = 10

        ref = [(0.5 * random.random(), 10 * random.random()) \
               for j in range(size)]

        work = [(r[0], r[1] / kb(r[0], k, b)) for r in ref]

        kbs = kb_scaler(ref, work)

        kbs.refine()

        print 'Linear: %.2f %.2f' % kbs.get_kb()

        lkbs = lkb_scaler(ref, work)

        lkbs.refine()

        print 'Log:    %.2f %.2f' % kbs.get_kb()
