import pickle
import sys

from dxtbx import load


def main(filename, threshold, images):
    """Read and sum all images, define those pixels which are POSITIVE but which
    come out below threshold as mask, write this mask in a format useful for
    DIALS."""

    image_data = None

    for image in images:
        i = load(image)
        if image_data is None:
            image_data = i.get_raw_data()
        else:
            image_data += i.get_raw_data()

    mask_inverse = (image_data >= 0) & (image_data < threshold)
    mask = ~mask_inverse
    with open(filename, "wb") as fh:
        pickle.dump((mask,), fh, pickle.HIGHEST_PROTOCOL)

    print(f"Mask written to {filename}")


def run(args=sys.argv):
    filename = args[1]
    threshold = int(args[2])
    images = args[3:]
    main(filename, threshold, images)
