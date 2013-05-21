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
                                         tolerance = 1.e-3)

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

        _indices = []
        _intensities = []
        _sigmas = []

        # limit only to relections with 500 counts or more

        for j, i in enumerate(intensities):
            if i < 500:
                continue
            _indices.append(indices[j])
            _intensities.append(intensities[j])
            _sigmas.append(sigmas[j])

        self._raw_indices = _indices
        self._raw_intensities = _intensities
        self._raw_sigmas = _sigmas

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

        _x = sum([w * x for w, x in zip(weights, x_obs)]) / \
            sum(weights)
        _y = sum([w * y for w, y in zip(weights, y_obs)]) / \
            sum(weights)

        B = sum([w * (x - _x) * (y - _y) for w, x, y in \
                 zip(weights, x_obs, y_obs)]) / \
            sum([w * (x - _x) ** 2 for w, x in zip(weights, x_obs)])

        s = _y - B * _x

        self._kb = s, B

        return s, B

    def scale_to_kb(self, k, B):
        '''Scale this set to match input ln(k), B.'''

        dk = k - self._kb[0]
        dB = B - self._kb[1]

        import math

        results = []

        for j, hkl in enumerate(self._raw_indices):
            ds_sq = self._unit_cell.d_star_sq(hkl)
            S = math.exp(dk + dB * ds_sq)
            self._raw_intensities[j] *= S
            self._raw_sigmas[j] *= S
            results.append((ds_sq, self._raw_intensities[j], self._raw_sigmas[j]))

        return results

def frame_numbers(frames):
    result = { }

    for f in frames:
        if not f.get_frames() in result:
            result[f.get_frames()] = 0
        result[f.get_frames()] += 1

    return result

def find_merge_common_images(args):
    phil = iotbx.phil.process_command_line(args = args,
                                           master_string = master_phil).show()
    work_params = phil.work.extract()
    if ("--help" in args) :
        libtbx.phil.parse(master_phil.show())
        return

    if ((work_params.d_min is None) or
        (work_params.data is None) or
        ((work_params.model is None) and
         work_params.scaling.algorithm != "mark1")) :
        raise Usage("cxi.merge "
                    "d_min=4.0 "
                    "data=~/scratch/r0220/006/strong/ "
                    "model=3bz1_3bz2_core.pdb")
    if ((work_params.rescale_with_average_cell) and
        (not work_params.set_average_unit_cell)) :
        raise Usage(
            "If rescale_with_average_cell=True, you must also specify "+
            "set_average_unit_cell=True.")

    # Read Nat's reference model from an MTZ file.  XXX The observation
    # type is given as F, not I--should they be squared?  Check with Nat!
    log = open("%s_%s_scale.log" % (work_params.output.prefix,
                                    work_params.scaling.algorithm), "w")
    out = multi_out()
    out.register("log", log, atexit_send_to=None)
    out.register("stdout", sys.stdout)

    print >> out, "Target unit cell and space group:"
    print >> out, "  ", work_params.target_unit_cell
    print >> out, "  ", work_params.target_space_group

    uc = work_params.target_unit_cell

    miller_set = symmetry(
        unit_cell=work_params.target_unit_cell,
        space_group_info=work_params.target_space_group
        ).build_miller_set(
        anomalous_flag=not work_params.merge_anomalous,
        d_min=work_params.d_min)
    print 'Miller set size: %d' % len(miller_set.indices())
    from xfel.cxi.merging.general_fcalc import random_structure
    i_model = random_structure(work_params)

    # ---- Augment this code with any special procedures for x scaling
    scaler = xscaling_manager(
        miller_set=miller_set,
        i_model=i_model,
        params=work_params,
        log=out)
    scaler.read_all()
    print "finished reading"
    sg = miller_set.space_group()
    pg = sg.build_derived_laue_group()
    miller_set.show_summary()

    hkl_asu = scaler.observations["hkl_id"]
    imageno = scaler.observations["frame_id"]
    intensi = scaler.observations["i"]
    sigma_i = scaler.observations["sigi"]
    
    lookup = scaler.millers["merged_asu_hkl"]    

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

    def nint(a):
        return int(round(a))

    from collections import defaultdict
    i_scale = 0.1
    i_hist = defaultdict(int)

    for j, se in enumerate(zip(starts, ends)):
        s, e = se

        for i in intensi[s:e]:
            i_hist[nint(i_scale * i)] += 1
        
        isig = sum(i / s for i, s in zip(intensi[s:e], sigma_i[s:e])) / (e - s)
        dmin = 100.0
        for x in xrange(s, e):
            d = uc.d(lookup[hkl_asu[x]])
            if d < dmin:
                dmin = d
        if isig > 6.0 and dmin < 3.2:
            keep_start.append(s)
            keep_end.append(e)

    fout = open('i_hist.dat', 'w')
    for i in i_hist:
        fout.write('%.2f %d\n' % (i / i_scale, i_hist[i]))
    fout.close()

    starts = keep_start
    ends = keep_end

    print 'Keeping %d frames' % len(starts)

    frames = []

    odd = 0
    even = 0

    for s, e in zip(starts, ends):

        for x in range(s, e):
            hkl = lookup[hkl_asu[x]]
            
            if (hkl[0] + hkl[1] + hkl[2]) % 2 == 1:
                odd += 1
            else:
                even += 1
        
        indices = [tuple(lookup[hkl_asu[x]]) for x in range(s, e)]
        intensities = intensi[s:e]
        sigmas = sigma_i[s:e]

        frames.append(Frame(uc, indices, intensities, sigmas))

    # pre-scale the data - first determine average ln(k), B; then apply

    kbs = [f.kb() for f in frames]

    mn_k = sum([kb[0] for kb in kbs]) / len(kbs)
    mn_B = sum([kb[1] for kb in kbs]) / len(kbs)

    n_lt_500 = 0
    n_gt_500 = 0

    for j, f in enumerate(frames):
        s_i = f.scale_to_kb(mn_k, mn_B)
        fout = open('frame-s-i-%05d.dat' % j, 'w')
        for s, i, si in s_i:
            fout.write('%f %f %f\n' % (s, i, si))
            if i < 500:
                n_lt_500 += 1
            else:
                n_gt_500 += 1
        fout.close()

    from collections import defaultdict

    hist = defaultdict(int)

    fout = open('kb.dat', 'w')

    for j, f in enumerate(frames):
        kb = f.kb()
        fout.write('%4d %6.3f %6.3f\n' % (j, kb[0], kb[1]))
        hist[int(round(kb[1]))] += 1

    fout.close()

    for b in sorted(hist):
        print b, hist[b]


    print odd, even
    print n_lt_500, n_gt_500
    

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
             "output.prefix=poly_122_unpolarized_control"
             ]
    result = find_merge_common_images(args=sargs)
      
