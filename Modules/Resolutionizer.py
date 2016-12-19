#!/usr/bin/env cctbx.python
# Resolutionizer.py
#
#   Copyright (C) 2013 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# A toolkit component for merging symmetry related intensity measurements
# to calculate:
#
#  - Rmerge vs. batch, resolution
#  - Chi^2
#  - Multiplicity
#  - Unmerged I/sigma
#  - Z^2 for centric and acentric reflections
#  - Completeness
#
# The standalone (moving to C++) version... FIXME use a DIALS ReflectionTable
# in here: this would be much faster.

import sys
import math
import os
import time
import itertools
import copy

from cctbx.array_family import flex
from cctbx.crystal import symmetry as crystal_symmetry
from cctbx.miller import build_set
from cctbx.miller import map_to_asu
from cctbx.sgtbx import rt_mx
from iotbx import mtz
import libtbx.phil
from scitbx import lbfgs

def nint(a):
  return int(round(a))

start_time = time.time()
def stamp(message):
  if False:
    print "[%7.3f] %s" % (time.time() - start_time, message)
  return

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

    tp = lbfgs.termination_parameters(max_iterations=1000)
    r = lbfgs.run(target_evaluator = self, termination_params=tp)
    return r

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

  stamp("fitter: %s %s %s" % (x, y, order))
  pf = poly_fitter(x, y, order)
  stamp("fitter: refine")
  pf.refine()
  stamp("fitter: done")

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

phil_str = '''
  rmerge = None
    .type = float(value_min=0)
    .help = "Maximum value of Rmerge in the outer resolution shell"
    .short_caption = "Outer shell Rmerge"
    .expert_level = 1
  completeness = None
    .type = float(value_min=0)
    .help = "Minimum completeness in the outer resolution shell"
    .short_caption = "Outer shell completeness"
    .expert_level = 1
  cc_half = 0.5
    .type = float(value_min=0)
    .help = "Minimum value of CC1/2 in the outer resolution shell"
    .short_caption = "Outer shell CC1/2"
    .expert_level = 1
  cc_half_significance_level = None
    .type = float(value_min=0, value_max=1)
    .expert_level = 1
  isigma = 0.25
    .type = float(value_min=0)
    .help = "Minimum value of the unmerged <I/sigI> in the outer resolution shell"
    .short_caption = "Outer shell unmerged <I/sigI>"
    .expert_level = 1
  misigma = 1.0
    .type = float(value_min=0)
    .help = "Minimum value of the merged <I/sigI> in the outer resolution shell"
    .short_caption = "Outer shell merged <I/sigI>"
    .expert_level = 1
  nbins = 100
    .type = int
    .help = "Number of resolution bins to use for estimation of resolution limit."
    .short_caption = "Number of resolution bins."
    .expert_level = 1
  binning_method = *counting_sorted volume
    .type = choice
    .help = "Use equal-volume bins or bins with approximately equal numbers of reflections per bin."
    .short_caption = "Equal-volume or equal #ref binning."
    .expert_level = 1
  anomalous = False
    .type = bool
    .short_caption = "Keep anomalous pairs separate in merging statistics"
    .expert_level = 1
'''


phil_defaults = libtbx.phil.parse('''
resolutionizer {
%s
  batch_range = None
    .type = ints(size=2, value_min=0)
  plot = False
    .type = bool
    .expert_level = 2
}
''' %phil_str)


class resolution_plot(object):
  def __init__(self, ylabel):
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import pyplot
    pyplot.style.use('ggplot')
    self.ylabel = ylabel
    self.fig = pyplot.figure()
    self.ax = self.fig.add_subplot(111)

  def plot(self, d_star_sq, values, label):
    self.ax.plot(d_star_sq, values, label=label)

  def plot_resolution_limit(self, d):
    from cctbx import uctbx
    d_star_sq = uctbx.d_as_d_star_sq(d)
    self.ax.plot([d_star_sq, d_star_sq], self.ax.get_ylim(), linestyle='--')

  def savefig(self, filename):
    from cctbx import uctbx
    xticks = self.ax.get_xticks()
    xticks_d = [
      '%.2f' %uctbx.d_star_sq_as_d(ds2) if ds2 > 0 else 0 for ds2 in xticks]
    self.ax.set_xticklabels(xticks_d)
    self.ax.set_xlabel('Resolution (A)')
    self.ax.set_ylabel(self.ylabel)
    self.ax.legend(loc='best')
    self.fig.savefig(filename)


class resolutionizer(object):
  '''A class to calculate things from merging reflections.'''

  def __init__(self, scaled_unmerged, params):

    self._params = params

    import iotbx.merging_statistics
    i_obs = iotbx.merging_statistics.select_data(scaled_unmerged, data_labels=None)
    i_obs = i_obs.customized_copy(anomalous_flag=True, info=i_obs.info())

    self._merging_statistics = iotbx.merging_statistics.dataset_statistics(
      i_obs=i_obs,
      n_bins=self._params.nbins,
      cc_one_half_significance_level=self._params.cc_half_significance_level,
      binning_method=self._params.binning_method,
      anomalous=params.anomalous,
      use_internal_variance=False,
      eliminate_sys_absent=False,
    )

    return

  def resolution_auto(self):
    '''Compute resolution limits based on the current self._params set.'''

    if self._params.rmerge:
      stamp("ra: rmerge")
      print 'Resolution rmerge:       %.2f' % \
          self.resolution_rmerge()

    if self._params.completeness:
      stamp("ra: comp")
      print 'Resolution completeness: %.2f' % \
          self.resolution_completeness()

    if self._params.cc_half:
      stamp("ra: cc")
      print 'Resolution cc_half     : %.2f' % \
          self.resolution_cc_half()

    if self._params.isigma:
      stamp("ra: isig")
      print 'Resolution I/sig:        %.2f' % \
          self.resolution_unmerged_isigma()

    if self._params.misigma:
      stamp("ra: mnisig")
      print 'Resolution Mn(I/sig):    %.2f' % \
          self.resolution_merged_isigma()

    return

  def resolution_rmerge(self, limit = None, log = None):
    '''Compute a resolution limit where either rmerge = 1.0 (limit if
    set) or the full extent of the data. N.B. this fit is only meaningful
    for positive values.'''

    if limit is None:
      limit = self._params.rmerge

    rmerge_s = flex.double(
      [b.r_merge for b in self._merging_statistics.bins]).reversed()
    s_s = flex.double(
      [1/b.d_min**2 for b in self._merging_statistics.bins]).reversed()

    sel = rmerge_s > 0
    rmerge_s = rmerge_s.select(sel)
    s_s = s_s.select(sel)

    if limit == 0.0:
      return 1.0 / math.sqrt(flex.max(s_s))

    if limit > flex.max(rmerge_s):
      return 1.0 / math.sqrt(flex.max(s_s))

    rmerge_f = log_inv_fit(s_s, rmerge_s, 6)

    if log:
      fout = open(log, 'w')
      for j, s in enumerate(s_s):
        d = 1.0 / math.sqrt(s)
        o = rmerge_s[j]
        m = rmerge_f[j]
        fout.write('%f %f %f %f\n' % (s, d, o, m))
      fout.close()

    try:
      r_rmerge = 1.0 / math.sqrt(interpolate_value(s_s, rmerge_f, limit))
    except:
      r_rmerge = 1.0 / math.sqrt(flex.max(s_s))

    if self._params.plot:
      plot = resolution_plot(ylabel='Rmerge')
      plot.plot(s_s, rmerge_f, label='fit')
      plot.plot(s_s, rmerge_s, label='Rmerge')
      plot.plot_resolution_limit(r_rmerge)
      plot.savefig('rmerge.png')

    return r_rmerge

  def resolution_unmerged_isigma(self, limit = None, log = None):
    '''Compute a resolution limit where either I/sigma = 1.0 (limit if
    set) or the full extent of the data.'''

    if limit is None:
      limit = self._params.isigma

    isigma_s = flex.double(
      [b.unmerged_i_over_sigma_mean for b in self._merging_statistics.bins]).reversed()
    s_s = flex.double(
      [1/b.d_min**2 for b in self._merging_statistics.bins]).reversed()

    sel = isigma_s > 0
    isigma_s = isigma_s.select(sel)
    s_s = s_s.select(sel)

    if flex.min(isigma_s) > limit:
      return 1.0 / math.sqrt(flex.max(s_s))

    isigma_f = log_fit(s_s, isigma_s, 6)

    if log:
      fout = open(log, 'w')
      for j, s in enumerate(s_s):
        d = 1.0 / math.sqrt(s)
        o = isigma_s[j]
        m = isigma_f[j]
        fout.write('%f %f %f %f\n' % (s, d, o, m))
      fout.close()

    try:
      r_isigma = 1.0 / math.sqrt(interpolate_value(s_s, isigma_f, limit))
    except:
      r_isigma = 1.0 / math.sqrt(flex.max(s_s))

    if self._params.plot:
      plot = resolution_plot(ylabel='Unmerged I/sigma')
      plot.plot(s_s, isigma_f, label='fit')
      plot.plot(s_s, isigma_s, label='Unmerged I/sigma')
      plot.plot_resolution_limit(r_isigma)
      plot.savefig('isigma.png')

    return r_isigma

  def resolution_merged_isigma(self, limit = None, log = None):
    '''Compute a resolution limit where either Mn(I/sigma) = 1.0 (limit if
    set) or the full extent of the data.'''

    if limit is None:
      limit = self._params.misigma

    misigma_s = flex.double(
      [b.i_over_sigma_mean for b in self._merging_statistics.bins]).reversed()
    s_s = flex.double(
      [1/b.d_min**2 for b in self._merging_statistics.bins]).reversed()

    sel = misigma_s > 0
    misigma_s = misigma_s.select(sel)
    s_s = s_s.select(sel)

    if flex.min(misigma_s) > limit:
      return 1.0 / math.sqrt(flex.max(s_s))

    misigma_f = log_fit(s_s, misigma_s, 6)

    if log:
      fout = open(log, 'w')
      for j, s in enumerate(s_s):
        d = 1.0 / math.sqrt(s)
        o = misigma_s[j]
        m = misigma_f[j]
        fout.write('%f %f %f %f\n' % (s, d, o, m))
      fout.close()

    try:
      r_misigma = 1.0 / math.sqrt(
          interpolate_value(s_s, misigma_f, limit))
    except:
      r_misigma = 1.0 / math.sqrt(flex.max(s_s))

    if self._params.plot:
      plot = resolution_plot(ylabel='Merged I/sigma')
      plot.plot(s_s, misigma_f, label='fit')
      plot.plot(s_s, misigma_s, label='Merged I/sigma')
      plot.plot_resolution_limit(r_misigma)
      plot.savefig('misigma.png')

    return r_misigma

  def resolution_completeness(self, limit = None, log = None):
    '''Compute a resolution limit where completeness < 0.5 (limit if
    set) or the full extent of the data. N.B. this completeness is
    with respect to the *maximum* completeness in a shell, to reflect
    triclinic cases.'''

    if limit is None:
      limit = self._params.completeness

    comp_s = flex.double(
      [b.completeness for b in self._merging_statistics.bins]).reversed()
    s_s = flex.double(
      [1/b.d_min**2 for b in self._merging_statistics.bins]).reversed()

    if flex.min(comp_s) > limit:
      return 1.0 / math.sqrt(flex.max(s_s))

    comp_f = fit(s_s, comp_s, 6)

    rlimit = limit * max(comp_s)

    if log:
      fout = open(log, 'w')
      for j, s in enumerate(s_s):
        d = 1.0 / math.sqrt(s)
        o = comp_s[j]
        m = comp_f[j]
        fout.write('%f %f %f %f\n' % (s, d, o, m))
      fout.close()

    try:
      r_comp = 1.0 / math.sqrt(
          interpolate_value(s_s, comp_f, rlimit))
    except Exception:
      r_comp = 1.0 / math.sqrt(flex.max(s_s))

    if self._params.plot:
      plot = resolution_plot(ylabel='Completeness')
      plot.plot(s_s, comp_f, label='fit')
      plot.plot(s_s, comp_s, label='Completeness')
      plot.plot_resolution_limit(r_comp)
      plot.savefig('completeness.png')

    return r_comp

  def resolution_cc_half(self, limit = None, log = None):
    '''Compute a resolution limit where cc_half < 0.5 (limit if
    set) or the full extent of the data.'''

    if limit is None:
      limit = self._params.cc_half

    cc_s = flex.double(
      [b.cc_one_half for b in self._merging_statistics.bins]).reversed()
    s_s = flex.double(
      [1/b.d_min**2 for b in self._merging_statistics.bins]).reversed()

    p = self._params.cc_half_significance_level
    if p is not None:
      significance = flex.bool(
        [b.cc_one_half_significance for b in self._merging_statistics.bins]).reversed()
      cc_half_critical_value = flex.double(
        [b.cc_one_half_critical_value for b in self._merging_statistics.bins]).reversed()
      # index of last insignificant bin
      i = flex.last_index(significance, False)
      if i is None or i == len(significance) - 1:
        i = 0
      else:
        i += 1
    else:
      i = 0
    cc_f = fit(s_s[i:], cc_s[i:], 6)

    stamp("rch: fits")
    rlimit = limit * max(cc_s)

    if log:
      fout = open(log, 'w')
      for j, s in enumerate(s_s):
        d = 1.0 / math.sqrt(s)
        o = cc_s[j]
        m = cc_f[j]
        fout.write('%f %f %f %f\n' % (s, d, o, m))
      fout.close()

    try:
      r_cc = 1.0 / math.sqrt(
          interpolate_value(s_s[i:], cc_f, rlimit))
    except:
      r_cc = 1.0 / math.sqrt(max(s_s[i:]))
    stamp("rch: done : %s" % r_cc)

    if self._params.plot:
      plot = resolution_plot('CC1/2')
      plot.plot(s_s[i:], cc_f, label='fit')
      plot.plot(s_s, cc_s, label='CC1/2')
      if p is not None:
        plot.plot(
          s_s, cc_half_critical_value, label='Confidence limit (p=%g)' %p)
      plot.plot_resolution_limit(r_cc)
      plot.savefig('cc_half.png')

    return r_cc

def run(args):
  working_phil = phil_defaults
  interp = working_phil.command_line_argument_interpreter(
    home_scope='resolutionizer')
  params, unhandled = interp.process_and_fetch(
    args, custom_processor='collect_remaining')
  params = params.extract().resolutionizer
  assert len(unhandled)
  scaled_unmerged = unhandled[0]

  stamp("Resolutionizer.py starting")
  m = resolutionizer(scaled_unmerged, params)
  stamp("instantiated")
  m.resolution_auto()
  stamp("the end.")


if __name__ == '__main__':
  run(sys.argv[1:])
