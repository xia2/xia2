# LIBTBX_SET_DISPATCHER_NAME dev.xia2.show_mask
from __future__ import absolute_import, division, print_function

import sys


def main(filename):
    """Show a mask from create_mask."""

    from dials.array_family import flex  # noqa: F401; Required for pickle loading
    import six.moves.cPickle as pickle
    from matplotlib import pylab

    with open(filename, "rb") as fh:
        m = pickle.load(fh)

    pylab.imshow(m[0].as_numpy_array())
    pylab.show()


if __name__ == "__main__":
    main(sys.argv[1])
