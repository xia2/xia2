#!/usr/bin/env python

from __future__ import absolute_import, division, print_function

import copy
import datetime
import math
import os
import sys
import time
import traceback

import pycbf
from scitbx import matrix
from scitbx.math import r3_rotation_axis_and_angle_from_matrix
from xia2.Driver.DriverFactory import DriverFactory

if __name__ == "__main__":
    debug = False
else:
    debug = False


class _HeaderCache(object):
    """A cache for image headers."""

    def __init__(self):
        self._headers = {}

    def put(self, image, header):
        self._headers[image] = copy.deepcopy(header)

    def get(self, image):
        return self._headers[image]

    def check(self, image):
        return image in self._headers

    def write(self, filename):
        import json

        json.dump(self._headers, open(filename, "w"))
        return

    def read(self, filename):
        assert self._headers == {}
        import json

        self._headers = json.load(open(filename, "r"))
        return len(self._headers)


HeaderCache = _HeaderCache()

# FIXME this does not include all MAR, RAXIS detectors

detector_class = {
    ("adsc", 2304, 81): "adsc q4",
    ("adsc", 1152, 163): "adsc q4 2x2 binned",
    ("adsc", 1502, 163): "adsc q4 2x2 binned",
    ("adsc", 4096, 51): "adsc q210",
    ("adsc", 2048, 102): "adsc q210 2x2 binned",
    ("adsc", 6144, 51): "adsc q315",
    ("adsc", 3072, 102): "adsc q315 2x2 binned",
    ("adsc", 4168, 64): "adsc q270",
    ("adsc", 4168, 65): "adsc q270",
    ("adsc", 2084, 128): "adsc q270 2x2 binned",
    ("adsc", 2084, 129): "adsc q270 2x2 binned",
    ("adsc", 2084, 130): "adsc q270 2x2 binned",
    ("cbf", 2463, 172): "pilatus 6M",
    ("mini-cbf", 2463, 172): "pilatus 6M",
    ("dectris", 2527, 172): "pilatus 6M",
    ("dectris", 1679, 172): "pilatus 2M",
    ("marccd", 4096, 73): "mar 300 ccd",
    ("marccd", 4096, 79): "mar 325 ccd",
    ("marccd", 3072, 73): "mar 225 ccd",
    ("marccd", 2048, 78): "mar 165 ccd",
    ("marccd", 2048, 79): "mar 165 ccd",
    ("marccd", 2048, 64): "mar 135 ccd",
    ("mar", 4096, 73): "mar 300 ccd",
    ("mar", 4096, 79): "mar 325 ccd",
    ("mar", 3072, 73): "mar 225 ccd",
    ("mar", 2048, 78): "mar 165 ccd",
    ("mar", 2048, 79): "mar 165 ccd",
    ("mar", 2048, 64): "mar 135 ccd",
    ("mar", 1200, 150): "mar 180",
    ("mar", 1600, 150): "mar 240",
    ("mar", 2000, 150): "mar 300",
    ("mar", 2300, 150): "mar 345",
    ("mar", 3450, 100): "mar 345",
    ("raxis", 3000, 100): "raxis IV",
    ("rigaku", 3000, 100): "raxis IV",
    ("saturn", 2048, 45): "rigaku saturn 92",
    ("saturn", 1024, 90): "rigaku saturn 92 2x2 binned",
    ("saturn", 2084, 45): "rigaku saturn 944",
    ("saturn", 1042, 90): "rigaku saturn 944 2x2 binned",
    ("rigaku", 2048, 45): "rigaku saturn 92",
    ("rigaku", 1024, 90): "rigaku saturn 92 2x2 binned",
    ("rigaku", 1042, 35): "rigaku saturn 724",
    ("rigaku", 1042, 70): "rigaku saturn 724 2x2 binned",
    ("rigaku", 2084, 45): "rigaku saturn 944",
    ("rigaku", 1042, 90): "rigaku saturn 944 2x2 binned",
    ("rigaku", 1042, 89): "rigaku saturn 944 2x2 binned",
}


def read_A200(image):
    """Read the header from a Rigaku A200 image. This is to work around the
    diffdump program falling over with such images."""

    raise RuntimeError("this needs implementing!")


# FIXME get proper specifications for these detectors...


def find_detector_id(cbf_handle):

    detector_id = ""

    cbf_handle.rewind_datablock()
    nblocks = cbf_handle.count_datablocks()

    for j in range(nblocks):
        cbf_handle.select_datablock(0)

    ncat = cbf_handle.count_categories()

    for j in range(ncat):
        cbf_handle.select_category(j)

        if not cbf_handle.category_name() == "diffrn_detector":
            continue

        nrows = cbf_handle.count_rows()
        ncols = cbf_handle.count_columns()

        cbf_handle.rewind_column()

        while True:
            if cbf_handle.column_name() == "id":
                detector_id = cbf_handle.get_value()
                break
            try:
                cbf_handle.next_column()
            except Exception:
                break

    return detector_id


def cbf_gonio_to_effective_axis(cbf_gonio):
    """Given a cbf goniometer handle, determine the real rotation axis."""

    x = cbf_gonio.rotate_vector(0.0, 1, 0, 0)
    y = cbf_gonio.rotate_vector(0.0, 0, 1, 0)
    z = cbf_gonio.rotate_vector(0.0, 0, 0, 1)

    R = matrix.rec(x + y + z, (3, 3)).transpose()

    x1 = cbf_gonio.rotate_vector(1.0, 1, 0, 0)
    y1 = cbf_gonio.rotate_vector(1.0, 0, 1, 0)
    z1 = cbf_gonio.rotate_vector(1.0, 0, 0, 1)

    R1 = matrix.rec(x1 + y1 + z1, (3, 3)).transpose()

    RA = R1 * R.inverse()

    axis = r3_rotation_axis_and_angle_from_matrix(RA).axis

    return axis


def failover_full_cbf(cbf_file):
    """Use pycbf library to read full cbf file description."""

    header = {}

    cbf_handle = pycbf.cbf_handle_struct()
    cbf_handle.read_widefile(cbf_file, pycbf.MSG_DIGEST)

    detector_id_map = {
        "Pilatus2M": "pilatus 2M",
        "Pilatus6M": "pilatus 6M",
        "i19-p300k": "pilatus 300K",
        "ADSCQ315-SN920": "adsc q315 2x2 binned",
    }

    header["detector_class"] = detector_id_map[find_detector_id(cbf_handle)]

    if "pilatus" in header["detector_class"]:
        header["detector"] = "dectris"
    elif "adsc" in header["detector_class"]:
        header["detector"] = "adsc"
    else:
        raise RuntimeError("unknown detector %s" % header["detector_class"])

    cbf_handle.rewind_datablock()

    detector = cbf_handle.construct_detector(0)

    # FIXME need to check that this is doing something sensible...!

    header["beam"] = tuple(map(math.fabs, detector.get_beam_center()[2:]))
    detector_normal = tuple(detector.get_detector_normal())

    gonio = cbf_handle.construct_goniometer()

    axis = tuple(gonio.get_rotation_axis())
    angles = tuple(gonio.get_rotation_range())

    header["distance"] = detector.get_detector_distance()
    header["pixel"] = (
        detector.get_inferred_pixel_size(1),
        detector.get_inferred_pixel_size(2),
    )

    header["phi_start"], header["phi_width"] = angles
    header["phi_end"] = header["phi_start"] + header["phi_width"]

    year, month, day, hour, minute, second, x = cbf_handle.get_datestamp()
    struct_time = datetime.datetime(year, month, day, hour, minute, second).timetuple()

    header["date"] = time.asctime(struct_time)
    header["epoch"] = cbf_handle.get_timestamp()[0]
    header["size"] = tuple(cbf_handle.get_image_size(0))
    header["exposure_time"] = cbf_handle.get_integration_time()
    header["wavelength"] = cbf_handle.get_wavelength()

    # compute the true two-theta offset... which is kind-of going around
    # the houses. oh and the real rotation axis.

    origin = detector.get_pixel_coordinates(0, 0)
    fast = detector.get_pixel_coordinates(0, 1)
    slow = detector.get_pixel_coordinates(1, 0)

    dfast = matrix.col([fast[j] - origin[j] for j in range(3)]).normalize()
    dslow = matrix.col([slow[j] - origin[j] for j in range(3)]).normalize()

    dorigin = matrix.col(origin)
    dnormal = dfast.cross(dslow)

    centre = -(dorigin - dorigin.dot(dnormal) * dnormal)

    f = centre.dot(dfast)
    s = centre.dot(dslow)

    header["fast_direction"] = dfast.elems
    header["slow_direction"] = dslow.elems
    header["detector_origin_mm"] = f, s

    header["rotation_axis"] = cbf_gonio_to_effective_axis(gonio)
    two_theta = dfast.angle(matrix.col((0.0, 1.0, 0.0)), deg=True)
    if math.fabs(two_theta - 180.0) < 1.0:
        header["two_theta"] = 0
    else:
        header["two_theta"] = two_theta

    # find the direct beam vector - takes a few steps
    cbf_handle.find_category("axis")

    # find record with equipment = source
    cbf_handle.find_column("equipment")
    cbf_handle.find_row("source")

    # then get the vector and offset from this

    beam_direction = []

    for j in range(3):
        cbf_handle.find_column("vector[%d]" % (j + 1))
        beam_direction.append(cbf_handle.get_doublevalue())

    # FIXME in here add in code to compute from first principles the beam
    # centre etc.

    detector.__swig_destroy__(detector)
    del detector

    gonio.__swig_destroy__(gonio)
    del gonio

    return header


def failover_cbf(cbf_file):
    """CBF files from the latest update to the PILATUS detector cause a
    segmentation fault in diffdump. This is a workaround."""

    header = {}

    header["two_theta"] = 0.0

    for record in open(cbf_file):

        if "_array_data.data" in record:
            break

        if "PILATUS 2M" in record:
            header["detector_class"] = "pilatus 2M"
            header["detector"] = "dectris"
            header["size"] = (1679, 1475)
            continue

        if "PILATUS3 2M" in record:
            header["detector_class"] = "pilatus 2M"
            header["detector"] = "dectris"
            header["size"] = (1679, 1475)
            continue

        if "PILATUS 6M" in record:
            header["detector_class"] = "pilatus 6M"
            header["detector"] = "dectris"
            header["size"] = (2527, 2463)
            continue

        if "PILATUS3 6M" in record:
            header["detector_class"] = "pilatus 6M"
            header["detector"] = "dectris"
            header["size"] = (2527, 2463)
            continue

        if "Start_angle" in record:
            header["phi_start"] = float(record.split()[-2])
            continue

        if "Angle_increment" in record:
            header["phi_width"] = float(record.split()[-2])
            continue

        if "Exposure_period" in record:
            header["exposure_time"] = float(record.split()[-2])
            continue

        if "Silicon sensor" in record:
            header["sensor"] = 1000 * float(record.split()[4])
            continue

        if "Count_cutoff" in record:
            header["saturation"] = int(record.split()[2])
            continue

        if "Detector_distance" in record:
            header["distance"] = 1000 * float(record.split()[2])
            continue

        if "Wavelength" in record:
            header["wavelength"] = float(record.split()[-2])
            continue

        if "Pixel_size" in record:
            header["pixel"] = (
                1000 * float(record.split()[2]),
                1000 * float(record.split()[5]),
            )
            continue

        if "Beam_xy" in record:

            # N.B. this is swapped again for historical reasons

            beam_pixels = map(
                float,
                record.replace("(", "").replace(")", "").replace(",", "").split()[2:4],
            )
            header["beam"] = (
                beam_pixels[1] * header["pixel"][1],
                beam_pixels[0] * header["pixel"][0],
            )
            header["raw_beam"] = (
                beam_pixels[1] * header["pixel"][1],
                beam_pixels[0] * header["pixel"][0],
            )
            continue

        # try to get the date etc. literally.

        try:
            datestring = record.split()[-1].split(".")[0]
            format = "%Y-%b-%dT%H:%M:%S"
            struct_time = time.strptime(datestring, format)
            header["date"] = time.asctime(struct_time)
            header["epoch"] = time.mktime(struct_time)

        except Exception:
            pass

        try:

            if not "date" in header:
                datestring = record.split()[-1].split(".")[0]
                format = "%Y-%m-%dT%H:%M:%S"
                struct_time = time.strptime(datestring, format)
                header["date"] = time.asctime(struct_time)
                header["epoch"] = time.mktime(struct_time)

        except Exception:
            pass

        try:

            if not "date" in header:
                datestring = record.replace("#", "").strip().split(".")[0]
                format = "%Y/%b/%d %H:%M:%S"
                struct_time = time.strptime(datestring, format)
                header["date"] = time.asctime(struct_time)
                header["epoch"] = time.mktime(struct_time)

        except Exception:
            pass

    header["phi_end"] = header["phi_start"] + header["phi_width"]

    return header


last_format = None


def failover_dxtbx(image_file):
    """Failover to use the dxtbx to read the image headers..."""

    # replacement dxtbx for rigaku saturns sometimes
    from dxtbx.format.Registry import Registry
    from dxtbx.model.detector_helpers_types import detector_helpers_types

    global last_format

    if last_format:
        iformat = last_format
    else:
        iformat = Registry.find(image_file)
        from xia2.Handlers.Streams import Debug

        Debug.write("Using dxtbx format instance: %s" % iformat.__name__)

    if not iformat.understand(image_file):
        raise RuntimeError("image file %s not understood by dxtbx" % image_file)

    last_format = iformat

    i = iformat(image_file)

    b = i.get_beam()
    g = i.get_goniometer()
    d = i.get_detector()
    s = i.get_scan()

    header = {}

    if not hasattr(d, "get_image_size"):
        # cope with new detector as array of panels dxtbx api
        fast, slow = map(int, d[0].get_image_size())
        _f, _s = d[0].get_pixel_size()
        F = matrix.col(d[0].get_fast_axis())
        S = matrix.col(d[0].get_slow_axis())
        N = F.cross(S)
        origin = matrix.col(d[0].get_origin())
    else:
        fast, slow = map(int, d.get_image_size())
        _f, _s = d.get_pixel_size()
        F = matrix.col(d.get_fast_axis())
        S = matrix.col(d.get_slow_axis())
        N = F.cross(S)
        origin = matrix.col(d.get_origin())

    beam = matrix.col(b.get_direction())

    # FIXME detector has methods to compute the beam centre now...

    centre = -(origin - origin.dot(N) * N)

    x = centre.dot(F)
    y = centre.dot(S)

    header["fast_direction"] = F.elems
    header["slow_direction"] = S.elems
    header["rotation_axis"] = g.get_rotation_axis()
    if hasattr(s, "get_exposure_time"):
        header["exposure_time"] = s.get_exposure_time()
    else:
        header["exposure_time"] = s.get_exposure_times()[0]
    header["distance"] = math.fabs(origin.dot(N))
    if math.fabs(beam.angle(N, deg=True) - 180) < 0.1:
        header["two_theta"] = 180 - beam.angle(N, deg=True)
    else:
        header["two_theta"] = -beam.angle(N, deg=True)
    header["raw_beam"] = x, y
    header["phi_start"] = s.get_oscillation()[0]
    header["phi_width"] = s.get_oscillation()[1]
    header["phi_end"] = sum(s.get_oscillation())
    header["pixel"] = _f, _s

    # FIXME this is very bad as it relates to teh legacy backwards Mosflm
    # beam centre standard still... FIXME-SCI-948

    header["beam"] = y, x
    header["epoch"] = s.get_image_epoch(s.get_image_range()[0])
    header["date"] = time.ctime(header["epoch"])
    header["wavelength"] = b.get_wavelength()
    header["size"] = fast, slow
    if hasattr(i, "detector_class"):
        header["detector_class"] = i.detector_class
        header["detector"] = i.detector
    else:
        if hasattr(d, "get_type"):
            # cope with new detector as array of panels API
            dtype = d.get_type()
        else:
            dtype = d[0].get_type()

        detector_type = detector_helpers_types.get(
            dtype, fast, slow, int(1000 * _f), int(1000 * _s)
        )

        header["detector_class"] = detector_type.replace("-", " ")
        header["detector"] = detector_type.split("-")[0]

    return header


def Diffdump(DriverType=None):
    """A factory for wrappers for the diffdump."""

    DriverInstance = DriverFactory.Driver(DriverType)

    class DiffdumpWrapper(DriverInstance.__class__):
        """Provide access to the functionality in diffdump."""

        def __init__(self):
            DriverInstance.__class__.__init__(self)

            self.set_executable("diffdump")

            self._image = None
            self._header = {}

            self._previous_crashed = False

            return

        def set_image(self, image):
            """Set an image to read the header of."""
            self._image = image
            self._header = {}
            return

        def _get_time(self, datestring):
            """Unpack a date string to a structure."""

            if not datestring:
                raise RuntimeError("empty date")

            if datestring == "N/A":
                # we don't have the date!
                # set default to 0-epoch
                return datetime.datetime(1970, 0, 0, 0, 0, 0).timetuple(), 0.0

            # problem here is multiple formats for date strings!
            # so have to change the structure...

            # FIXME!
            # pilatus: 2007/Sep/22 21:15:03.229
            # format: %Y/%b/%d %H:%M:%S

            # allow for milliseconds
            ms = 0.0

            struct_time = None
            try:
                format = "%Y/%b/%d %H:%M:%S"
                ms = 0.001 * int(datestring.split(".")[1])
                _datestring = datestring.split(".")[0]
                struct_time = time.strptime(_datestring, format)
            except Exception:
                struct_time = None

            # ADSC CBF format

            if not struct_time:
                try:
                    format = "%d/%m/%Y %H:%M:%S"
                    ms = 0.001 * int(datestring.split(".")[1])
                    _datestring = datestring.split(".")[0]
                    struct_time = time.strptime(_datestring, format)
                except Exception:
                    struct_time = None

            if not struct_time:
                try:
                    struct_time = time.strptime(datestring)
                except Exception:
                    struct_time = None

            if not struct_time:
                # this may be a mar format date...
                # MMDDhhmmYYYY.ss - go figure
                # or it could also be the format from
                # saturn images like:
                # 23-Oct-2006 13:42:36
                if not "-" in datestring:
                    month = int(datestring[:2])
                    day = int(datestring[2:4])
                    hour = int(datestring[4:6])
                    minute = int(datestring[6:8])
                    year = int(datestring[8:12])
                    second = int(datestring[-2:])
                    d = datetime.datetime(year, month, day, hour, minute, second)
                    struct_time = d.timetuple()
                else:
                    struct_time = time.strptime(datestring, "%d-%b-%Y %H:%M:%S")

            return struct_time, ms

        def _epoch(self, datestring):
            """Compute an epoch from a date string."""

            t, ms = self._get_time(datestring)

            return time.mktime(t) + ms

        def _date(self, datestring):
            """Compute a human readable date from a date string."""

            return time.asctime(self._get_time(datestring)[0])

        def readheader(self):
            """Read the image header."""

            if self._header:
                return copy.deepcopy(self._header)

            if HeaderCache.check(self._image):
                self._header = HeaderCache.get(self._image)
                return copy.deepcopy(self._header)

            if os.path.getsize(self._image) == 0:
                raise RuntimeError("empty file: %s" % self._image)

            if not self._previous_crashed:
                try:
                    return self.readheader_diffdump()
                except Exception:
                    self._previous_crashed = True

            try:
                self._header = failover_dxtbx(self._image)
                HeaderCache.put(self._image, self._header)
                return copy.deepcopy(self._header)
            except Exception:
                traceback.print_exc(file=sys.stdout)

        def readheader_diffdump(self):
            """Read the image header."""

            global detector_class

            # check that the input file exists..

            if not os.path.exists(self._image):
                raise RuntimeError("image %s does not exist" % self._image)

            # consider using more recent code to read these images in
            # first instance, to replace diffdump

            try:
                if ".cbf" in self._image[-4:]:
                    header = failover_cbf(self._image)
                    assert header["detector_class"] in ["pilatus 2M", "pilatus 6M"]
                    self._header = header
                    HeaderCache.put(self._image, self._header)
                    return copy.deepcopy(self._header)
            except Exception:
                if ".cbf" in self._image[-4:]:
                    header = failover_full_cbf(self._image)
                    self._header = header
                    HeaderCache.put(self._image, self._header)
                    return copy.deepcopy(self._header)

            self.clear_command_line()
            self.add_command_line(self._image)
            self.start()

            self.close_wait()

            # why is this commented out?
            # self.check_for_errors()

            # results were ok, so get all of the output out
            output = self.get_all_output()

            if debug:
                print("! all diffdump output follows")
                for o in output:
                    print("! %s" % o[:-1])

            # note that some of the records in the image header
            # will depend on the detector class - this should
            # really be fixed in the program diffdump...

            detector = None

            fudge = {
                "adsc": {"wavelength": 1.0, "pixel": 1.0},
                "dectris": {"wavelength": 1.0, "pixel": 1.0},
                "rigaku": {"wavelength": 1.0, "pixel": 1.0},
                "raxis": {"wavelength": 1.0, "pixel": 1.0},
                "saturn": {"wavelength": 1.0, "pixel": 1.0},
                "marccd": {"wavelength": 1.0, "pixel": 0.001},
                "mini-cbf": {"wavelength": 1.0, "pixel": 1.0},
                "cbf": {"wavelength": 1.0, "pixel": 1.0},
                "mar": {"wavelength": 1.0, "pixel": 1.0},
            }

            cbf_format = False

            for o in output:
                l = o.split(":")

                if len(l) > 1:
                    l2 = l[1].split()
                else:
                    l2 = ""

                # latest version of diffdump prints out manufacturer in
                # place of image type...

                if ("Image type" in o) or ("Manufacturer" in o):
                    if debug:
                        print("! found image type: %s" % l[1].strip().lower())
                    self._header["detector"] = l[1].strip().lower()

                    # correct spelling, perhaps
                    if self._header["detector"] == "mar ccd":
                        self._header["detector"] = "marccd"
                    if self._header["detector"] == "mar 345":
                        self._header["detector"] = "mar"
                    if self._header["detector"] == "rigaku saturn":
                        self._header["detector"] = "saturn"
                    if self._header["detector"] == "rigaku raxis":
                        self._header["detector"] = "raxis"
                    if self._header["detector"] == "rigaku r-axis":
                        self._header["detector"] = "raxis"
                    detector = self._header["detector"]

                if "Format" in o:
                    if o.split()[-1] == "CBF":
                        cbf_format = True

                # FIXME in here need to check a trust file timestamp flag

                if "Exposure epoch" in o or "Collection date" in o:
                    try:
                        d = o[o.index(":") + 1 :]
                        if d.strip():
                            self._header["epoch"] = self._epoch(d.strip())
                            self._header["date"] = self._date(d.strip())
                            if debug:
                                print(
                                    "! exposure epoch: %d" % int(self._header["epoch"])
                                )
                        else:
                            self._header["epoch"] = 0.0
                            self._header["date"] = ""

                    except Exception as e:

                        if debug:
                            print("! error interpreting date: %s" % str(e))

                        # this is badly formed....
                        # so perhaps read the file creation date?
                        # time.ctime(os.stat(filename)[8]) -> date
                        # os.stat(filename)[8] -> epoch
                        self._header["epoch"] = float(os.stat(self._image)[8])
                        self._header["date"] = time.ctime(self._header["epoch"])
                        # self._header['epoch'] = 0.0
                        # self._header['date'] = ''

                if "Exposure time" in o:
                    self._header["exposure_time"] = float(l2[0])

                if "Wavelength" in o:
                    self._header["wavelength"] = (
                        float(l2[0]) * fudge[detector]["wavelength"]
                    )
                    if debug:
                        print("! found wavelength: %f" % self._header["wavelength"])

                if "Distance" in o:
                    self._header["distance"] = float(l[1].replace("mm", "").strip())

                if "Beam cent" in o:
                    beam = (
                        l[1]
                        .replace("(", "")
                        .replace(")", "")
                        .replace("mm", " ")
                        .split(",")
                    )
                    self._header["beam"] = map(float, beam)
                    self._header["raw_beam"] = map(float, beam)

                if "Image Size" in o:
                    image = l[1].replace("px", "")
                    image = image.replace("(", "").replace(")", "").split(",")
                    self._header["size"] = map(float, image)

                if "Pixel Size" in o:
                    image = l[1].replace("mm", "")
                    x, y = image.replace("(", "").replace(")", "").split(",")
                    if detector == "marccd" and math.fabs(float(x)) < 1.0:
                        self._header["pixel"] = (float(x), float(y))
                    else:
                        self._header["pixel"] = (
                            float(x) * fudge[detector]["pixel"],
                            float(y) * fudge[detector]["pixel"],
                        )

                if "Angle range" in o:
                    phi = map(float, l[1].split("->"))
                    self._header["phi_start"] = phi[0]
                    self._header["phi_end"] = phi[1]
                    self._header["phi_width"] = phi[1] - phi[0]

                if "Oscillation" in o:
                    phi = map(float, l[1].replace("deg", "").split("->"))
                    self._header["phi_start"] = phi[0]
                    self._header["phi_end"] = phi[1]
                    self._header["phi_width"] = phi[1] - phi[0]

                if "Oscillation range" in o:
                    phi = map(float, l[1].replace("deg", "").split("->"))
                    self._header["phi_start"] = phi[0]
                    self._header["phi_end"] = phi[1]
                    self._header["phi_width"] = phi[1] - phi[0]

                if "Two Theta value" in o:
                    try:
                        two_theta = float(o.split(":")[1].split()[0])
                        self._header["two_theta"] = two_theta * -1.0
                    except ValueError:
                        self._header["two_theta"] = 0.0

            # check to see if the beam centre needs to be converted
            # from pixels to mm - e.g. MAR 300 images from APS ID 23

            if (
                "beam" in self._header
                and "pixel" in self._header
                and "size" in self._header
            ):
                # look to see if the current beam is somewhere in the middle
                # pixel count wise...
                beam = self._header["beam"]
                size = self._header["size"]
                pixel = self._header["pixel"]
                if math.fabs((beam[0] - 0.5 * size[0]) / size[0]) < 0.25:
                    new_beam = (beam[0] * pixel[0], beam[1] * pixel[1])
                    self._header["beam"] = new_beam

            # check beam centre is sensible i.e. not NULL

            if (
                math.fabs(self._header["beam"][0]) < 0.01
                and math.fabs(self._header["beam"][1]) < 0.01
            ):
                size = self._header["size"]
                pixel = self._header["pixel"]
                self._header["beam"] = (
                    0.5 * size[0] * pixel[0],
                    0.5 * size[1] * pixel[1],
                )

            if (
                "detector" in self._header
                and "pixel" in self._header
                and "size" in self._header
            ):
                # compute the detector class
                detector = self._header["detector"]
                width = int(self._header["size"][0])
                pixel = int(1000 * self._header["pixel"][0])

                key = (detector, width, pixel)

                self._header["detector_class"] = detector_class[key]

                # check for mar ccd and perhaps reassign

                if detector == "mar" and "ccd" in self._header["detector_class"]:
                    self._header["detector"] = "marccd"

                # currently diffdump swaps x, y in beam centre output
                if self._header["detector_class"] == "pilatus 2M":
                    x, y = self._header["beam"]
                    self._header["beam"] = y, x
                    x, y = self._header["raw_beam"]
                    self._header["raw_beam"] = y, x

            else:
                self._header["detector_class"] = "unknown"

            # quickly check diffdump didn't do something stupid...

            if detector == "adsc" and not cbf_format:

                osc_start = 0.0
                osc_range = 0.0

                size = int(open(self._image, "r").read(20).split()[-1])
                hdr = open(self._image, "r").read(size)
                for record in hdr.split("\n"):
                    if "OSC_START" in record:
                        osc_start = float(record.replace(";", "").split("=")[-1])
                    if "OSC_RANGE" in record:
                        osc_range = float(record.replace(";", "").split("=")[-1])

                self._header["phi_start"] = osc_start
                self._header["phi_width"] = osc_range
                self._header["phi_end"] = osc_start + osc_range

            if detector == "adsc" and abs(header["two_theta"]) > 1.0:
                raise RuntimeError("adsc + two-theta not supported")

            HeaderCache.put(self._image, self._header)

            return copy.deepcopy(self._header)

        def gain(self):
            """Estimate gain for this image."""

            # check that the input file exists..

            if not os.path.exists(self._image):
                raise RuntimeError("image %s does not exist" % self._image)

            self.add_command_line("-gain")
            self.add_command_line(self._image)
            self.start()
            self.close_wait()

            self.check_for_errors()

            # results were ok, so get all of the output out
            output = self.get_all_output()

            gain = 0.0

            for o in output:
                l = o.split(":")

                if "Estimation of gain" in o:
                    # This often seems to be an underestimate...
                    gain = 1.333 * float(l[1])

            return gain

    return DiffdumpWrapper()
