# A module to determine the accumulated dose as a function of exposure epoch
# for a given set of images, assuming:
#
# (i)  the set is complete
# (ii) the set come from a single (logical) crystal
#
# This is to work with fortran program "doser"


import collections

from scitbx.array_family import flex


def accumulate_dose(imagesets):
    epochs = flex.double()
    exposure_times = flex.double()
    for imageset in imagesets:
        scan = imageset.get_scan()
        epochs.extend(scan.get_epochs())
        exposure_times.extend(scan.get_exposure_times())

    perm = flex.sort_permutation(epochs)
    epochs = epochs.select(perm)
    exposure_times = exposure_times.select(perm)

    integrated_dose = collections.OrderedDict()

    total = 0.0
    for e, t in zip(epochs, exposure_times):
        integrated_dose[e] = total + 0.5 * t
        total += t

    return integrated_dose
