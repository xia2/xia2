# Interactive indexing with XDS: at the moment this means just selecting which
# images you want to use for indexing though FIXME it should be possible to
# have the indexing fully interactive i.e. user can run index, select solution,
# change images to use etc. so it becomes fully interactive.


from xia2.Modules.Indexer.IndexerSelectImages import index_select_image_wedges_user
from xia2.Modules.Indexer.XDSIndexer import XDSIndexer


class XDSIndexerInteractive(XDSIndexer):
    """An extension of XDSIndexer using all available images."""

    def __init__(self):
        super().__init__()
        self._index_select_images = "interactive"

    # helper functions

    def _index_select_images_interactive(self):

        phi_width = self.get_phi_width()

        # use five degrees for the background calculation

        five_deg = int(round(5.0 / phi_width)) - 1

        if five_deg < 5:
            five_deg = 5

        images = self.get_matching_images()

        wedges = index_select_image_wedges_user(self.get_template(), phi_width, images)

        if min(images) + five_deg in images:
            self._background_images = (min(images), min(images) + five_deg)
        else:
            self._background_images = (min(images), max(images))

        return wedges
