# Refine list of space group candidate and HKL indices against observed 2theta values.

from cctbx import miller, uctbx
from cctbx.array_family import flex
import scitbx.lbfgs
import random

class _refinery:
  # Modelled after cctbx/examples/unit_cell_refinement.py

  def __init__(self, two_thetas_obs, miller_indices, wavelength, unit_cell, lattice=None):
    self.two_thetas_obs = two_thetas_obs
    self.miller_indices = miller_indices
    self.wavelength = wavelength
    self.lattice = lattice

    self.restraints, self.constraints, self.side_constraints = {}, {}, {}
    if lattice == 'm':
      self.restraints = { 3:90, 5:90 } # alpha, gamma = 90
      self.constraints = { 4:90 } # beta >= 90

    elif lattice == 'o':
      self.restraints = { 3:90, 4:90, 5:90 }

    elif lattice == 't':
      self.restraints = { 3:90, 4:90, 5:90 }
      self.side_constraints = { 1: 0 } # b = a

    elif lattice == 'h':
      self.restraints = { 3:90, 4:90, 5:120 }
      self.side_constraints = { 1: 0 }

    elif lattice == 'c':
      self.restraints = { 3:90, 4:90, 5:90 }
      self.side_constraints = { 1: 0, 2: 0 } # b = a, c = a

    self.x = flex.double(unit_cell.parameters())
    scitbx.lbfgs.run(target_evaluator=self)

  def unit_cell(self):
    params = list(self.x)
    for tgt, src in self.side_constraints.iteritems():
      params[tgt] = params[src]
    for ang, const in self.restraints.iteritems():
      params[ang] = const
    for ang, minval in self.constraints.iteritems():
      params[ang] = max(params[ang], minval)
    return uctbx.unit_cell(params)

  def compute_functional_and_gradients(self):
    unit_cell = self.unit_cell()
    f = self.residual(unit_cell)
    g = self.gradients(unit_cell, lattice=self.lattice)
#   print "cell ", unit_cell
#   print "functional: %12.6g" % f, "gradient norm: %12.6g" % g.norm()
    return f, g

  def callback_after_step(self, minimizer):
    pass

  def residual(self, unit_cell):
    two_thetas_calc = unit_cell.two_theta(self.miller_indices, self.wavelength, deg=True)
    return flex.sum(flex.pow2(self.two_thetas_obs - two_thetas_calc))

  def gradients(self, unit_cell, eps=1.e-6, lattice=None):
    result = flex.double()

    for i in xrange(6):
      if i in self.restraints:
        result.append(0)
        continue
      if i in self.constraints: # naive
        if (list(unit_cell.parameters())[i] < self.constraints[i]):
          result.append(-1)
          continue
        if (list(unit_cell.parameters())[i] == self.constraints[i]):
          result.append(0)
          continue
      if i in self.side_constraints:
        result.append(0)
        continue
      rs = []
      for signed_eps in [eps, -eps]:
        params_eps = list(unit_cell.parameters())
        params_eps[i] += signed_eps
        rs.append(self.residual(uctbx.unit_cell(params_eps)))
      result.append((rs[0]-rs[1])/(2*eps))
    return result

  def show_fit(self, unit_cell):
    two_thetas_calc = unit_cell.two_theta(self.miller_indices, self.wavelength, deg=True)
    for h,o,c in zip(self.miller_indices, self.two_thetas_obs, two_thetas_calc):
      print "(%2d, %2d, %2d)" % h, "%6.2f - %6.2f = %6.2f" % (o, c, o-c)
    print
