# LIBTBX_SET_DISPATCHER_NAME dev.xia2.show_mask

import pickle
import sys

from dials.array_family import flex  # noqa; lgtm; required for pickle loading


def main(filename):
    """Show a mask from create_mask."""

    from matplotlib import pylab

    with open(filename, "rb") as fh:
        m = pickle.load(fh)

    pylab.imshow(m[0].as_numpy_array())
    pylab.show()


if __name__ == "__main__":
    main(sys.argv[1])
