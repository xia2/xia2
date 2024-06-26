from __future__ import annotations

import pickle
import sys

from dials.array_family import flex  # noqa: F401


def main(filename):
    """Show a mask from create_mask."""

    from matplotlib import pylab

    with open(filename, "rb") as fh:
        m = pickle.load(fh)

    pylab.imshow(m[0].as_numpy_array())
    pylab.show()


def run(args=sys.argv):
    main(args[1])
