from __future__ import division

import iotbx.phil
from scitbx import matrix
from cctbx.crystal import symmetry
from libtbx.utils import Usage, multi_out
import sys
from xfel.cxi.util import is_odd_numbered # implicit import
from xfel.command_line.cxi_merge import master_phil
from xfel.command_line.cxi_xmerge import xscaling_manager

# supporting functions

def meansd(values):
  import math

  assert(len(values) > 1)
    
  mean = sum(values) / len(values)
  var = sum([(v - mean) ** 2 for v in values]) / len(values - 1)
  return mean, math.sqrt(var)

def mean(values):
  return sum(values) / len(values)

def merge(observations):
  result = { }
  for hkl in observations:
    result[hkl] = sum(observations[hkl]) / len(observations[hkl])
    
  return result

def common_indices(set_a, set_b):
  indices_a = set([d.hkl for d in set_a])
  indices_b = set([d.hkl for d in set_b])

  return indices_a.intersection(indices_b)

def compute_cc(list_a, list_b):

  import math
    
  assert(len(list_a) == len(list_b))
  mean_a = sum(list_a) / len(list_a)
  mean_b = sum(list_b) / len(list_b)

  sum_aa = 0.0
  sum_ab = 0.0
  sum_bb = 0.0
  
  for a, b in zip(list_a, list_b):
    sum_aa += (a - mean_a) ** 2
    sum_ab += (a - mean_a) * (b - mean_b)
    sum_bb += (b - mean_b) ** 2

  try:
    return sum_ab / math.sqrt(sum_aa * sum_bb)
  except ZeroDivisionError, zde:
    return 0.0

def cc(set_a, set_b):
  merged_a = merge(set_a)
  merged_b = merge(set_b)

  _a = []
  _b = []

  for hkl in merged_a:
    if hkl in merged_b:
      _a.append(merged_a[hkl])
      _b.append(merged_b[hkl])
      
  if len(_a) == 0:
    return 0, 0.0

  return len(_a), compute_cc(_a, _b)    

def pairwise_product(set_a, set_b):
  merged_a = merge(set_a)
  merged_b = merge(set_b)

  _a = []
  _b = []

  for hkl in merged_a:
    if hkl in merged_b:
      _a.append(merged_a[hkl])
      _b.append(merged_b[hkl])

  if len(_a) == 0:
    return 0, 0.0

  import math

  result = sum([a * b for a, b in zip(_a, _b)]) / math.sqrt(
    sum([a ** 2 for a in _a]) * sum([b ** 2 for b in _b]))

  return len(_a), result

# supporting classes

class Scaler(object):
  '''A class to place data from different frames on a common scale using
  simple kB scaling. Initially use derivitive free minimiser.'''

  def __init__(self, unit_cell, indices, intensities, sigmas, frame_sizes):
    self._unit_cell = unit_cell
    self._indices = indices
    self._intensities = intensities
    self._sigmas = sigmas
    self._weights = [1.0 / (s ** 2) for s in sigmas]
    self._frame_sizes = frame_sizes

    self._scales_s = [0.0 for f in frame_sizes]
    self._scales_b = [0.0 for f in frame_sizes]

    self._compute_imean()

    self._target_evaluations = 0
        
    return

  def scale_factor(self, frame, hkl):
    '''Scale factor calculation. N.B. exponential form chosen for
    the overall frame scale to avoid negative scales.'''
    
    import math
    s = self._scales_s[frame]
    b = self._scales_b[frame]
    return math.exp(s + 2 * b * self._unit_cell.d_star_sq(hkl))
  
  def _compute_imean(self):
    self._imean = { }

    # numerator and denominator for calculations

    from collections import defaultdict
        
    imean_s_n = defaultdict(float)
    imean_s_d = defaultdict(float)
    
    # work through the lists

    j = 0
    
    for f, fs in enumerate(self._frame_sizes):
      for k in range(fs):
        hkl = self._indices[j]
        g_hl = self.scale_factor(f, hkl)
        n = self._intensities[j] * self._weights[j] * g_hl
        d = self._weights[j] * g_hl * g_hl

        # only include terms with non-zero weight
                
        imean_s_n[hkl] += n
        imean_s_d[hkl] += d

        j += 1
            
    assert(j == len(self._indices))

    for hkl in imean_s_n:
      self._imean[hkl] = imean_s_n[hkl] / imean_s_d[hkl]

    return

  def get_imean(self):
    return self._imean

  def get_scaled_intensities(self):
    return self._scaled_intensities
                
  def target(self, vector):
    
    # copy across the scale factors: first one is 0

    from scitbx.array_family import flex

    self._scales_s = flex.double(1, 0.0)
    self._scales_s.extend(vector[:len(self._frame_sizes) - 1])
    self._scales_b = flex.double(1, 0.0)
    self._scales_b.extend(vector[len(self._frame_sizes) - 1:])

    assert(len(self._scales_s) == len(self._frame_sizes))
    assert(len(self._scales_b) == len(self._frame_sizes))

    self._compute_imean()
        
    residual = 0.0

    j = 0

    for f, fs in enumerate(self._frame_sizes):
      for k in range(fs):
        hkl = self._indices[j]
        g_hl = self.scale_factor(f, hkl)
        residual += self._weights[j] * (
          self._intensities[j] - g_hl * self._imean[hkl]) ** 2
                
        j += 1

    # add a restraint term

    if False:
      restraint = sum([f * s ** 2 * b ** 2 for f, s, b in \
                       zip(self._frame_sizes, self._scales_s,
                           self._scales_b)])
                                                            
    assert(j == len(self._indices))
    self._target_evaluations += 1

    return residual
                
  def scale(self):
    '''Find scale factors s, b that minimise target function.'''

    from scitbx.direct_search_simulated_annealing import dssa
    from scitbx.simplex import simplex_opt
    
    from scitbx.array_family import flex

    # only scale second and subsequent scale factors - first ones are
    # constrained to 0.0
        
    self.n = 2 * len(self._frame_sizes) - 2
    self.x = flex.double(self._scales_s[1:] + self._scales_b[1:])
    self.starting_matrix = [self.x + flex.random_double(self.n) \
                            for j in range(self.n + 1)]

    if False:
      self.optimizer = dssa(dimension = self.n,
                            matrix = self.starting_matrix,
                            evaluator = self,
                            tolerance = 1.e-6,
                            further_opt = True)
    else:
      self.optimizer = simplex_opt(dimension = self.n,
                                   matrix = self.starting_matrix,
                                   evaluator = self,
                                   tolerance = 1.e-3)
      
    # save the best scale factors
             
    self.x = self.optimizer.get_solution()

    self._scales_s = flex.double(1, 0.0)
    self._scales_s.extend(self.x[:len(self._frame_sizes) - 1])
    self._scales_b = flex.double(1, 0.0)
    self._scales_b.extend(self.x[len(self._frame_sizes) - 1:])
    
    # scale the raw intensity data for later reference

    scaled_intensities = []
    
    for f, fs in enumerate(self._frame_sizes):
      for k in range(fs):
        hkl = self._indices[j]
        g_hl = self.scale_factor(f, hkl)
        scaled_intensities.append((self._intensities[j] / g_hl))

    self._scaled_intensities = scaled_intensities

    # now compute reflections with > 1 observation as starting point for
    # computing the Rmerge

    from collections import defaultdict
    multiplicity = defaultdict(list)

    for j, i in enumerate(self._indices):
      multiplicity[i].append(j)

    rmerge_n = 0.0
    rmerge_d = 0.0

    import math

    for i in multiplicity:
      if len(multiplicity[i]) == 1:
        continue
      imean = self._imean[i]
      for j in multiplicity[i]:
        rmerge_n += math.fabs(scaled_intensities[j] - imean)
        rmerge_d += imean
      
    return rmerge_n / rmerge_d

class Frame:
  '''A class to represent one set of intensity measurements from X-fel
  data collection.'''

  def __init__(self, unit_cell, indices, other, intensities, sigmas):
    self._unit_cell = unit_cell
    
    _indices = []
    _other = []
    _intensities = []
    _sigmas = []
    
    # limit only to relections with I/sigma(I) or more
    
    for j, i in enumerate(intensities):
      # FIXME should really exclude all observations with I/sigma < 3
      if i < 3 * sigmas[j]:
        continue
      _indices.append(indices[j])
      _other.append(other[j])
      _intensities.append(intensities[j])
      _sigmas.append(sigmas[j])
      
    assert(len(_indices) == len(_other))

    self._raw_indices = _indices
    self._raw_other = _other
    self._raw_intensities = _intensities
    self._raw_sigmas = _sigmas
    
    self._intensities = _intensities
    self._sigmas = _sigmas

    self._frames = 1
    self._frame_sizes = [len(_indices)]

    self._kb = None
        
    return

  def empty(self):
    self._raw_indices = []
    self._raw_other = []
    self._raw_intensities = []
    self._raw_sigmas = []
    
    self._intensities = []
    self._sigmas = []
    
    self._frames = 0
    self._frame_sizes = []
    
    return
  
  def __cmp__(self, other):
    return self._frames.__cmp__(other.get_frames())

  def get_frames(self):
    return self._frames

  def get_frame_sizes(self):
    return self._frame_sizes

  def get_intensities(self):
    return self._intensities
    
  def get_sigmas(self):
    return self._sigmas

  def get_raw_intensities(self):
    return self._raw_intensities
    
  def get_raw_sigmas(self):
    return self._raw_sigmas

  def get_indices(self):
    return self._raw_indices

  def get_unique_indices(self):
    return len(set(self._raw_indices))

  def get_other(self):
    return self._raw_other

  def get_unique_other(self):
    return len(set(self._raw_other))

  def get_intensity_dict(self):
    '''Useful for CC value between frames: FIXME this should be using the
    merged values from last scaling round.'''

    from collections import defaultdict

    result = defaultdict(list)

    for j in range(len(self._raw_indices)):
      hkl = self._raw_indices[j]
      i = self._intensities[j]
      
      result[hkl].append(i)

    return result

  def get_other_dict(self):
    '''Useful for CC value between frames: FIXME this should be using the
    merged values from last scaling round.'''

    from collections import defaultdict

    result = defaultdict(list)

    for j in range(len(self._raw_other)):
      hkl = self._raw_other[j]
      i = self._intensities[j]
      
      result[hkl].append(i)

    return result

  def normalize(self):
    '''Set scale: <I> = 1'''

    scale = sum(self._raw_intensities) / len(self._raw_intensities)
    
    self._intensities = [i / scale for i in self._raw_intensities]
    self._sigmas = [s / scale for s in self._raw_sigmas]
    
    return

  def cc(self, other):
        
    return cc(self.get_intensity_dict(), other.get_intensity_dict())

  def cc_other(self, other):
        
    return cc(self.get_intensity_dict(), other.get_other_dict())

  def reindex(self):
    # FIXME this should just switch the original and alternative indices
    self._raw_other, self._raw_indices = self._raw_indices, self._raw_other
    return
  
  def merge(self, other):
    '''Scale and merge frame data from this frame and the other.'''

    raw_indices = self._raw_indices + other.get_indices()
    raw_other = self._raw_other + other.get_other()
    raw_intensities = self._raw_intensities + other.get_raw_intensities()
    raw_sigmas = self._raw_sigmas + other.get_raw_sigmas()
    frame_sizes = self._frame_sizes + other.get_frame_sizes()

    # FIXME in here should provide previous scale factors as a
    # starting point - ideally could roughly scale the two sets of
    # scale factors together first but maybe not worth the effort

    # sometimes (rarely) the scaling just does not work: accept this and
    # move on, just act as if nothing was merged - the frame will not be
    # emptied so there is no cost.

    try:
      scaler = Scaler(self._unit_cell, raw_indices,
                      raw_intensities, raw_sigmas, frame_sizes)
      rmerge = scaler.scale()
    except ZeroDivisionError, zde:
      return None

    # and then in here I should grab the refined scale factors and
    # save them

    self._raw_indices = raw_indices
    self._raw_other = raw_other
    self._raw_intensities = raw_intensities
    self._raw_sigmas = raw_sigmas
    self._frame_sizes = frame_sizes
    
    self._intensities = scaler.get_scaled_intensities()

    self._frames += other.get_frames()
        
    # FIXME here empty other frame of reflections etc - do not need to worry
    # then about thrashing frame lists.
    
    other.empty()

    return rmerge

  def common(self, other):
    return len(set(self._raw_indices).intersection(
      set(other.get_indices())))

  def common_other(self, other):
    return len(set(self._raw_indices).intersection(
      set(other.get_other())))

  def kb(self):
    '''Compute estimates for the overall scale factor and B factor by
    linear regression of the intensity observations. N.B. fitting
    ln(I) on baseline of 1/d^2 '''
    
    import math
    
    x_obs = []
    y_obs = []
    weights = []
    
    for j, i in enumerate(self._raw_intensities):
      s = self._raw_sigmas[j]
      if i > s:
        x_obs.append(self._unit_cell.d_star_sq(self._raw_indices[j]))
        y_obs.append(math.log(i))
        weights.append((i / s) ** 2)

    _x = sum(x_obs) / len(x_obs)
    _y = sum(y_obs) / len(y_obs)

    B = sum([w * (x - _x) * (y - _y) for w, x, y in \
             zip(weights, x_obs, y_obs)]) / \
             sum([w * (x - _x) ** 2 for w, x in zip(weights, x_obs)])

    s = _y - B * _x

    self._kb = s, B

    return s, B

  def hand_pairs(self):

    # FIXME this should just use the saved indices

    unique_indices = set(self._raw_indices)
    unique_other = set(self._raw_other)

    return len(unique_indices.intersection(unique_other))

  def scale_to_kb(self, k, B):
    '''Scale this set to match input ln(k), B.'''

    dk = k - self._kb[0]
    dB = B - self._kb[1]

    import math

    for j, hkl in enumerate(self._raw_indices):
      S = math.exp(dk + dB * self._unit_cell.d_star_sq(hkl))
      self._raw_intensities[j] *= S
      self._raw_sigmas[j] *= S
      
    return

  def output_as_scalepack(self, sg, scalepack_fn):
    '''Output the *raw data* as an ersatz unmerged scalepack file.'''

    # FIXME this needs to be fixed to output the correct original indices

    # first write header bumpf
        
    symm = [op.r() for op in sg.smx()]
    
    fout = open(scalepack_fn, 'w')

    symbol = sg.type().lookup_symbol().replace(' ', '')
    fout.write('%5d %s\n' % (len(symm), symbol))

    for s in symm:
      fout.write('%3d%3d%3d%3d%3d%3d%3d%3d%3d\n%3d%3d%3d\n' % tuple(
        map(int, s.as_double()) + [0, 0, 0]))

    # then write out the measurements
    
    j = 0
        
    for b, fs in enumerate(self._frame_sizes):
      for k in range(fs):
        hkl = self._raw_indices[j]
        ohkl = self._raw_other[j]
        m = 1
        i = self._raw_intensities[j]
        s = self._raw_sigmas[j]
        fout.write('%4d%4d%4d%4d%4d%4d%6d 0 0%3d%8.1f%8.1f\n' %
                   (hkl + ohkl + (b + 1, m, i, s)))
        j += 1

    fout.close()

def frame_numbers(frames):
    result = { }

    for f in frames:
        if not f.get_frames() in result:
            result[f.get_frames()] = 0
        result[f.get_frames()] += 1

    return result


# main application...

def run(args):
  phil = iotbx.phil.process_command_line(
    args = args, master_string = master_phil)
  work_params = phil.work.extract()
  if ("--help" in args) :
    libtbx.phil.parse(master_phil.show())
    return

  if ((work_params.d_min is None) or
      (work_params.data is None) or
      ((work_params.model is None) and
       work_params.scaling.algorithm != "mark1")):
    raise Usage("cxi.merge "
                "d_min=4.0 "
                "data=~/scratch/r0220/006/strong/ "
                "model=3bz1_3bz2_core.pdb")
  
  if ((work_params.rescale_with_average_cell) and
      (not work_params.set_average_unit_cell)) :
    raise Usage("If rescale_with_average_cell=True, you must also specify "+
      "set_average_unit_cell=True.")
  
  miller_set = symmetry(
      unit_cell = work_params.target_unit_cell,
      space_group_info = work_params.target_space_group
    ).build_miller_set(
      anomalous_flag = not work_params.merge_anomalous,
      d_min = work_params.d_min)
  from xfel.cxi.merging.general_fcalc import random_structure
  i_model = random_structure(work_params)

# ---- Augment this code with any special procedures for x scaling
  scaler = xscaling_manager(
    miller_set = miller_set,
    i_model = i_model,
    params = work_params)
  
  scaler.read_all()
  sg = miller_set.space_group()
  pg = sg.build_derived_laue_group()
  rational_ops = []
  for symop in pg:
    rational_ops.append((matrix.sqr(symop.r().transpose().as_rational()),
                         symop.r().as_hkl()))

  # miller_set.show_summary()
    
  uc = work_params.target_unit_cell
    
  hkl_asu = scaler.observations["hkl_id"]
  imageno = scaler.observations["frame_id"]
  intensi = scaler.observations["i"]
  sigma_i = scaler.observations["sigi"]
  lookup = scaler.millers["merged_asu_hkl"]
  origH = scaler.observations["H"]
  origK = scaler.observations["K"]
  origL = scaler.observations["L"]

  from cctbx.miller import map_to_asu
  sgtype = miller_set.space_group_info().type()
  aflag = miller_set.anomalous_flag()
  from cctbx.array_family import flex

  # FIXME in here perform the mapping to ASU for both the original and other
  # index as an array-wise manipulation to make things a bunch faster...
  # however this also uses a big chunk of RAM... FIXME also in here use
  # cb_op.apply(indices) to get the indices reindexed...

  original_indices = flex.miller_index()
  for x in xrange(len(scaler.observations["hkl_id"])):
    original_indices.append(lookup[hkl_asu[x]])

  from cctbx.sgtbx import change_of_basis_op

  I23 = change_of_basis_op('k, -h, l')

  other_indices = I23.apply(original_indices)

  map_to_asu(sgtype, aflag, original_indices)
  map_to_asu(sgtype, aflag, other_indices)

  # FIXME would be useful in here to have a less expensive way of finding the
  # symmetry operation which gave the map to the ASU - perhaps best way is to
  # make a new C++ map_to_asu which records this.
  
  # FIXME in here recover the original frame structure of the data to
  # logical frame objetcs - N.B. the frame will need to be augmented to test
  # alternative indexings

  # construct table of start / end indices for frames: now using Python
  # range indexing

  starts = [0]
  ends = []
    
  for x in xrange(1, len(scaler.observations["hkl_id"])):
    if imageno[x] != imageno[x - 1]:
      ends.append(x)
      starts.append(x)
            
  ends.append(len(scaler.observations["hkl_id"]))
  
  keep_start = []
  keep_end = []
  
  for j, se in enumerate(zip(starts, ends)):
    print 'processing frame %d: %d to %d' % (j, se[0], se[1])
    s, e = se
    isig = sum(i / s for i, s in zip(intensi[s:e], sigma_i[s:e])) / (e - s)
    dmin = 100.0
    for x in xrange(s, e):
      d = uc.d(lookup[hkl_asu[x]])
      if d < dmin:
        dmin = d
    if isig > 6.0 and dmin < 3.2:
      keep_start.append(s)
      keep_end.append(e)

  starts = keep_start
  ends = keep_end

  print 'Keeping %d frames' % len(starts)

  # then start running the comparison code

  frames = []

  for s, e in zip(starts, ends):
    # FIXME need this from remap to ASU
    misym = [0 for x in range(s, e)]
    indices = [original_indices[x] for x in range(s, e)]
    other = [other_indices[x] for x in range(s, e)]
    intensities = intensi[s:e]
    sigmas = sigma_i[s:e]

    frames.append(Frame(uc, indices, other, intensities, sigmas))

  cycle = 0

  total_nref = sum([len(f.get_indices()) for f in frames])

  # pre-scale the data - first determine average ln(k), B; then apply

  kbs = [f.kb() for f in frames]

  mn_k = sum([kb[0] for kb in kbs]) / len(kbs)
  mn_B = sum([kb[1] for kb in kbs]) / len(kbs)

  for f in frames:
    f.scale_to_kb(mn_k, mn_B)
    
  while True:

    print 'Analysing %d frames' % len(frames)
    print 'Cycle %d' % cycle
    cycle += 1

    print 'Power spectrum'
    fn = frame_numbers(frames)
    for j in sorted(fn):
      print '%4d %4d' % (j, fn[j])
            
    nref_cycle = sum([len(f.get_indices()) for f in frames])
    assert(nref_cycle == total_nref)

    # first work on the original indices

    import numpy

    common_reflections = numpy.zeros((len(frames), len(frames)),
                                     dtype = numpy.short)
    
    obs = { } 

    # for other hand add -j

    for j, f in enumerate(frames):
      indices = set(f.get_indices())
      for i in indices:
        _i = tuple(i)
        if not _i in obs:
          obs[_i] = []
        obs[_i].append(j)

    for hkl in obs:
      obs[hkl].sort()
      for j, f1 in enumerate(obs[hkl][:-1]):
        for f2 in obs[hkl][j + 1:]:
          if f1 * f2 > 0:
            common_reflections[(abs(f1), abs(f2))] += 1

    cmn_rfl_list = []

    for f1 in range(len(frames)):
      for f2 in range(f1 + 1, len(frames)):
        if common_reflections[(f1, f2)] > 10:
          cmn_rfl_list.append((common_reflections[(f1, f2)], f1, f2))

    cmn_rfl_list.sort()
    cmn_rfl_list.reverse()
    
    joins = []
    used = []
    
    for n, f1, f2 in cmn_rfl_list:
      
      if f1 in used or f2 in used:
        continue
            
      _cc = frames[f1].cc(frames[f2])

      # really only need to worry about f2 which will get merged...
      # merging multiple files together should be OK provided they are
      # correctly sorted (though the order should not matter anyhow?)
      # anyhow they are sorted anyway... ah as f2 > f1 then just sorting
      # the list by f2 will make sure the data cascase correctly.

      # p-value small (3% ish) for cc > 0.6 for > 10 observations -
      # necessary as will be correlated due to Wilson curves though
      # with B factor < 10 this is less of an issue

      if _cc[0] > 10 and _cc[1] > 0.6:
        print '%4d %.3f' % _cc, f1, f2
        joins.append((f2, f1))
        used.append(f2)

    if not joins:
      print 'No pairs found'
      break

    joins.sort()
    joins.reverse()
        
    for j2, j1 in joins:
      rmerge = frames[j1].merge(frames[j2])
      if rmerge:
        print 'R: %4d %4d %6.3f' % (j1, j2, rmerge)
      else:
        print 'R: %4d %4d ------' % (j1, j2)

    all_joins = [j for j in joins]

    # then do the same for the alternative indices

    other_reflections = numpy.zeros((len(frames), len(frames)),
                                    dtype = numpy.short)

    obs = { } 

    # for other hand add -j

    for j, f in enumerate(frames):
      indices = set(f.get_indices())
      for i in indices:
        _i = tuple(i)
        if not _i in obs:
          obs[_i] = []
        obs[_i].append(j)

      indices = set(f.get_other())
      for i in indices:
        _i = tuple(i)
        if not _i in obs:
          obs[_i] = []
        obs[_i].append(-j)

    for hkl in obs:
      obs[hkl].sort()
      for j, f1 in enumerate(obs[hkl][:-1]):
        for f2 in obs[hkl][j + 1:]:
          if f1 * f2 < 0:
            other_reflections[(abs(f1), abs(f2))] += 1

    oth_rfl_list = []

    for f1 in range(len(frames)):
      for f2 in range(f1 + 1, len(frames)):
        if other_reflections[(f1, f2)] > 10:
          oth_rfl_list.append((other_reflections[(f1, f2)], f1, f2))
    
    joins = []

    oth_rfl_list.sort()
    oth_rfl_list.reverse()
        
    for n, f1, f2 in oth_rfl_list:
      
      if f1 in used or f2 in used:
        continue
            
      _cc = frames[f1].cc_other(frames[f2])

      # really only need to worry about f2 which will get merged...
      # merging multiple files together should be OK provided they are
      # correctly sorted (though the order should not matter anyhow?)
      # anyhow they are sorted anyway... ah as f2 > f1 then just sorting
      # the list by f2 will make sure the data cascase correctly.

      # p-value small (3% ish) for cc > 0.6 for > 10 observations -
      # necessary as will be correlated due to Wilson curves though
      # with B factor < 10 this is less of an issue

      if _cc[0] > 10 and _cc[1] > 0.6:
        print '%4d %.3f' % _cc, f1, f2
        joins.append((f2, f1))
        used.append(f2)

    all_joins += joins

    if not all_joins:
      break
      
    joins.sort()
    joins.reverse()
        
    for j2, j1 in joins:
      frames[j2].reindex()
      rmerge = frames[j1].merge(frames[j2])
      if rmerge:
        print 'R: %4d %4d %6.3f' % (j1, j2, rmerge)
      else:
        print 'R: %4d %4d ------' % (j1, j2)
        
    continue

  frames.sort()

  print 'Biggest few: #frames; #unique refl'
  j = -1
  while frames[j].get_frames() > 1:
    print frames[j].get_frames(), frames[j].get_unique_indices()
    frames[j].output_as_scalepack(sg, 'scalepack-%d.sca' % j)
    j -= 1

  return

if (__name__ == "__main__"):
  sargs = ["d_min=3.0",
           "output.n_bins=25",
           "target_unit_cell=106.18,106.18,106.18,90,90,90",
           "target_space_group=I23",
           "nproc=1",
           "merge_anomalous=True",
           "plot_single_index_histograms=False",
           "scaling.algorithm=mark1",
           "raw_data.sdfac_auto=True",
           "scaling.mtz_file=fake_filename.mtz",
           "scaling.show_plots=True",
           "scaling.log_cutoff=-3.",
           "set_average_unit_cell=True",
           "rescale_with_average_cell=False",
           "significance_filter.sigma=0.5",
           "output.prefix=poly_124_unpolarized_control"
           ]
  result = run(args=sargs)
