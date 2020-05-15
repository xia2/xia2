# Code for the selection of images for autoindexing - selecting lone images
# from a list or wedges from a list, for XDS.


import logging

logger = logging.getLogger("xia2.Modules.Indexer.IndexerSelectImages")


def index_select_images_lone(phi_width, images):
    """Select images close to 0, 45 and 90 degrees from the list of available
    frames. N.B. we assume all frames have the same oscillation width."""

    selected_images = [images[0]]

    offset = images[0] - 1

    if offset + int(90.0 / phi_width) in images:
        selected_images.append(offset + int(45.0 / phi_width))
        selected_images.append(offset + int(90.0 / phi_width))

    else:
        middle = len(images) // 2 - 1
        if len(images) >= 3:
            selected_images.append(images[middle])
        selected_images.append(images[-1])

    return selected_images


def index_select_image_wedges_user(sweep_id, phi_width, images):
    images = [(min(images), max(images))]
    images_list = ", ".join("%d-%d" % i for i in images)

    logger.info("Existing images for indexing %s: %s", sweep_id, images_list)

    while True:

        record = input(">")

        if not record.strip():
            return images

        try:
            images = [
                tuple(int(t.strip()) for t in r.split("-")) for r in record.split(",")
            ]
            images_list = ", ".join("%d-%d" % i for i in images)
            logger.info("New images for indexing: %s", images_list)

            return images

        except ValueError:
            pass


if __name__ == "__main__":

    images = list(range(1, 91))

    assert index_select_images_lone(0.5, images) == [1, 45, 90]
    assert index_select_images_lone(1.0, images) == [1, 45, 90]
    assert index_select_images_lone(2.0, images) == [1, 22, 45]

    images = list(range(1, 361))

    assert index_select_images_lone(0.5, images) == [1, 90, 180]
    assert index_select_images_lone(1.0, images) == [1, 45, 90]
