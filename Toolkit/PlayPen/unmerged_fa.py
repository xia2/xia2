import sys
import math
from iotbx import mtz
from cctbx.miller import build_set
from cctbx.crystal import symmetry as crystal_symmetry
from cctbx.xray import array_f_sq_as_f_xtal_3_7 as f_sq_as_f

def weight(t, s):
    return math.exp(- t * t * 0.5 / s)

def estimate(values, t, s):
    # FIXME need to include error estimates

    weights = [weight(v[0] - t, s) for v in values]
    w0 = sum(weights)
    if w0 < 1.0e-6:
        weights = [1 for v in values]
        w0 = sum(weights)
    weights = [w / w0 for w in weights]

    return sum(v[1] * weights[j] for j, v in enumerate(values))

def compute_fa(plus, minus, s):
    # FIXME need to include error estimates
    
    diff_p = [(p[0], p[1] - estimate(minus, p[0], s)) for p in plus]
    diff_m = [(m[0], estimate(plus, m[0], s) - m[1]) for m in minus]    

    return sorted(diff_p + diff_m)

def nint(a):
    return int(round(a))

def unmerged_fa(_mtz_file):
    mtz_obj = mtz.object(_mtz_file)
    
    mi = mtz_obj.extract_miller_indices()
    dmax, dmin = mtz_obj.max_min_resolution()

    crystal_name = None
    dataset_name = None
    nref = 0
    uc = None

    symmetry = mtz_obj.space_group()

    # now have a rummage through to get the columns out that I want

    base_column = None
    misym_column = None
    i_column = None
    sigi_column = None

    batch_column = None

    for crystal in mtz_obj.crystals():

        for dataset in crystal.datasets():
            if dataset.name() != 'HKL_base':
                dataset_name = dataset.name()

        if crystal.name() != 'HKL_base':
            crystal_name = crystal.name()

        uc = crystal.unit_cell()

        for dataset in crystal.datasets():
            for column in dataset.columns():
                if column.label() == 'BATCH':
                    batch_column = column
                if column.label() == 'M_ISYM':
                    misym_column = column
                if column.label() == 'I':
                    i_column = column
                if column.label() == 'SIGI':
                    sigi_column = column

    assert(batch_column != None)
    assert(misym_column != None)
    assert(i_column != None)
    assert(sigi_column != None)

    r = f_sq_as_f(i_column.extract_valid_values().as_double(),
                  sigi_column.extract_valid_values().as_double(),
                  1.0e-6)

    f, sigf = r.f, r.sigma_f
    misym = misym_column.extract_valid_values()
    batch = batch_column.extract_valid_values()

    reflections = { }

    for j in range(mi.size()):
        hkl = mi[j]
        pm = int(round(misym[j])) % 2
        if not hkl in reflections:
            reflections[(hkl)] = []
        reflections[(hkl)].append((pm, batch[j], f[j], sigf[j]))

    # now compute unmerged FA values

    unmerged_fa = { }

    for hkl in reflections:
        plus = []
        minus = []

        for pm, b, f, sigf in reflections[hkl]:
            if pm:
                plus.append((b, f, sigf))
            else:
                minus.append((b, f, sigf))

        # FIXME include errors (sigf values) however in meantime don't worry
        # as Chef calculation does not need this.
 
        unmerged_fa[hkl] = compute_fa(plus, minus, 60.0)

    rcp_top = { }
    rcp_bottom = { }

    batch = map(nint, batch)

    for b in range(min(batch), max(batch) + 1):
        rcp_top[b] = 0.0
        rcp_bottom[b] = 0.0

    for hkl in unmerged_fa:
        fas = unmerged_fa[hkl]
        for n, (b, fa) in enumerate(fas):
            for _b, _fa in fas[n + 1:]:
                ra = math.fabs(fa - _fa)
                rb = 0.5 * math.fabs(fa + _fa)
                mb = nint(max(b, _b))
                rcp_top[mb] += ra
                rcp_bottom[mb] += rb

    for b in range(min(batch) + 1, max(batch) + 1):
        rcp_top[b] += rcp_top[b - 1]
        rcp_bottom[b] += rcp_bottom[b - 1]

    for b in range(min(batch), max(batch) + 1):
        print '%5d %6.3f' % (b, rcp_top[b] / rcp_bottom[b])

if __name__ == '__main__':
    unmerged_fa(sys.argv[1])

    
