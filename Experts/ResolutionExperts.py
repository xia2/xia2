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
import tempfile
import shutil
import time

from xia2.Wrappers.CCP4.Pointless import Pointless
from xia2.Wrappers.CCP4.Mtzdump import Mtzdump
from xia2.Wrappers.CCP4.Rebatch import Rebatch
from xia2.Handlers.Streams import Debug
from xia2.Handlers.Flags import Flags

# global parameters

def nint(a):
  i = int(a)
  if a - i >= 0.5:
    i += 1

  return i

_scale_bins = 0.004
_number_bins = nint(2.0 / _scale_bins)

# jiffy functions

def _small_molecule():
  '''Switch the settings to small molecule mode!'''

  global _scale_bins, _number_bins
  _scale_bins = 0.04
  _number_bins = nint(2.0 / _scale_bins)
  return

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

  a_s = b * c * sa / V
  b_s = c * a * sb / V
  c_s = a * b * sg / V

  # compute reciprocal angles

  cas = (cb * cg - ca) / (sb * sg)
  cbs = (ca * cg - cb) / (sa * sg)
  cgs = (ca * cb - cg) / (sa * sb)

  alphas = math.acos(cas) / rtod
  betas = math.acos(cbs) / rtod
  gammas = math.acos(cgs) / rtod

  return a_s, b_s, c_s, alphas, betas, gammas

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

  if not values:
    return 0.0, 0.0

  if len(values) == 1:
    return values[0], 0.0

  mean = sum(values) / len(values)
  sd = 0.0

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

  a_s, b_s, c_s, alphas, betas, gammas = real_to_reciprocal(
      a, b, c, alpha, beta, gamma)

  a_, b_, c_ = B(a_s, b_s, c_s, alphas, betas, gammas)

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

class ResolutionCell(object):
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

class ResolutionGeometry(object):
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

    s, r = rc.resolution(h, k, l)

    result.append((s, i, sigma))

  return result

def mosflm_mtz_to_list(mtz):
  '''Run pointless to convert mtz to list of h k l ... and give the
  unit cell, then convert this to a list as necessary before returning.'''

  hklout = tempfile.mktemp('.hkl', '', os.environ['CCP4_SCR'])

  p = Pointless()
  p.set_hklin(mtz)
  cell = p.sum_mtz(hklout)

  hkl = pointless_summedlist_to_list(hklout, cell)

  os.remove(hklout)

  return hkl

def pointless_summedlist_to_list(summedlist, cell):
  '''Parse the output of a pointless summedlist to a list of
  (s, i, sigma) as above, using the unit cell to calculate the
  resolution of reflections.'''

  a, b, c, alpha, beta, gamma = cell

  rc = ResolutionCell(a, b, c, alpha, beta, gamma)

  result = []

  for record in open(summedlist, 'r').readlines():
    lst = record.split()

    if not lst:
      continue

    h, k, l = tuple(map(int, lst[:3]))

    i, sigma = tuple(map(float, lst[4:6]))

    s, r = rc.resolution(h, k, l)

    result.append((s, i, sigma))

  return result

def find_blank(hklin):

  # first dump to temp. file
  hklout = tempfile.mktemp('.hkl', '', os.environ['CCP4_SCR'])

  p = Pointless()
  p.set_hklin(hklin)
  cell = p.sum_mtz(hklout)

  if not os.path.isfile(hklout):
    Debug.write('Pointless failed:')
    Debug.write(''.join(p.get_all_output()))
    raise RuntimeError('Pointless failed: %s does not exist' %hklout)

  isig = { }

  for record in open(hklout, 'r'):
    lst = record.split()
    if not lst:
      continue
    batch = int(lst[3])
    i, sig = float(lst[4]), float(lst[5])

    if not sig:
      continue

    if not batch in isig:
      isig[batch] = []

    isig[batch].append(i / sig)

  # look at the mean and sd

  blank = []
  good = []

  for batch in sorted(isig):
    m, s = meansd(isig[batch])
    if m < 1:
      blank.append(batch)
    else:
      good.append(batch)

  # finally delete temp file
  os.remove(hklout)

  return blank, good

def remove_blank(hklin, hklout):
  '''Find and remove blank batches from the file. Returns hklin if no
  blanks.'''

  blanks, goods = find_blank(hklin)

  if not blanks:
    return hklin

  # if mostly blank return hklin too...
  if len(blanks) > len(goods):
    Debug.write('%d blank vs. %d good: ignore' % (len(blanks), len(goods)))
    return hklin

  rb = Rebatch()
  rb.set_hklin(hklin)
  rb.set_hklout(hklout)

  for b in blanks:
    rb.exclude_batch(b)

  rb.exclude_batches()

  return hklout

def bin_o_tron0(sisigma):
  '''Bin the incoming list of (s, i, sigma) and return a list of bins
  of width _scale_bins in S.'''

  bins = {}

  for j in range(_number_bins):
    bins[j + 1] = []

  for sis in sisigma:
    s, i, sigma = sis

    qs = nint(0.5 * _number_bins * s)

    if qs in bins:
      bins[qs].append((i / sigma))

  result = { }

  for j in range(_number_bins):
    result[_scale_bins * (j + 1)] = meansd(bins[j + 1])

    if False:
      print result[_scale_bins * (j + 1)][0], \
            result[_scale_bins * (j + 1)][1], \
            len(bins[j + 1])

  return result

def outlier(sisigma):
  ''' Finely bin the reflections, then look for outlier regions -
  if these are found, remove the reflections in that region from
  the list, then return the edited list.'''

  # first bin the measurements

  t0 = time.time()

  bins = {}

  for j in range(500):
    bins[j + 1] = []

  for sis in sisigma:
    s, i, sigma = sis

    qs = nint(0.5 * 500 * s)

    if qs in bins:
      bins[qs].append((i / sigma))


  # then look for outliers... first calculate the mean in each bin...

  result = { }
  keys = []

  fout = open('q.txt', 'w')

  for j in range(500):
    result[0.004 * (j + 1)] = meansd(bins[j + 1])
    keys.append(0.004 * (j + 1))

    fout.write('%f %f %f\n' % (0.004 * (j + 1),
                               result[0.004 * (j + 1)][0],
                               result[0.004 * (j + 1)][1]))

  fout.close()

  # then look to see which bins don't fit

  outliers = []

  for j in range(4, 500 - 4):
    k_m2 = keys[j - 2]
    k_m1 = keys[j - 1]
    k_p1 = keys[j + 1]
    k_p2 = keys[j + 2]

    k = keys[j]

    m_m2 = result[k_m2][0]
    m_m1 = result[k_m1][0]
    m_p1 = result[k_p1][0]
    m_p2 = result[k_p2][0]

    if result[k][0] > 5 * (0.5 * (m_m1 + m_p1)):
    # if result[k][0] > 5 * min([m_m2, m_m1, m_p1, m_p2]):
      if not k in outliers:
        outliers.append(k)

  # now remove these from the list - brutal - just excise completely!

  sisigma_new = []

  limit = min(outliers)

  for sis in sisigma:
    s = sis[0]
    keep = True
    # for o in outliers:
    # if math.fabs(s - o) < 0.004:
    # keep = False

    if s > limit:
      keep = False

    if keep:
      sisigma_new.append(sis)

  return sisigma_new

def bin_o_tron(sisigma):
  '''Bin the incoming list of (s, i, sigma) and return a list of bins
  of width _scale_bins in S.'''

  # first reject the outliers - nope, let's not...

  # sisigma = outlier(sisigma)

  bins_i = { }
  bins_s = { }

  for j in range(_number_bins):
    bins_i[j + 1] = []
    bins_s[j + 1] = []

  for sis in sisigma:
    s, i, sigma = sis

    qs = nint(0.5 * _number_bins * s)

    if qs in bins_i:
      bins_i[qs].append(i)
      bins_s[qs].append(sigma)

  result = { }

  for j in range(_number_bins):
    msd = meansd(bins_i[j + 1])
    result[_scale_bins * (j + 1)] = (msd[0], msd[1],
                                     meansd(bins_s[j + 1])[0])

    if False:
      print result[_scale_bins * (j + 1)][0], \
            result[_scale_bins * (j + 1)][1], \
            len(bins[j + 1])


  return result


def linear(x, y):

  _x = sum(x) / len(x)
  _y = sum(y) / len(y)

  sumxx = 0.0
  sumxy = 0.0

  for j in range(len(x)):

    sumxx += (x[j] - _x) * (x[j] - _x)
    sumxy += (x[j] - _x) * (y[j] - _y)

  m = sumxy / sumxx

  c = _y - _x * m

  return m, c

def ice(s):
  '''Could the reflection with inverse resolution s be in an ice ring?
  calculated from XDS example input...'''

  if s >= 0.065 and s <= 0.067:
    return True
  if s >= 0.073 and s <= 0.075:
    return True
  if s >= 0.083 and s <= 0.086:
    return True
  if s >= 0.137 and s <= 0.143:
    return True
  if s >= 0.192 and s <= 0.203:
    return True
  if s >= 0.226 and s <= 0.240:
    return True
  if s >= 0.264 and s <= 0.281:
    return True

  return False


def digest(bins, isigma_limit = 1.0):
  '''Digest a list of bins to calculate a sensible resolution limit.'''

  # print 'Debugging! isigma_limit = %f' % isigma_limit

  ss = bins.keys()

  ss.sort()

  for j in range(_number_bins):
    s = ss[j]
    mean, sdm, sd = bins[s]

    if False:
      print s, 1.0 / math.sqrt(s), mean, sd

  # ok, really the first thing I need to do is see if the reflections
  # fall off the edge of the detector - i.e. this is a close-in low
  # resolution set with I/sig >> 1 at the edge...

  _mean = []
  _s = []

  for j in range(_number_bins):
    s = ss[j]
    mean, sdm, sd = bins[s]

    if mean > 0:
      _mean.append(mean / sd)
      _s.append(s)
      smax = s

  # allow a teeny bit of race - ignore the last resolution bin
  # in this calculation...

  if min(_mean[:-1]) > isigma_limit:
    # we have a data set which is all I/sigma > 1.0
    s = max(_s)
    r = 1.0 / math.sqrt(s)
    return s, r

  # first find the area where mean(I/s) ~ sd(I/s) on average - this defines
  # the point where the distribution is "Wilson like". Add a fudge factor of
  # 10% for good measure. Start a little way off the beginning e.g. at 10A.

  # panic - fixme - this should be SPREAD not mean error.

  for j in range(nint(0.01 * _number_bins), _number_bins):
    s = ss[j]
    mean, sdm, sd = bins[s]

    if sdm > 0.9 * mean:
      j0 = j
      s0 = s
      break

  # now wade through until we get the first point where mean(I/s) ~ 1

  for j in range(j0, _number_bins):
    s = ss[j]
    mean, sdm, sd = bins[s]

    if sd == 0.0:
      continue

    if (mean / sd) <= isigma_limit:
      s1 = s
      j1 = j
      break

  Debug.write('Selected resolution range: %.2f to %.2f for Wilson fit' %
              (1.0 / math.sqrt(s0), 1.0 / math.sqrt(s1)))

  # now decide if it is appropriate to consider a fit to a Wilson
  # distribution... FIXME need to make a decision about this

  # then actually do the fit... excluding ice rings of course

  x = []
  y = []

  if j0 + 1 >= j1:
    # we need to do this differently... just count down the bins
    # until I/sigma < 1 - actually this is already s1
    r1 = 1.0 / math.sqrt(s1)

    return s1, r1

  for j in range(j0, j1):
    s = ss[j]

    if ice(s):
      continue

    mean, sdm, sd = bins[s]

    x.append(s)
    y.append(math.log10(mean / sd))

  m, c = linear(x, y)

  L = math.log10(isigma_limit)

  if False:
    for isigma in 1.0, 2.0, 3.0, 4.0, 5.0:
      s = (math.log10(isigma) - c) / m
      print 'Debugging again... %.1f %.2f' % (isigma, 1.0 / math.sqrt(s))

  s = (L - c) / m

  # logic really - limit the resolution limit estimate to the
  # highest resolution we have, as we can't predict what will
  # happen outside the known range.

  if s > smax:
    s = smax

  r = 1.0 / math.sqrt(s)

  return s, r

if __name__ == '__main__':

  bot = bin_o_tron(xds_integrate_hkl_to_list(sys.argv[1]))

  for b in sorted(bot):
    mean, spread, sigma = bot[b]
    if mean:
      print 1.0 / math.sqrt(b), mean, spread, sigma, mean / sigma

  s, r = digest(bot)

  print s, r
