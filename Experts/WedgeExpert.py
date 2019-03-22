#!/usr/bin/env python
# WedgeExpert.py
#
#   Copyright (C) 2009 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Some code to help figure out how the experiment was performed and tell
# Chef where we could consider cutting the data at... N.B. this will now
# take the digested wedges from the Chef wrapper.

from __future__ import absolute_import, division, print_function


def digest_wedges(wedges):
    """Digest the wedges defined as a list of

  FIRST_DOSE FIRST_BATCH SIZE EXPOSURE DATASET

  to a set of potential "stop" points, in terms of the doses. This will
  return a list of DOSE values which should be treated as LIMITS (i.e.
  d:d < DOSE ok)."""

    # first digest to logical sweeps, keyed by the last image in the set
    # and the wavelength name, and containing the start and end dose.

    if False:
        return

    doses = {}

    belonging_wedges = {}

    for w in wedges:
        dose, batch, size, exposure, dataset = w
        if (dataset, batch) in doses:
            k_old = (dataset, batch)
            k_new = (dataset, batch + size)

            sweep = doses[k_old]
            doses[k_new] = (sweep[0], sweep[1] + exposure * size)

            belonging_wedges[k_new] = belonging_wedges[k_old]
            belonging_wedges[k_new].append(w)

            del doses[k_old]
            del belonging_wedges[k_old]

        else:
            end_dose = dose + exposure * (size - 1)

            doses[(dataset, batch + size)] = (dose, end_dose)
            belonging_wedges[(dataset, batch + size)] = [w]

    # now invert

    sweeps = {}

    for k in doses:
        sweeps[doses[k]] = k

    # now try to figure the sweeps which are overlapping - these will be
    # added to a list named "groups"

    groups = []

    last_time = sorted(sweeps)[0][0] - 1.0

    for s in sorted(sweeps):
        if s[0] > last_time:
            last_time = s[1]
            groups.append([s])
        else:
            last_time = s[1]
            groups[-1].append(s)

    dmaxes = []

    group_report = []

    for j, g in enumerate(groups):

        # check that the group structure is correct, i.e. all have the
        # uniform number of wedges...

        group_wedges = {}

        for s in g:
            all_wedges = belonging_wedges[sweeps[s]]
            dataset = all_wedges[0][-1]
            last_image = int(s[1])

            # Boom! this is wrong for inverse beam data sets

            group_wedges[(dataset, last_image)] = all_wedges

        size = 0

        datasets = list({k[0] for k in group_wedges})

        if len(g) == 1:
            assert len(belonging_wedges[sweeps[g[0]]]) == 1
            group_report.append("Single wedge")
        elif len(datasets) == 1:
            assert len(group_wedges) == 2
            group_report.append("Inverse beam")
        else:
            group_report.append("%d-wedge data collection" % len(group_wedges))

        for dataset, last_image in group_wedges:
            if not size:
                size = len(group_wedges[(dataset, last_image)])

            assert size == len(group_wedges[(dataset, last_image)])

        for j in range(size):

            d_local = []

            for s in g:
                bw = belonging_wedges[sweeps[s]][j]
                d_local.append(bw[0] + bw[2] * bw[3])

            dmaxes.append(max(d_local))

    return dmaxes, group_report


if __name__ == "__main__":

    import six.moves.cPickle as pickle

    with open("test.pkl", "rb") as fh:
        wedges = pickle.loads(fh.read())

    dmaxes, group_report = digest_wedges(wedges)

    for gr in group_report:
        print(gr)
