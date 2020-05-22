import datetime
import logging
import os
import subprocess
import time

from scitbx import matrix

logger = logging.getLogger("xia2.Wrappers.XDS.XDS")


class XDSException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)


_xds_version_cache = None


def get_xds_version():
    global _xds_version_cache
    if _xds_version_cache is None:
        xds_version_str = subprocess.check_output("xds")
        assert b"VERSION" in xds_version_str
        first_line = xds_version_str.split(b"\n")[1].strip().decode("latin-1")

        _xds_version_cache = str(first_line.split("(")[1].split(")")[0])
        assert "VERSION" in _xds_version_cache, _xds_version_cache

    return _xds_version_cache


_running_xds_version_stamp = None


def _running_xds_version():
    global _running_xds_version_stamp
    if _running_xds_version_stamp is None:
        xds_version_str = subprocess.check_output("xds")
        assert b"VERSION" in xds_version_str
        first_line = xds_version_str.split("\n")[1].strip().decode("latin-1")
        if b"BUILT=" not in xds_version_str:
            format_str = "***** XDS *****  (VERSION  %B %d, %Y)"
            date = datetime.datetime.strptime(first_line, format_str)
            _running_xds_version_stamp = date.year * 10000 + date.month * 100 + date.day
        else:
            s = first_line.index("BUILT=") + 6
            _running_xds_version_stamp = int(first_line[s : s + 8])

    return _running_xds_version_stamp


def add_xds_version_to_mtz_history(mtz_file):
    from iotbx.reflection_file_reader import any_reflection_file
    from xia2.Wrappers.XDS import XDS

    reader = any_reflection_file(mtz_file)
    assert reader.file_type() == "ccp4_mtz"
    mtz_object = reader.file_content()
    date_str = time.strftime("%d/%m/%Y at %H:%M:%S", time.gmtime())
    mtz_object.add_history(f"From XDS {XDS.get_xds_version()}, run on {date_str}")
    mtz_object.write(mtz_file)


def xds_check_version_supported(xds_output_list):
    """No longer check that the XDS version is supported."""

    for record in xds_output_list:
        if "Sorry, license expired" in record:
            raise RuntimeError("installed XDS expired on %s" % record.split()[-1])


xds_error_database = {
    "cannot open or read file lp_01.tmp": "Error running forkintegrate"
}


def xds_check_error(xds_output_list):
    """Check for errors in XDS output and raise an exception if one is
    found."""

    for line in xds_output_list:
        if "!!!" in line and "ERROR" in line:
            message = line.split("!!!")[2].strip().lower()
            if message in xds_error_database:
                message = xds_error_database[message]
            error = "[XDS] %s" % message
            raise XDSException(error)


def imageset_to_xds(
    imageset,
    synchrotron=None,
    refined_beam_vector=None,
    refined_rotation_axis=None,
    refined_distance=None,
):
    """A function to take an input header dictionary from Diffdump
    and generate a list of records to start XDS - see Doc/INP.txt."""

    # decide if we are at a synchrotron if we don't know already...
    # that is, the wavelength is around either the Copper or Chromium
    # K-alpha edge and this is an image plate.

    beam = imageset.get_beam()

    from dxtbx.serialize.xds import to_xds, xds_detector_name

    converter = to_xds(imageset)

    h5_names = ["h5", "nxs"]
    if imageset.get_template().split(".")[-1] in h5_names:
        if not check_xds_ok_with_h5():
            raise RuntimeError("HDF5 input with no converter for XDS")

    detector_class_is_square = {
        "adsc q4": True,
        "adsc q4 2x2 binned": True,
        "adsc q210": True,
        "adsc q210 2x2 binned": True,
        "adsc q270": True,
        "adsc q270 2x2 binned": True,
        "adsc q315": True,
        "adsc q315 2x2 binned": True,
        "adsc HF4M": True,
        "holton fake 01": True,
        "unknown electron 57": True,
        "mar 345": False,
        "mar 180": False,
        "mar 240": False,
        "mar 300 ccd": True,
        "mar 325 ccd": True,
        "mar 225 ccd": True,
        "mar ccd 225 hs": True,
        "rayonix ccd 165": False,
        "rayonix ccd 135": False,
        "rayonix ccd 300": True,
        "rayonix ccd 325": True,
        "rayonix ccd 225": True,
        "rayonix ccd 225 hs": True,
        "rayonix ccd 300 hs": True,
        "mar 165 ccd": False,
        "mar 135 ccd": False,
        "pilatus 12M": True,
        "pilatus 6M": True,
        "pilatus 2M": True,
        "pilatus 1M": True,
        "pilatus 200K": True,
        "pilatus 300K": True,
        "eiger 1M": True,
        "eiger 4M": True,
        "eiger 9M": True,
        "eiger 16M": True,
        "rigaku saturn 92 2x2 binned": True,
        "rigaku saturn 944 2x2 binned": True,
        "rigaku saturn 724 2x2 binned": True,
        "rigaku saturn 92": True,
        "rigaku saturn 944": True,
        "rigaku saturn 724": True,
        "rigaku saturn a200": True,
        "raxis IV": True,
        "NOIR1": True,
    }

    sensor = converter.get_detector()[0].get_type()
    fast, slow = converter.detector_size
    f, s = converter.pixel_size
    df = int(1000 * f)
    ds = int(1000 * s)

    # FIXME probably need to rotate by pi about the X axis

    result = []

    from dxtbx.model.detector_helpers_types import detector_helpers_types

    detector = xds_detector_name(detector_helpers_types.get(sensor, fast, slow, df, ds))
    trusted = converter.get_detector()[0].get_trusted_range()

    # if CCD; undo dxtbx pedestal offset, hard code minimum 1; else use trusted
    # range verbatim (i.e. for PAD) (later in pipeline sensor is SENSOR_UNKNOWN
    # so additional test)

    if sensor == "SENSOR_CCD" or detector == "CCDCHESS":
        trusted = 1, trusted[1] - trusted[0]

    # XDS upset if we trust < 0 see #193
    if trusted[0] < 0:
        trusted = 0, trusted[1]

    result.append(
        "DETECTOR=%s MINIMUM_VALID_PIXEL_VALUE=%d OVERLOAD=%d"
        % (detector, trusted[0], trusted[1])
    )

    result.append("DIRECTION_OF_DETECTOR_X-AXIS=%f %f %f" % converter.detector_x_axis)

    result.append("DIRECTION_OF_DETECTOR_Y-AXIS=%f %f %f" % converter.detector_y_axis)

    from xia2.Handlers.Phil import PhilIndex

    params = PhilIndex.get_python_object()
    if params.xds.trusted_region:
        result.append("TRUSTED_REGION= %.2f %.2f" % tuple(params.xds.trusted_region))
    elif detector_class_is_square[
        detector_helpers_types.get(sensor, fast, slow, df, ds).replace("-", " ")
    ]:
        result.append("TRUSTED_REGION=0.0 1.41")
    else:
        result.append("TRUSTED_REGION=0.0 0.99")

    result.append("NX=%d NY=%d QX=%.4f QY=%.4f" % (fast, slow, f, s))

    # RAXIS detectors have the distance written negative - why????
    # this is ONLY for XDS - SATURN are the same - probably left handed
    # goniometer rotation on rigaku X-ray sets.

    if refined_distance:
        result.append("DETECTOR_DISTANCE=%7.3f" % refined_distance)
    else:
        result.append("DETECTOR_DISTANCE=%7.3f" % converter.detector_distance)

    result.append("OSCILLATION_RANGE=%4.2f" % converter.oscillation_range)
    result.append("X-RAY_WAVELENGTH=%8.6f" % converter.wavelength)

    # if user specified reversephi and this was not picked up in the
    # format class reverse phi: n.b. double-negative warning!

    if refined_rotation_axis:
        result.append("ROTATION_AXIS= %f %f %f" % refined_rotation_axis)
    else:
        result.append("ROTATION_AXIS= %.3f %.3f %.3f" % converter.rotation_axis)

    if refined_beam_vector:
        result.append("INCIDENT_BEAM_DIRECTION=%f %f %f" % refined_beam_vector)
    else:
        result.append("INCIDENT_BEAM_DIRECTION= %.3f %.3f %.3f" % converter.beam_vector)

    if hasattr(beam, "get_polarization_fraction"):
        R = converter.imagecif_to_xds_transformation_matrix
        result.append(
            "FRACTION_OF_POLARIZATION= %.3f" % beam.get_polarization_fraction()
        )
        result.append(
            "POLARIZATION_PLANE_NORMAL= %.3f %.3f %.3f"
            % (R * matrix.col(beam.get_polarization_normal())).elems
        )

    # 24/NOV/14 XDS determines the air absorption automatically
    # based on wavelength. May be useful to override this for in vacuo exps
    # result.append('AIR=0.001')

    if detector == "PILATUS":
        try:
            thickness = converter.get_detector()[0].get_thickness()
            if not thickness:
                thickness = 0.32
                logger.debug(
                    "Could not determine sensor thickness. Assuming default PILATUS 0.32mm"
                )
        except Exception:
            thickness = 0.32
            logger.debug(
                "Error occured during sensor thickness determination. Assuming default PILATUS 0.32mm"
            )
        result.append("SENSOR_THICKNESS=%f" % thickness)

    #  FIXME: Sensor absorption coefficient calculation probably requires a more general solution
    #  if converter.get_detector()[0].get_material() == 'CdTe':
    #    print "CdTe detector detected. Beam wavelength is %8.6f Angstrom" % converter.wavelength

    if len(converter.panel_x_axis) > 1:
        for panel_id in range(len(converter.panel_x_axis)):

            result.append("")
            result.append("!")
            result.append("! SEGMENT %d" % (panel_id + 1))
            result.append("!")
            result.append("SEGMENT= %d %d %d %d" % converter.panel_limits[panel_id])
            result.append(
                "DIRECTION_OF_SEGMENT_X-AXIS= %.3f %.3f %.3f"
                % converter.panel_x_axis[panel_id]
            )
            result.append(
                "DIRECTION_OF_SEGMENT_Y-AXIS= %.3f %.3f %.3f"
                % converter.panel_y_axis[panel_id]
            )
            result.append("SEGMENT_DISTANCE= %.3f" % converter.panel_distance[panel_id])
            result.append(
                "SEGMENT_ORGX= %.1f SEGMENT_ORGY= %.1f"
                % converter.panel_origin[panel_id]
            )
            result.append("")

    for panel, (x0, _, y0, _) in zip(converter.get_detector(), converter.panel_limits):
        for f0, s0, f1, s1 in panel.get_mask():
            result.append(
                "UNTRUSTED_RECTANGLE= %d %d %d %d"
                % (f0 + x0 - 1, f1 + x0, s0 + y0 - 1, s1 + y0)
            )

    if params.xds.untrusted_ellipse:
        for untrusted_ellipse in params.xds.untrusted_ellipse:
            result.append("UNTRUSTED_ELLIPSE= %d %d %d %d" % tuple(untrusted_ellipse))
        logger.debug(result[-1])

    if params.xds.untrusted_rectangle:
        for untrusted_rectangle in params.xds.untrusted_rectangle:
            result.append(
                "UNTRUSTED_RECTANGLE= %d %d %d %d" % tuple(untrusted_rectangle)
            )
        logger.debug(result[-1])

    return result


def xds_read_xparm(xparm_file):
    """Parse the new-style or old-style XPARM file."""

    with open(xparm_file) as fh:
        line = fh.readline()
    if "XPARM" in line:
        return xds_read_xparm_new_style(xparm_file)
    else:
        return xds_read_xparm_old_style(xparm_file)


def xds_read_xparm_old_style(xparm_file):
    """Parse the XPARM file to a dictionary."""

    with open(xparm_file) as fh:
        data = [float(x) for x in fh.read().split()]

    assert len(data) == 42

    starting_frame = int(data[0])
    phi_start, phi_width = data[1:3]
    axis = data[3:6]

    wavelength = data[6]
    beam = data[7:10]

    nx, ny = list(map(int, data[10:12]))
    px, py = data[12:14]

    distance = data[14]
    ox, oy = data[15:17]

    x, y = data[17:20], data[20:23]
    normal = data[23:26]

    spacegroup = int(data[26])
    cell = data[27:33]

    a, b, c = data[33:36], data[36:39], data[39:42]

    results = {
        "starting_frame": starting_frame,
        "phi_start": phi_start,
        "phi_width": phi_width,
        "axis": axis,
        "wavelength": wavelength,
        "beam": beam,
        "nx": nx,
        "ny": ny,
        "px": px,
        "py": py,
        "distance": distance,
        "ox": ox,
        "oy": oy,
        "x": x,
        "y": y,
        "normal": normal,
        "spacegroup": spacegroup,
        "cell": cell,
        "a": a,
        "b": b,
        "c": c,
    }

    return results


def xds_read_xparm_new_style(xparm_file):
    """Parse the XPARM file to a dictionary."""

    with open(xparm_file) as fh:
        data = [float(x) for x in " ".join(fh.readlines()[1:]).split()]

    starting_frame = int(data[0])
    phi_start, phi_width = data[1:3]
    axis = data[3:6]

    wavelength = data[6]
    beam = data[7:10]

    spacegroup = int(data[10])
    cell = data[11:17]
    a, b, c = data[17:20], data[20:23], data[23:26]
    assert int(data[26]) == 1
    nx, ny = list(map(int, data[27:29]))
    px, py = data[29:31]
    ox, oy = data[31:33]
    distance = data[33]
    x, y = data[34:37], data[37:40]
    normal = data[40:43]

    results = {
        "starting_frame": starting_frame,
        "phi_start": phi_start,
        "phi_width": phi_width,
        "axis": axis,
        "wavelength": wavelength,
        "beam": beam,
        "nx": nx,
        "ny": ny,
        "px": px,
        "py": py,
        "distance": distance,
        "ox": ox,
        "oy": oy,
        "x": x,
        "y": y,
        "normal": normal,
        "spacegroup": spacegroup,
        "cell": cell,
        "a": a,
        "b": b,
        "c": c,
    }

    return results


def template_to_xds(template):
    from xia2.Applications.xia2setup import is_hdf5_name

    if is_hdf5_name(template):
        # Given (e.g.) XYZ_master.h5 and data files XYZ_data_00000[0-9].h5
        # XDS expects the template XYZ_??????.h5
        assert template.endswith("master.h5"), template

        # FIXME for #401 - should look into the master file for references
        # either explicitly to child data sets or via the VDS - meantimes,
        # remove the check

        # master_file = template
        # g = glob.glob(master_file.split("master.h5")[0] + "data_*[0-9].h5")
        # g.extend(glob.glob(master_file.split("master.h5")[0] + "*[0-9].h5"))
        # assert len(g), "No associated data files found for %s" % master_file

        # we don't know what is in the master file but we know at this point
        # that the word master is in there, so... otherwise can get complicated
        # side-effects when people have a folder named e.g. data_200.
        return template.replace("master.h5", "??????.h5")

    return template.replace("#", "?")


__hdf5_lib = ""


def find_hdf5_lib(template=None):
    global __hdf5_lib
    from xia2.Applications.xia2setup import is_hdf5_name

    if template and not is_hdf5_name(template):
        return ""

    if __hdf5_lib:
        return __hdf5_lib

    from xia2.Handlers.Phil import PhilIndex
    from dials.util import Sorry

    plugin_name = PhilIndex.get_python_object().xds.hdf5_plugin

    if os.path.isabs(plugin_name):
        if not os.path.exists(plugin_name):
            raise Sorry("Cannot find plugin %s" % plugin_name)
        __hdf5_lib = "LIB=%s\n" % plugin_name
        return __hdf5_lib

    for d in os.environ["PATH"].split(os.pathsep):
        if os.path.exists(os.path.join(d, plugin_name)):
            __hdf5_lib = "LIB=%s\n" % os.path.join(d, plugin_name)
            return __hdf5_lib
    return ""


__h5toxds = ""


def find_h5toxds():
    global __h5toxds
    if __h5toxds:
        return __h5toxds

    for d in os.environ["PATH"].split(os.pathsep):
        if os.path.exists(os.path.join(d, "H5ToXds")):
            __h5toxds = os.path.join(d, "H5ToXds")
    return __h5toxds


def check_xds_ok_with_h5():
    if find_hdf5_lib():
        return True
    if find_h5toxds():
        return True
    return False
