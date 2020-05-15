import os
import sys

import iotbx.phil
from cctbx import sgtbx
from iotbx.command_line import merging_statistics


master_phil = """\
include scope iotbx.command_line.merging_statistics.master_phil

latex = False
  .type = bool
"""

master_params = iotbx.phil.parse(master_phil, process_includes=True)


# override default parameters
master_params = master_params.fetch(
    source=iotbx.phil.parse(
        """\
use_internal_variance = False
eliminate_sys_absent = False
"""
    )
)


def table1_tex(merging_stats):
    # based on table1 from
    #
    # http://journals.iucr.org/d/issues/2018/02/00/di5011/index.html

    ncols = len(merging_stats)

    print("\\begin{tabular}{%s}" % ("l" * (ncols + 1)))

    # name_str = ['']
    # for cp in crystal_params:
    # name_str.append(cp['name'].replace('_', '\_'))

    # print(' & '.join(name_str) + ' \\\\')
    print("Crystal parameters" + " & " * ncols + "\\\\")
    print(
        "Space group & "
        + " & ".join(
            ms.crystal_symmetry.space_group().type().lookup_symbol()
            for ms in merging_stats
        )
        + " \\\\"
    )

    # witchcraft to work out how to write out the unit cell
    cell_str = ["Unit-cell parameters (\\AA)"]
    for ms in merging_stats:
        sg = ms.crystal_symmetry.space_group()
        constraints = sgtbx.tensor_rank_2_constraints(
            space_group=sg, reciprocal_space=False
        )
        cell_tmp = "$"
        cell = ms.crystal_symmetry.unit_cell().parameters()
        independent = constraints.independent_indices

        # weird case spotted with P3 - this set is impossible
        if independent == (2, 3):
            independent = (1, 2)

        if 0 in independent:
            cell_tmp += "a=%.5f, " % cell[0]
        else:
            cell_tmp += "a="
        if 1 in independent:
            cell_tmp += "b=%.5f, " % cell[1]
        else:
            cell_tmp += "b="
        cell_tmp += "c=%.5f" % cell[2]
        if 3 in independent:
            cell_tmp += ", \\alpha=%.5f" % cell[3]
        if 4 in independent:
            cell_tmp += ", \\beta=%.5f" % cell[4]
        if 5 in independent:
            cell_tmp += ", \\gamma=%.5f" % cell[5]
        cell_tmp += "$"
        cell_str.append(cell_tmp)
    print(" & ".join(cell_str) + " \\\\")
    print("Data statistics" + " & " * ncols + "\\\\")

    # resolution ranges, shells

    resolution_str = ["Resolution range (\\AA)"]

    for ms in merging_stats:
        low = (ms.bins[0].d_max, ms.bins[0].d_min)
        high = (ms.bins[-1].d_max, ms.bins[-1].d_min)
        resolution_str.append(
            "%.2f-%.2f (%.2f-%.2f)" % (low[0], high[1], high[0], high[1])
        )

    print(" & ".join(resolution_str) + " \\\\")

    # loopy boiler plate stuff - https://xkcd.com/1421/ - sorry - and why do
    # grown ups sometimes need things in %ages? x_x

    magic_words_and_places_and_multipliers = [
        ("No. of unique reflections", "n_uniq", 1, "%d"),
        ("Multiplicity", "multiplicity", 1, "%.1f"),
        ("$R_{\\rm{merge}}$", "r_merge", 1, "%.3f"),
        ("$R_{\\rm{meas}}$", "r_meas", 1, "%.3f"),
        ("$R_{\\rm{pim}}$", "r_pim", 1, "%.3f"),
        ("Completeness (\\%)", "completeness", 1, "%.1f"),
        ("$<I/\\sigma(I)>$", "i_over_sigma_mean", 1, "%.1f"),
        ("$CC_{\\frac{1}{2}}$", "cc_one_half", 1, "%.3f"),
    ]

    for mw, p, m, fmt in magic_words_and_places_and_multipliers:

        magic_str = [mw]

        for ms in merging_stats:
            ms_d = ms.as_dict()
            magic_str.append(
                ("%s (%s)" % (fmt, fmt)) % (ms_d["overall"][p] * m, ms_d[p][-1] * m)
            )

        print(" & ".join(magic_str) + " \\\\")

    print("\\end{tabular}")


def run(args):
    if len(args) == 0 or "-h" in args or "--help" in args:
        master_params.show()
    interp = master_params.command_line_argument_interpreter(args)
    phil_scope, unhandled = interp.process_and_fetch(
        args, custom_processor="collect_remaining"
    )
    params = phil_scope.extract()
    merging_stats = []

    for arg in unhandled:
        assert os.path.isfile(arg)
        merging_stats.append(merging_statistics.run([arg], master_params=phil_scope))
    if params.latex:
        table1_tex(merging_stats)


if __name__ == "__main__":
    run(sys.argv[1:])
