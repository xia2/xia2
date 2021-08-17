# The kernel of code to start to calculate backstop masks for Mosflm and
# XDS from a list of coordinates read off from ADXV of the corners of the
# backstop. Initially this will be coded for the backstop on Diamond Light
# Source beamline I03

"""Code for backstop masking. In the first instance this will just be for a
single quadrilateral mask as per Diamond phase I MX beamlines. The input is a
table which contains the following:

  distance x1 y1 x2 y2 x3 y3 x4 y4

from which a backstop mask for the input images is calculated. N.B. positions
1, 4 are assumed to be on the edge of the image, 2, 3 close to the direct beam
position. The positions may be read from ADXV and will be applied to both XDS
and Mosflm."""


import binascii
import logging
import math

from xia2.Modules.UnpackByteOffset import pack_values, unpack_values

logger = logging.getLogger("xia2.Toolkit.BackstopMask")


def mmcc(ds, xs, ys):
    """Fit a straight line

    (x, y) = (mx, my) *  d + (cx, cy)

    to ordinates x, y in xs, ys as a function of d in ds."""

    assert len(ds) == len(xs)
    assert len(ds) == len(ys)

    ds = [float(i) for i in ds]
    xs = [float(i) for i in xs]
    ys = [float(i) for i in ys]

    _d = sum(ds) / len(ds)
    _x = sum(xs) / len(xs)
    _y = sum(ys) / len(ys)

    mx = sum((d - _d) * (x - _x) for d, x in zip(ds, xs)) / sum(
        (d - _d) * (d - _d) for d in ds
    )

    my = sum((d - _d) * (y - _y) for d, y in zip(ds, ys)) / sum(
        (d - _d) * (d - _d) for d in ds
    )

    cx = _x - mx * _d
    cy = _y - my * _d

    return mx, my, cx, cy


def compute_fit(distances, coordinates):

    xs = [c[0] for c in coordinates]
    ys = [c[1] for c in coordinates]

    return mmcc(distances, xs, ys)


def directions(o, t):
    """Compute a list of directions o -> t unit length."""

    assert len(o) == len(t)

    result = []

    for j in range(len(o)):
        dx = t[j][0] - o[j][0]
        dy = t[j][1] - o[j][1]
        l = math.sqrt(dx * dx + dy * dy)
        result.append((dx / l, dy / l))

    return result


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def line_intersect_rectangle(o, d, nx, ny):
    """Calculate where a line starting at origin o and heading in direction d
    intersects rectangle bounded by (0,0), (nx, 0), (nx, ny), (0, ny)."""

    # requirements are:
    #
    # direction not perpendicular to axis:
    #  intersection is within range:
    #    direction to intersection point is positive:
    #      return this

    assert math.fabs(dot(d, d) - 1) < 0.001

    if d[0] != 0.0:
        intersection = o[1] - (o[0] / d[0]) * d[1]
        if 0 <= intersection <= ny:
            if dot((0.0 - o[0], intersection - o[1]), d) > 0.0:
                return (0.0, intersection)

        intersection = o[1] - ((o[0] - nx) / d[0]) * d[1]
        if 0 <= intersection <= ny:
            if dot((nx - o[0], intersection - o[1]), d) > 0.0:
                return (nx, intersection)

    if d[1] != 0.0:
        intersection = o[0] - (o[1] / d[1]) * d[0]
        if 0 <= intersection <= nx:
            if dot((intersection - o[0], 0.0 - o[1]), d) > 0.0:
                return (intersection, 0.0)

        intersection = o[0] - ((o[1] - ny) / d[1]) * d[0]
        if 0 <= intersection <= nx:
            if dot((intersection - o[0], ny - o[1]), d) > 0.0:
                return (intersection, ny)

    raise RuntimeError("intersection not found")


def invert_2x2(a, b, c, d):

    e = a * d - b * c

    return d / e, -b / e, -c / e, a / e


def equation_of_line(p1, p2):
    """Determine a, b, c: ax + by + c = 0 passes through the two points
    given."""

    # first check that the points are different
    if (p1[0] == p2[0]) and (p1[1] == p2[1]):
        raise RuntimeError("points are identical")

    # then check for the special case: vertical line
    if p1[0] == p2[0]:
        if p1[1] > p2[1]:
            return -1.0, 0.0, -1.0 * p1[0]
        else:
            return 1.0, 0.0, -1.0 * p1[0]

    # then the special case of the horizontal line
    if p1[1] == p2[1]:
        if p1[0] > p2[0]:
            return 0.0, -1.0, -1.0 * p1[1]
        else:
            return 0.0, 1.0, -1.0 * p1[1]

    # then for the special case k: p2 = k p1

    if p1[0] != 0.0 and p1[1] != 0.0:
        if (p2[1] / p1[1]) == (p2[0] / p1[0]):
            return 1.0, p1[1] / p1[0], 0.0

    # and then finally the general case
    a, b, c, d = invert_2x2(p1[0], p1[1], p2[0], p2[1])

    return -(a + b), -(c + d), 1


class BackstopMask:
    """A class to handle the calculation of back stop masks, from a
    set of masks as a function of distance derived from inspection
    of images in ADXV."""

    def __init__(self, site_file):
        """Parse a site file containing records which begin:

        distance x1 y1 x2 y2 x3 y3 x4 y4 (nonsense)

        where distance is in mm, coordinates are in pixels. Will return
        origins and directions for positions 2 and 3, and directions for
        the vectors 2 -> 1 and 3 -> 4."""

        # first read out the file

        distances = []
        coordinates = {}

        for record in open(site_file):
            values = list(map(float, record.split()[:9]))
            if not values:
                continue
            distances.append(values[0])
            for j in range(4):
                coordinates.setdefault(j, []).append(
                    (values[2 * j + 1], values[2 * j + 2])
                )

        # now compute directions and so on for 2, 3 first
        # then directions for 2 -> 1, 3 -> 4, then fit and store

        self._p2 = compute_fit(distances, coordinates[1])
        self._p3 = compute_fit(distances, coordinates[2])

        d21 = directions(coordinates[1], coordinates[0])
        d34 = directions(coordinates[2], coordinates[3])

        self._d21 = compute_fit(distances, d21)
        self._d34 = compute_fit(distances, d34)

    def calculate_mask(self, header):
        """Calculate the pixel positions for the mask, given the image
        header."""

        distance = header["distance"]
        nx, ny = header["size"]

        mx2, my2, cx2, cy2 = self._p2
        mx3, my3, cx3, cy3 = self._p3
        mx21, my21, cx21, cy21 = self._d21
        mx34, my34, cx34, cy34 = self._d34

        p2 = (mx2 * distance + cx2, my2 * distance + cy2)
        p3 = (mx3 * distance + cx3, my3 * distance + cy3)

        d21 = (mx21 * distance + cx21, my21 * distance + cy21)
        d34 = (mx34 * distance + cx34, my34 * distance + cy34)

        # now extrapolate the directions

        p1 = line_intersect_rectangle(p2, d21, nx, ny)
        p4 = line_intersect_rectangle(p3, d34, nx, ny)

        return p1, p2, p3, p4

    def apply_mask_xds(self, header, cbf_in, cbf_out):
        """Apply the calculated backstop mask to a BKGINIT.cbf - do this
        immediately after the INIT step."""

        r = self.rectangle(header)

        data = open(cbf_in, "rb").read()

        start_tag = binascii.unhexlify("0c1a04d5")

        data_offset = data.find(start_tag) + 4

        cbf_header = data[: data.find(start_tag)]

        fast = 0
        slow = 0
        length = 0

        for record in cbf_header.split("\n"):
            if "X-Binary-Size-Fastest-Dimension" in record:
                fast = int(record.split()[-1])
            elif "X-Binary-Size-Second-Dimension" in record:
                slow = int(record.split()[-1])
            elif "X-Binary-Number-of-Elements" in record:
                length = int(record.split()[-1])

        assert length == fast * slow
        assert fast == int(header["size"][0])
        assert slow == int(header["size"][1])

        values = unpack_values(data[data_offset:], length)

        # or perhaps mask it out a little more cleverly

        limits = r.limits()

        for x in range(int(limits[0]), int(limits[1]) + 1):
            for y in range(int(limits[2]), int(limits[3]) + 1):
                j = y * fast + x
                if r.is_inside((x + 0.5, y + 0.5)):
                    values[j] = -3

        # and write out the updated file

        result = cbf_header + start_tag + pack_values(values)

        with open(cbf_out, "w") as fh:
            fh.write(result)

    def rectangle(self, header):
        """Return a configured rectangle object to test whether pixels are
        within the backstop region."""

        p1, p2, p3, p4 = self.calculate_mask(header)

        logger.debug(
            "Vertices of mask: (%d, %d), (%d, %d), (%d, %d), (%d, %d)",
            int(p1[0]),
            int(p1[1]),
            int(p2[0]),
            int(p2[1]),
            int(p3[0]),
            int(p3[1]),
            int(p4[0]),
            int(p4[1]),
        )

        return rectangle(p1, p2, p3, p4)


class rectangle:
    """A class to represent a rectange."""

    def __init__(self, p1, p2, p3, p4):

        self._points = p1, p2, p3, p4

        self._l12 = equation_of_line(p1, p2)
        self._l23 = equation_of_line(p2, p3)
        self._l34 = equation_of_line(p3, p4)
        self._l41 = equation_of_line(p4, p1)

        centre = (
            0.25 * (p1[0] + p2[0] + p3[0] + p4[0]),
            0.25 * (p1[1] + p2[1] + p3[1] + p4[1]),
        )

        self._in12 = self._evaluate(self._l12, centre)
        self._in23 = self._evaluate(self._l23, centre)
        self._in34 = self._evaluate(self._l34, centre)
        self._in41 = self._evaluate(self._l41, centre)

    def _evaluate(self, abc, p):
        a, b, c = abc
        r = a * p[0] + b * p[1] + c
        return r

    def limits(self):
        xs = [p[0] for p in self._points]
        ys = [p[1] for p in self._points]

        return min(xs), max(xs), min(ys), max(ys)

    def is_inside(self, p):
        if self._in12 * self._evaluate(self._l12, p) < 0.0:
            return False
        if self._in23 * self._evaluate(self._l23, p) < 0.0:
            return False
        if self._in34 * self._evaluate(self._l34, p) < 0.0:
            return False
        if self._in41 * self._evaluate(self._l41, p) < 0.0:
            return False
        return True
