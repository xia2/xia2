import json
import os
import sys
from cctbx import sgtbx


def table1_tex(crystal_params, merging_stats):
    # based on table1 from
    #
    # http://journals.iucr.org/d/issues/2018/02/00/di5011/index.html

    assert len(crystal_params) == len(merging_stats)

    # first iterate through and work out how many columns we will be needing
    columns = [len(ms) for ms in merging_stats]

    if max(columns) > 1:
        raise RuntimeError(":TODO: make this work for multiwavelength data sets")

    ncols = sum(columns)

    print("\\begin{tabular}{%s}" % ("l" * (ncols + 1)))

    name_str = [""]
    for cp in crystal_params:
        name_str.append(cp["name"].replace("_", r"\_"))

    print(" & ".join(name_str) + " \\\\")
    print("Crystal parameters" + " & " * ncols + "\\\\")
    print(
        "Space group & "
        + " & ".join(cp["space_group"] for cp in crystal_params)
        + " \\\\"
    )

    # witchcraft to work out how to write out the unit cell
    cell_str = ["Unit-cell parameters (\\AA)"]
    for cp in crystal_params:
        sgi = sgtbx.space_group_info(str(cp["space_group"]))
        sg = sgi.group()
        constraints = sgtbx.tensor_rank_2_constraints(
            space_group=sg, reciprocal_space=False
        )
        cell_tmp = "$"
        cell = cp["cell"]
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
        for name in ms:
            low = ms[name]["Low resolution limit"]
            high = ms[name]["High resolution limit"]
            resolution_str.append(
                "%.2f-%.2f (%.2f-%.2f)" % (low[0], high[0], low[2], high[2])
            )

    print(" & ".join(resolution_str) + " \\\\")

    # loopy boiler plate stuff - https://xkcd.com/1421/ - sorry - and why do
    # grown ups sometimes need things in %ages? x_x

    magic_words_and_places_and_multipliers = [
        ("No. of unique reflections", "Total unique", 1, "%d"),
        ("Multiplicity", "Multiplicity", 1, "%.1f"),
        ("$R_{\\rm{merge}}$", "Rmerge(I)", 1, "%.3f"),
        ("$R_{\\rm{meas}}$", "Rmeas(I)", 1, "%.3f"),
        ("$R_{\\rm{pim}}$", "Rpim(I)", 1, "%.3f"),
        ("Completeness (\\%)", "Completeness", 1, "%.1f"),
        ("$<I/\\sigma(I)>$", "I/sigma", 1, "%.1f"),
        ("$CC_{\\frac{1}{2}}$", "CC half", 1, "%.3f"),
    ]

    for mw, p, m, fmt in magic_words_and_places_and_multipliers:

        magic_str = [mw]

        for ms in merging_stats:
            for name in ms:
                data = ms[name][p]
                magic_str.append(("%s (%s)" % (fmt, fmt)) % (data[0] * m, data[2] * m))

        print(" & ".join(magic_str) + " \\\\")

    print("\\end{tabular}")


def table1():
    jsons = []
    for xia2 in sys.argv[1:]:
        assert os.path.exists(os.path.join(xia2, "xia2.json")), xia2
        with open(os.path.join(xia2, "xia2.json")) as fh:
            jsons.append(json.load(fh))

    # extract out the information needed - for the moment just the merging
    # statistics though could later extract data collection statistics from
    # the image headers :TODO:

    merging_stats = []
    crystal_params = []

    for _j, j in enumerate(jsons):
        for x in j["_crystals"]:
            s = j["_crystals"][x]["_scaler"]
            crystal_param = {
                "space_group": s["_scalr_likely_spacegroups"][0],
                "cell": s["_scalr_cell"],
                "cell_esd": s["_scalr_cell_esd"],
                "name": sys.argv[_j + 1],
            }

            merging_stats.append(s["_scalr_statistics"])
            crystal_params.append(crystal_param)

    table1_tex(crystal_params, merging_stats)


if __name__ == "__main__":
    table1()
