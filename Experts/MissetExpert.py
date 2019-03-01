#!/usr/bin./env python
# MissetExpert.py
#   Copyright (C) 2009 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 11th August 2009
#
# A class to calculate the missetting angles for Mosflm as a function of
# oscillation angle, to enable more robust parallel integration when the
# rotation is off perpendicular to the beam by more than e.g. 1 degree.
#
# N.B. similar calculations could use the XDS refined XPARM to record the
# rotation axis then reuse it here.

from __future__ import absolute_import, division, print_function

from scitbx import matrix
from scitbx.math import r3_rotation_axis_and_angle_from_matrix
from scitbx.math.euler_angles import xyz_angles, xyz_matrix


class MosflmMissetExpert(object):
    """A class to calculate the missetting angles to use for integration
    given some values around the start and a good way in (ideally 90 degrees)
    to the data processing. The protocol to obtain these remains to be
    established."""

    def __init__(self, phi0, misset0, phi1, misset1):
        """Initialise the rotation axis and what have you from some
        experimental results. N.B. all input values in DEGREES."""

        # canonical: X = X-ray beam
        #            Z = rotation axis
        #            Y = Z ^ X

        z = matrix.col([0, 0, 1])

        # then calculate the rotation axis

        R = (
            (
                z.axis_and_angle_as_r3_rotation_matrix(phi1, deg=True)
                * matrix.sqr(xyz_matrix(misset1[0], misset1[1], misset1[2]))
            )
            * (
                z.axis_and_angle_as_r3_rotation_matrix(phi0, deg=True)
                * matrix.sqr(xyz_matrix(misset0[0], misset0[1], misset0[2]))
            ).inverse()
        )

        self._z = z
        self._r = matrix.col(r3_rotation_axis_and_angle_from_matrix(R).axis)
        self._M0 = matrix.sqr(xyz_matrix(misset0[0], misset0[1], misset0[2]))

        return

    def get_r(self):
        """Get the rotation axis."""

        return self._r.elems

    def missets(self, phi):
        """Calculate the missetting angles for the given rotation angle."""

        P = self._z.axis_and_angle_as_r3_rotation_matrix(phi, deg=True)
        R = self._r.axis_and_angle_as_r3_rotation_matrix(phi, deg=True)
        M = P.inverse() * R * self._M0

        return xyz_angles(M)


if __name__ == "__main__":

    # example taken from the problematic myoglobin data set

    mme = MosflmMissetExpert(0.25, (-0.33, -0.32, -0.01), 91.75, (0.56, -0.12, -0.03))

    for j in range(0, 320, 20):
        phi = 0.5 * j + 0.25
        x, y, z = mme.missets(phi)
        print("%8.2f %8.2f %8.2f %8.2f" % (j + 1, x, y, z))
