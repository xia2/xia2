from __future__ import absolute_import, division, print_function

import math

from scitbx import matrix


def set_distance(detector, distance):
    panel = detector[0]
    d_normal = matrix.col(panel.get_normal())
    d_origin = matrix.col(panel.get_origin())
    d_distance = math.fabs(d_origin.dot(d_normal) - panel.get_directed_distance())
    assert d_distance < 0.001, d_distance
    translation = d_normal * (distance - panel.get_directed_distance())
    new_origin = d_origin + translation
    d_distance = math.fabs(new_origin.dot(d_normal) - distance)
    assert d_distance < 0.001, d_distance
    fast = panel.get_fast_axis()
    slow = panel.get_slow_axis()
    panel.set_frame(panel.get_fast_axis(), panel.get_slow_axis(), new_origin.elems)
    d_fast = matrix.col(panel.get_fast_axis()).angle(matrix.col(fast), deg=True)
    assert d_fast < 1e-4, d_fast
    d_slow = matrix.col(panel.get_slow_axis()).angle(matrix.col(slow), deg=True)
    assert d_slow < 1e-4, d_slow
    d_distance = math.fabs(panel.get_directed_distance() - distance)
    assert d_distance < 0.001, d_distance
