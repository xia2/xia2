from __future__ import annotations

from xia2.Schema.Interfaces.Indexer import (
    Indexer,
    beam_centre,
    beam_centre_raw_image,
)

X_MM, Y_MM = 10.0, 20.0


class FakePanel:
    def get_bidirectional_ray_intersection(self, s0):
        return (X_MM, Y_MM)

    def is_coord_valid_mm(self, xy):
        return True

    def get_raw_image_offset(self):
        return (0.0, 0.0)

    def millimeter_to_pixel(self, xy):
        return (xy[0] * 10.0, xy[1] * 10.0)

    def pixel_to_millimeter(self, xy):
        return (xy[0] / 10.0, xy[1] / 10.0)


class FakeDetector(list):
    def __init__(self):
        super().__init__([FakePanel()])


class FakeBeam:
    def get_s0(self):
        return (0.0, 0.0, 1.0)


class FakeExperiment:
    detector = FakeDetector()
    beam = FakeBeam()


def test_beam_centre_returns_x_then_y():
    panel_id, (x, y) = beam_centre(FakeDetector(), FakeBeam())
    assert panel_id == 0
    assert x == X_MM
    assert y == Y_MM


def test_beam_centre_raw_image_returns_x_then_y():
    assert beam_centre_raw_image(FakeDetector(), FakeBeam()) == (X_MM, Y_MM)


def test_get_indexer_beam_centre_raw_image_is_x_then_y():
    # The ISPyB output reports beam[0] as refined_xbeam and beam[1] as
    # refined_ybeam, so the raw-image beam centre must be (x, y).
    indexer = object.__new__(Indexer)
    indexer.index = lambda: None
    indexer.get_indexer_experiment_list = lambda: [FakeExperiment()]

    assert indexer.get_indexer_beam_centre_raw_image() == (X_MM, Y_MM)
