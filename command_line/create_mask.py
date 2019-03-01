# LIBTBX_SET_DISPATCHER_NAME dev.xia2.create_mask
from __future__ import absolute_import, division, print_function


def main(filename, threshold, images):
    """Read and sum all images, define those pixels which are POSITIVE but which
    come out below threshold as mask, write this mask in a format useful for
    DIALS."""

    from dxtbx import load
    from dials.array_family import flex
    import six.moves.cPickle as pickle

    image_data = None

    for image in images:
        i = load(image)
        d = i.get_raw_data()
        if image_data is None:
            image_data = i.get_raw_data()
        else:
            image_data += i.get_raw_data()

    mask_inverse = (image_data >= 0) & (image_data < threshold)
    mask = ~mask_inverse
    with open(filename, "wb") as fh:
        pickle.dump((mask,), fh, pickle.HIGHEST_PROTOCOL)

    print("Mask written to %s" % filename)


if __name__ == "__main__":
    import sys

    filename = sys.argv[1]
    threshold = int(sys.argv[2])
    images = sys.argv[3:]
    main(filename, threshold, images)
