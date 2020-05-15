import math
import sys

import xia2.Handlers.Streams
from iotbx.reflection_file_reader import any_reflection_file
from scitbx.array_family import flex
from xia2.Toolkit.NPP import npp_ify


def npp(hklin):
    reader = any_reflection_file(hklin)
    intensities = [
        ma
        for ma in reader.as_miller_arrays(merge_equivalents=False)
        if ma.info().labels == ["I", "SIGI"]
    ][0]
    indices = intensities.indices()

    # merging: use external variance i.e. variances derived from SIGI column
    merger = intensities.merge_equivalents(use_internal_variance=False)
    mult = merger.redundancies().data()
    imean = merger.array()
    unique = imean.indices()
    iobs = imean.data()
    # scale up variance to account for sqrt(multiplicity) effective scaling
    variobs = (imean.sigmas() ** 2) * mult.as_double()

    all = flex.double()
    cen = flex.double()

    for hkl, i, v, m in zip(unique, iobs, variobs, mult):

        # only consider if meaningful number of observations
        if m < 3:
            continue

        sel = indices == hkl
        data = intensities.select(sel).data()

        assert m == len(data)

        _x, _y = npp_ify(data, input_mean_variance=(i, v))

        # perform linreg on (i) all data and (ii) subset between +/- 2 sigma

        sel = flex.abs(_x) < 2
        _x_ = _x.select(sel)
        _y_ = _y.select(sel)

        fit_all = flex.linear_regression(_x, _y)
        fit_cen = flex.linear_regression(_x_, _y_)

        all.append(fit_all.slope())
        cen.append(fit_cen.slope())

        print(
            "%3d %3d %3d" % hkl,
            "%.2f %.2f %.2f" % (i, v, i / math.sqrt(v)),
            "%.2f %.2f" % (fit_all.slope(), fit_cen.slope()),
            "%d" % m,
        )

    sys.stderr.write(
        "Mean gradients: %.2f %.2f\n"
        % (flex.sum(all) / all.size(), flex.sum(cen) / cen.size())
    )


if __name__ == "__main__":
    xia2.Handlers.Streams.setup_logging(
        logfile="xia2.npp.txt", debugfile="xia2.npp-debug.txt"
    )
    npp(sys.argv[1])
