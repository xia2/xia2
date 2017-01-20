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

from __future__ import absolute_import, division

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

class poly_fitter(object):
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

def get_positive_values(x):
  '''Return a list of values v from x where v > 0.'''

  result = []

  for _x in x:
    if _x > 0:
      result.append(_x)
    else:
      return result

  return result


if __name__ == '__main__':

  # trying to work out why something is slow...

  x = [0.28733375585344956, 0.3336648239480671, 0.37392475503798783, 0.4116791460480823, 0.44667362480391215, 0.48010999459819637, 0.5123842907520316, 0.5445830447029069, 0.5747600267080056, 0.605268188207491, 0.6348694178757428, 0.6628307139444256, 0.6915543733106164, 0.7190850546688736, 0.7466325833791124, 0.7726534107667972, 0.7991813564734889, 0.8246120592630442, 0.8509431563671859, 0.8752222362981207, 0.9003835108822839, 0.925531251174205, 0.9495577347489563, 0.9736107180716824, 0.9977616739729435, 1.0211126767435303, 1.0442229585861016, 1.0676870644761218, 1.089626948783452, 1.11325323064326, 1.1353748686331517, 1.157229309091089, 1.1793787289152926, 1.2012850147174827, 1.223192876382562, 1.2442806850714754, 1.2659456255540278, 1.2868725763092403, 1.3077684542819044, 1.329693962546648, 1.3497661431014192, 1.3703975279412275, 1.3913213083813614, 1.4118099020522166, 1.431944241466548, 1.451565968015303, 1.4726043408387703, 1.4926361862881505, 1.511947564871118, 1.531623424311822, 1.5518379642619582, 1.571415292664728, 1.590956013986232, 1.6101289757746151, 1.629504706812003, 1.6488436799317054, 1.6677873136267631, 1.6871236000102316, 1.7063804384195065, 1.7247788587316706, 1.74385084639364, 1.7632567530747427, 1.7810671017919066, 1.8000204739946506, 1.8187750413718835, 1.8362045669565548, 1.855888986697667, 1.8736099866108273, 1.8919543734165152, 1.9099014671201333, 1.9278705840578851, 1.9459285536685293, 1.9644838792250359, 1.9822046837796143, 1.9995268983422625, 2.0173386661672104, 2.0350303628559123, 2.0527713302473805, 2.0715436512758125, 2.088532979967127, 2.105448870913261, 2.122996752747121, 2.140658402767489, 2.1580900095590096, 2.1754356707821283, 2.19275774398331, 2.211194475389986, 2.232982621587298, 2.2551925602858534, 2.280016719289489, 2.3063211626596343, 2.3350430868315497, 2.3665452139200425, 2.4015454429869205, 2.440733908945748, 2.4858785233713427, 2.5418727931246536, 2.6144084555616858, 2.7959062808147896]
  y = [24.77724034532261, 24.37804249554226, 24.19024290469251, 24.060132497289498, 23.78910669554878, 23.490999254422075, 23.230491536468016, 23.05617339327898, 22.64620165329114, 22.579695553808385, 22.383003610771798, 22.262032410277936, 22.21201767180415, 21.93212194269467, 21.726772939444658, 21.460467444724543, 21.27059568803877, 21.06466968773921, 20.634888404569303, 20.238281789327637, 19.672916110100605, 19.546897202422976, 18.87739359459743, 18.59488191380871, 18.14880392608624, 17.6962994383689, 17.37710441451018, 16.81250842496295, 16.678882667587086, 16.182391499497715, 15.828587302315464, 15.205433904690839, 14.495596165710925, 14.511859823120211, 13.971753232798177, 13.658395498023248, 13.366842896276086, 13.05856744427929, 12.337465723961392, 12.29682965701954, 12.147839110097841, 11.760324551597702, 11.471407424003074, 11.049213704891022, 10.919965795059092, 10.601626749506291, 10.335411804585565, 9.718082839773091, 9.585767093427409, 9.423114689530454, 9.251666562241514, 9.124491493213558, 8.906324740537787, 8.29969595224133, 8.179515265478527, 8.078946904786891, 8.074081206125799, 7.795640184700349, 7.327064345560753, 7.180371145672737, 6.982901221348126, 6.831549776236767, 6.774329916623371, 6.598455395485047, 6.242034228013543, 6.211893244192715, 5.978124228824288, 5.616738659970417, 5.760183273642267, 5.255614400544779, 5.040337222517639, 4.970512178822339, 4.967344687551919, 4.548778129253488, 4.451021806395992, 4.264074612710173, 4.067343853822604, 4.043692161771108, 3.6569324304568642, 3.727811294231763, 3.4954349302961947, 3.345749115417511, 3.2665114375808058, 3.1220011432385397, 2.8973373248698233, 2.853040292102494, 2.713019895460359, 2.573460999432591, 2.4801019159829423, 2.2829226930395405, 2.1913185826611636, 2.0872962418506518, 1.9316795102089115, 1.6848508083758817, 1.5530229534306241, 1.361701873571922, 1.1916682079143257, 1.053122785634863, 0.771132065724789]

  m = log_fit(x, y, 6)

  for j in range(len(x)):
    print x[j], y[j], m[j]
