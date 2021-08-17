# A singleton to handle flags, which can be imported more easily
# as it will not suffer the problems with circular references that
# the CommandLine singleton suffers from.
# xia2#42: this is due for retirement & working into the Phil structure


import os

from xia2.Wrappers.XDS.XDS import xds_read_xparm


class _Flags:
    """A singleton to manage boolean flags."""

    def __init__(self):
        # XDS specific things - to help with handling tricky data sets

        self._xparm = None
        self._xparm_beam_vector = None
        self._xparm_rotation_axis = None
        self._xparm_origin = None

        self._xparm_a = None
        self._xparm_b = None
        self._xparm_c = None

        # starting directory (to allow setting working directory && relative
        # paths on input)
        self._starting_directory = os.getcwd()

    def get_starting_directory(self):
        return self._starting_directory

    def set_xparm(self, xparm):
        self._xparm = xparm

        xparm_info = xds_read_xparm(xparm)

        self._xparm_origin = xparm_info["ox"], xparm_info["oy"]
        self._xparm_beam_vector = tuple(xparm_info["beam"])
        self._xparm_rotation_axis = tuple(xparm_info["axis"])
        self._xparm_distance = xparm_info["distance"]

    def get_xparm(self):
        return self._xparm

    def get_xparm_origin(self):
        return self._xparm_origin

    def get_xparm_rotation_axis(self):
        return self._xparm_rotation_axis

    def get_xparm_beam_vector(self):
        return self._xparm_beam_vector

    def get_xparm_distance(self):
        return self._xparm_distance

    def set_xparm_ub(self, xparm):
        self._xparm_ub = xparm

        with open(xparm) as fh:
            tokens = list(map(float, fh.read().split()))

        self._xparm_a = tokens[-9:-6]
        self._xparm_b = tokens[-6:-3]
        self._xparm_c = tokens[-3:]

    def get_xparm_a(self):
        return self._xparm_a

    def get_xparm_b(self):
        return self._xparm_b

    def get_xparm_c(self):
        return self._xparm_c


Flags = _Flags()
