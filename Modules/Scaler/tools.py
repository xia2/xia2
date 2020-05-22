#!/usr/bin/env python
#
#   Copyright (C) 2009 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.

#
# Patch .mtz file and overwrite stored unit cell parameters
#
from iotbx import mtz


def patch_mtz_unit_cell(mtzfile, unit_cell_parameters):
    """Overwrite unit cell stored in mtz file"""

    f = mtz.object(file_name=mtzfile)
    assert f.n_crystals() == 2, "Can only patch .mtz files with 2 crystals"

    f.crystals()[0].set_unit_cell_parameters(unit_cell_parameters)
    f.crystals()[1].set_unit_cell_parameters(unit_cell_parameters)

    f.write(file_name=mtzfile)


#
# Replacement function centralised to replace the use of cellparm.
#


def compute_average_unit_cell(unit_cell_list):
    """Compute the weighted average unit cell based on a list of

    ((unit cell), nref)

    tuples."""

    w_tot = 0.0

    a_tot = 0.0
    b_tot = 0.0
    c_tot = 0.0
    alpha_tot = 0.0
    beta_tot = 0.0
    gamma_tot = 0.0

    for cell, n_ref in unit_cell_list:
        w_tot += n_ref
        a_tot += cell[0] * n_ref
        b_tot += cell[1] * n_ref
        c_tot += cell[2] * n_ref
        alpha_tot += cell[3] * n_ref
        beta_tot += cell[4] * n_ref
        gamma_tot += cell[5] * n_ref

    return (
        a_tot / w_tot,
        b_tot / w_tot,
        c_tot / w_tot,
        alpha_tot / w_tot,
        beta_tot / w_tot,
        gamma_tot / w_tot,
    )
