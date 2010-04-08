import math

from cctbx.array_family import flex
from scitbx import lbfgs

def kb(s, k, b):
    return k * math.exp(-1 * b * s)

def residual_kb(ref, work, params):
    
    k, b = params

    res = sum([math.fabs(r[1] - w[1] * kb(w[0], k, b)) \
               for r, w in zip(ref, work)]) / \
               sum(math.fabs(r[1]) for r in ref)

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

class kb_scale:

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
        
if __name__ == '__main__':

    import random

    k = 5
    b = 10

    ref = [(random.random(), random.random()) for k in range(1000)]

    work = [(r[0], r[1] / kb(r[0], k, b)) for r in ref]

    print residual_kb(ref, work, (1, 0))
    print residual_kb(ref, work, (k, b))

    kbs = kb_scale(ref, work)

    kbs.refine()

    k2, b2 = kbs.get_kb()

    print k2, b2

    print residual_kb(ref, work, (k2, b2))
