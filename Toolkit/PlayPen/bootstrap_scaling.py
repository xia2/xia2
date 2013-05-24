from __future__ import division
import iotbx.phil
from scitbx import matrix
from cctbx.crystal import symmetry
from libtbx.utils import Usage, multi_out
import sys
from xfel.cxi.util import is_odd_numbered # implicit import
from xfel.command_line.cxi_merge import master_phil
from xfel.command_line.cxi_xmerge import xscaling_manager
import numpy

def meansd(values):
    import math

    assert(len(values) > 1)
    
    mean = sum(values) / len(values)
    var = sum([(v - mean) ** 2 for v in values]) / len(values - 1)
    return mean, math.sqrt(var)

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

def loop_through_frames(starts, ends, joins = { }):
    for s, e in zip(starts, ends):
        for x in range(s, e):
            yield x
        for _s, _e in joins.get(s, []):
            for x in range(_s, _e):
                yield x

def frame_range_thing(starts, ends, j, joins):
    for x in range(starts[j], ends[j]):
        yield x
    for s, e in joins.get(starts[j], []):
        for x in range(s, e):
            yield x

def merge_frames(starts, ends, joins, i, j):
    '''merge frame j into frame i; update joins table; remove references to 
    frame j; works in place'''

    if not i in joins:
        joins[i] = [(starts[j], ends[j])]
    else:
        joins[i].append((starts[j], ends[j]))
        
    # now fix the starts, ends table

    starts.remove(starts[j])
    ends.remove(ends[j])

    return

def mean(values):
    return sum(values) / len(values)

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
                                         tolerance = 1.e-6)

        # save the best scale factors
             
        self.x = self.optimizer.get_solution()

        self._scales_s = flex.double(1, 0.0)
        self._scales_s.extend(self.x[:len(self._frame_sizes) - 1])
        self._scales_b = flex.double(1, 0.0)
        self._scales_b.extend(self.x[len(self._frame_sizes) - 1:])
        
        # scale the raw intensity data for later reference

        scaled_intensities = []
        j = 0

        for f, fs in enumerate(self._frame_sizes):
            for k in range(fs):
                hkl = self._indices[j]
                g_hl = self.scale_factor(f, hkl)
                scaled_intensities.append((self._intensities[j] / g_hl))

                j += 1

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

    def __init__(self, unit_cell, indices, intensities, sigmas):
        self._unit_cell = unit_cell
        self._raw_indices = list(indices)
        self._raw_intensities = list(intensities)
        self._raw_sigmas = list(sigmas)

        self._intensities = intensities
        self._sigmas = sigmas

        self._frames = 1
        self._frame_sizes = [len(indices)]

        self._kb = None
        
        return

    def empty(self):
        self._raw_indices = []
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

    def normalize(self):
        '''Set scale: <I> = 1'''

        scale = sum(self._raw_intensities) / len(self._raw_intensities)

        self._intensities = [i / scale for i in self._raw_intensities]
        self._sigmas = [s / scale for s in self._raw_sigmas]

        return

    def cc(self, other):
        
        return cc(self.get_intensity_dict(), other.get_intensity_dict())

    def reindex(self):
        raise RuntimeError, 'implement me'

    def merge(self, other):
        '''Scale and merge frame data from this frame and the other.'''

        raw_indices = self._raw_indices + other.get_indices()
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

            # apply arbitrary cut-off on scaling: R > 0 and R < 1
            if rmerge > 1:
                return None
            if rmerge < 0:
                return None
            
        except ZeroDivisionError, zde:
            return None

        # and then in here I should grab the refined scale factors and
        # save them

        self._raw_indices = raw_indices
        self._raw_intensities = raw_intensities
        self._raw_sigmas = raw_sigmas
        self._frame_sizes = frame_sizes

        self._intensities = scaler.get_scaled_intensities()

        self._frames += other.get_frames()
        
        # FIXME here empty other frame of reflections etc - do not need to worry
        # then about thrashing frame lists.

        other.empty()

        return rmerge

    def merge_old(self, other):

        indices = other.get_indices()
        intensities = other.get_raw_intensities()
        sigmas = other.get_raw_sigmas()

        # better scale factor: scale by common observations

        common_hkl = set(self._raw_indices).intersection(set(indices))

        other_common_intensity = []

        for j, hkl in enumerate(indices):
            if hkl in common_hkl:
                other_common_intensity.append(intensities[j])

        self_common_intensity = []

        for j, hkl in enumerate(self._raw_indices):
            if hkl in common_hkl:
                self_common_intensity.append(self._raw_intensities[j])

        scale_other = mean(other_common_intensity) / mean(self_common_intensity)

        scaled_intensities = [i / scale_other for i in intensities]
        scaled_sigmas = [s / scale_other for s in sigmas]

        self._raw_indices += indices
        self._raw_intensities += scaled_intensities
        self._raw_sigmas += scaled_sigmas
        self._frame_sizes += other.get_frame_sizes()

        self._frames += other.get_frames()
        
        # FIXME here empty other frame of reflections etc - do not need to worry
        # then about thrashing frame lists.

        other.empty()

        # end merge_old

        return

    def common(self, other):
        return len(set(self._raw_indices).intersection(
                set(other.get_indices())))

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
        '''Find # reflection pairs matched by hand inversion operation h, l, k.
        N.B. this does have determinant -1 but also maps reflections asu onto
        self.'''

        unique_indices = set(self._raw_indices)

        from cctbx.sgtbx import rt_mx, change_of_basis_op

        hp = 0

        oh = change_of_basis_op(rt_mx('h,l,k'))

        for ui in unique_indices:
            oh_ui = oh.apply(ui)
            if oh_ui == ui:
                continue
            if oh_ui in unique_indices:
                hp += 1

        return hp / 2

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

def get_stuff_from_hklin(hklin):
    from iotbx import mtz

    mtz_obj = mtz.object(hklin)

    dmax, dmin = mtz_obj.max_min_resolution()
    
    sg = mtz_obj.space_group()
    uc = None

    # now have a rummage through to get the columns out that I want

    i_column = None
    sigi_column = None

    for crystal in mtz_obj.crystals():
        uc = crystal.unit_cell()

    return uc, sg, (dmax, dmin)
    

def frame_factory(hklin):
    '''Create a Frame object from an MTZ file corresponding to one INTEGRATE
    run in XDS.'''

    from iotbx import mtz

    mtz_obj = mtz.object(hklin)

    mi = mtz_obj.extract_miller_indices()
    dmax, dmin = mtz_obj.max_min_resolution()
    
    sg = mtz_obj.space_group()
    uc = None

    # now have a rummage through to get the columns out that I want

    i_column = None
    sigi_column = None

    for crystal in mtz_obj.crystals():
        uc = crystal.unit_cell()

        for dataset in crystal.datasets():
            for column in dataset.columns():
                if column.label() == 'I':
                    i_column = column
                elif column.label() == 'SIGI':
                    sigi_column = column

    return Frame(uc, mi, i_column.extract_values(
        not_a_number_substitute = 0.0), sigi_column.extract_values(
        not_a_number_substitute = 0.0))

def frame_numbers(frames):
    result = { }

    for f in frames:
        if not f.get_frames() in result:
            result[f.get_frames()] = 0
        result[f.get_frames()] += 1

    return result

def find_merge_common_images(args):

    dmax = None
    dmin = None
    sg = None
    uc = None

    for arg in args:
        _uc, _sg, _d = get_stuff_from_hklin(arg)

        if uc is None:
            uc = _uc
        else:
            # FIXME should test these are similar
            pass

        if sg is None:
            sg = _sg
        else:
            # FIXME should test these are the same
            pass

        if dmax is None:
            dmax = _d[0]
        else:
            if _d[0] > dmax:
                dmax = _d[0]
                
        if dmin is None:
            dmin = _d[1]
        else:
            if _d[1] < dmin:
                dmin = _d[1]
        
    miller_set = symmetry(
        unit_cell = uc,
        space_group_info = sg.info()
        ).build_miller_set(
        anomalous_flag = False,
        d_min = dmin)

    frames = []

    for arg in args:
        frames.append(frame_factory(arg))

    cycle = 0

    total_nref = sum([len(f.get_indices()) for f in frames])

    # pre-scale the data - first determine average ln(k), B; then apply

    kbs = [f.kb() for f in frames]

    mn_k = sum([kb[0] for kb in kbs]) / len(kbs)
    mn_B = sum([kb[1] for kb in kbs]) / len(kbs)

    print 'K, B: %.2f %.2f' % (mn_k, mn_B)

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

        common_reflections = numpy.zeros((len(frames), len(frames)),
                                         dtype = numpy.short)

        obs = { } 

        from cctbx.sgtbx import rt_mx, change_of_basis_op
        oh = change_of_basis_op(rt_mx('h,l,k'))

        for j, f in enumerate(frames):
            indices = set(f.get_indices())
            for i in indices:
                _i = tuple(i)
                if not _i in obs:
                    obs[_i] = []
                obs[_i].append(j)

        # work through unique observations ignoring those which include no
        # hand information
 
        for hkl in obs:
            if hkl == oh.apply(hkl):
                continue
            obs[hkl].sort()
            for j, f1 in enumerate(obs[hkl][:-1]):
                for f2 in obs[hkl][j + 1:]:
                    common_reflections[(f1, f2)] += 1

        cmn_rfl_list = []

        for f1 in range(len(frames)):
            for f2 in range(f1 + 1, len(frames)):
                if common_reflections[(f1, f2)] > 20:
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

            # p-value very small for cc > 0.75 for > 20 observations - necessary
            # as will be correlated due to Wilson curves

            if _cc[0] > 20 and _cc[1] > 0.75:
                print '%4d %.3f' % _cc, f1, f2
                joins.append((f2, f1))
                # used.append(f1)
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
                
        continue

    frames.sort()

    print 'Biggest few: #frames; #unique refl'
    j = -1
    while frames[j].get_frames() > 1:
        print frames[j].get_frames(), frames[j].get_unique_indices()
        j -= 1

    return

    
if (__name__ == "__main__"):
    import sys
    result = find_merge_common_images(sys.argv[1:])
      
