#!/usr/bin/env xia2.python

from collections import OrderedDict


def flex_double_as_string(flex_array, n_digits=None):
    if n_digits is not None:
        flex_array = flex_array.round(n_digits)
    return list(flex_array.as_string())


def plot_uc_histograms(uc_params):

    a, b, c = (flex_double_as_string(p, n_digits=4) for p in uc_params[:3])
    d = OrderedDict()

    d["uc_scatter"] = {
        "data": [
            {
                "x": a,
                "y": b,
                "type": "scatter",
                "mode": "markers",
                "name": "a vs. b",
                "xaxis": "x",
                "yaxis": "y",
            },
            {
                "x": b,
                "y": c,
                "type": "scatter",
                "mode": "markers",
                "name": "b vs. c",
                "xaxis": "x2",
                "yaxis": "y2",
            },
            {
                "x": c,
                "y": a,
                "type": "scatter",
                "mode": "markers",
                "name": "c vs. a",
                "xaxis": "x3",
                "yaxis": "y3",
            },
        ],
        "layout": {
            "grid": {"rows": 1, "columns": 3, "pattern": "independent"},
            "title": "Distribution of unit cell parameters",
            "showlegend": False,
            "xaxis": {"title": "a (Å)"},
            "yaxis": {"title": "b (Å)"},
            "xaxis2": {"title": "b (Å)"},
            "yaxis2": {"title": "c (Å)"},
            "xaxis3": {"title": "c (Å)"},
            "yaxis3": {"title": "a (Å)"},
        },
        "help": """\
The distribution of the unit cell parameters: a vs. b, b vs. c and c vs.a respectively.
""",
    }

    d["uc_hist"] = {
        "data": [
            {
                "x": a,
                "type": "histogram",
                "connectgaps": False,
                "name": "uc_hist_a",
                "nbins": "auto",
                "xaxis": "x",
                "yaxis": "y",
            },
            {
                "x": b,
                "type": "histogram",
                "connectgaps": False,
                "name": "uc_hist_b",
                "nbins": "auto",
                "xaxis": "x2",
                "yaxis": "y",
            },
            {
                "x": c,
                "type": "histogram",
                "connectgaps": False,
                "name": "uc_hist_c",
                "nbins": "auto",
                "xaxis": "x3",
                "yaxis": "y",
            },
        ],
        "layout": {
            "grid": {"rows": 1, "columns": 3, "subplots": [["xy", "x2y", "x3y"]]},
            "title": "Histogram of unit cell parameters",
            "showlegend": False,
            "xaxis": {"title": "a (Å)"},
            "yaxis": {"title": "Frequency"},
            "xaxis2": {"title": "b (Å)"},
            "xaxis3": {"title": "c (Å)"},
        },
        "help": """\
Histograms of unit cell parameters, a, b and c.
""",
    }

    return d
