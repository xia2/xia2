# LIBTBX_SET_DISPATCHER_NAME dev.xia2.show_mask
from __future__ import absolute_import, division, print_function

import sys
import six.moves.cPickle as pickle
from dials.array_family import flex  # lgtm # noqa # Required for pickle loading


def main(filename):
    """Show a mask from create_mask."""

    from matplotlib import pylab

    with open(filename, "rb") as fh:
        m = pickle.load(fh)

    pylab.imshow(m[0].as_numpy_array())
    pylab.show()


if __name__ == "__main__":
    main(sys.argv[1])
