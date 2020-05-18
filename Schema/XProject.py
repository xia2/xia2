# This represents the "top level" of the .xinfo hierarchy, and should
# exactly correspond to the contents of the .xinfo file.


import inspect
import json
import logging
import os

import pathlib
from dxtbx.serialize.load import _decode_list
from xia2.Handlers.Phil import PhilIndex
from xia2.Handlers.Syminfo import Syminfo
from xia2.Handlers.XInfo import XInfo
from xia2.Schema.XCrystal import XCrystal
from xia2.Schema.XSample import XSample
from xia2.Schema.XWavelength import XWavelength

logger = logging.getLogger("xia2.Schema.XProject")


class XProject:
    """A representation of a complete project. This will contain a dictionary
    of crystals."""

    def __init__(self, xinfo_file=None, name=None, base_path=None):
        self.path = pathlib.Path(base_path or os.getcwd()).absolute()
        self._crystals = {}
        if xinfo_file:
            self._setup_from_xinfo_file(xinfo_file)
        else:
            self._name = name

    # serialization functions

    def to_dict(self):
        obj = {"__id__": "XProject"}

        attributes = inspect.getmembers(self, lambda m: not inspect.isroutine(m))
        for a in attributes:
            if a[0] == "_crystals":
                crystals = {cname: cryst.to_dict() for cname, cryst in a[1].items()}
                obj[a[0]] = crystals
            elif a[0].startswith("__"):
                continue
            elif hasattr(a[1], "__fspath__"):
                obj[a[0]] = a[1].__fspath__()
            else:
                obj[a[0]] = a[1]
        return obj

    @classmethod
    def from_dict(cls, obj, base_path=None):
        assert obj["__id__"] == "XProject"
        return_obj = cls()
        for k, v in obj.items():
            if k == "_crystals":
                v_ = {}
                for cname, cdict in v.items():
                    cryst = XCrystal.from_dict(cdict)
                    cryst._project = return_obj
                    v_[cname] = cryst
                v = v_
            setattr(return_obj, k, v)
        if hasattr(return_obj, "path"):
            return_obj.path = pathlib.Path(return_obj.path).absolute()
        else:
            return_obj.path = pathlib.Path(base_path or os.getcwd()).absolute()
        return return_obj

    def as_json(self, filename=None, compact=True):
        obj = self.to_dict()
        if compact:
            text = json.dumps(
                obj, skipkeys=True, separators=(",", ":"), ensure_ascii=True
            )
        else:
            text = json.dumps(obj, skipkeys=True, indent=2, ensure_ascii=True)

        # If a filename is set then dump to file otherwise return string
        if filename is not None:
            with open(filename, "w") as outfile:
                outfile.write(text)
        else:
            return text

    @classmethod
    def from_json(cls, filename=None, string=None):
        def _decode_dict(data):
            """ Decode a dict to str from unicode. """
            rv = {}
            for key, value in data.items():
                if isinstance(value, list):
                    value = _decode_list(value)
                elif isinstance(value, dict):
                    value = _decode_dict(value)
                try:
                    key = float(key)
                    if int(key) == key:
                        key = int(key)
                except ValueError:
                    pass
                rv[key] = value
            return rv

        assert [filename, string].count(None) == 1
        if filename:
            with open(filename, "rb") as f:
                string = f.read()
            base_path = os.path.dirname(filename)
        else:
            base_path = None
        obj = json.loads(string, object_hook=_decode_dict)
        return cls.from_dict(obj, base_path=base_path)

    def get_output(self):
        result = "Project: %s\n" % self._name

        for crystal in self._crystals:
            result += self._crystals[crystal].get_output()
        return result[:-1]

    def summarise(self):
        """Produce summary information."""

        summary = ["Project: %s" % self._name]
        for crystal in self._crystals:
            for record in self._crystals[crystal].summarise():
                summary.append(record)

        return summary

    def get_name(self):
        return self._name

    def add_crystal(self, xcrystal):
        """Add a new xcrystal to the project."""

        if not xcrystal.__class__.__name__ == "XCrystal":
            raise RuntimeError("crystal must be class XCrystal.")

        if xcrystal.get_name() in self._crystals:
            raise RuntimeError(
                "XCrystal with name %s already exists" % xcrystal.get_name()
            )

        self._crystals[xcrystal.get_name()] = xcrystal

    def get_crystals(self):
        return self._crystals

    def _setup_from_xinfo_file(self, xinfo_file):
        """Set up this object & all subobjects based on the .xinfo
        file contents."""

        settings = PhilIndex.params.xia2.settings

        sweep_ids = [sweep.id for sweep in settings.sweep]
        sweep_ranges = [sweep.range for sweep in settings.sweep]

        if not sweep_ids:
            sweep_ids = None
            sweep_ranges = None

        xinfo = XInfo(xinfo_file, sweep_ids=sweep_ids, sweep_ranges=sweep_ranges)

        self._name = xinfo.get_project()
        crystals = xinfo.get_crystals()

        for crystal in crystals:
            xc = XCrystal(crystal, self)
            if "sequence" in crystals[crystal]:
                xc.set_aa_sequence(crystals[crystal]["sequence"])
            if "ha_info" in crystals[crystal]:
                if crystals[crystal]["ha_info"] != {}:
                    xc.set_ha_info(crystals[crystal]["ha_info"])

            if "scaled_merged_reflection_file" in crystals[crystal]:
                xc.set_scaled_merged_reflections(
                    crystals[crystal]["scaled_merged_reflections"]
                )

            if "reference_reflection_file" in crystals[crystal]:
                xc.set_reference_reflection_file(
                    crystals[crystal]["reference_reflection_file"]
                )
            if "freer_file" in crystals[crystal]:
                xc.set_freer_file(crystals[crystal]["freer_file"])

            # user assigned spacegroup
            if "user_spacegroup" in crystals[crystal]:
                xc.set_user_spacegroup(crystals[crystal]["user_spacegroup"])
            elif settings.space_group is not None:
                # XXX do we ever actually get here?
                xc.set_user_spacegroup(settings.space_group.type().lookup_symbol())

            # add a default sample if none present in xinfo file
            if not crystals[crystal]["samples"]:
                crystals[crystal]["samples"]["X1"] = {}

            for sample in crystals[crystal]["samples"]:
                xsample = XSample(sample, xc)
                xc.add_sample(xsample)

            if not crystals[crystal]["wavelengths"]:
                raise RuntimeError("No wavelengths specified in xinfo file")

            for wavelength, wave_info in crystals[crystal]["wavelengths"].items():
                # FIXME 29/NOV/06 in here need to be able to cope with
                # no wavelength information - this should default to the
                # information in the image header (John Cowan pointed
                # out that this was untidy - requiring that it agrees
                # with the value in the header makes this almost
                # useless.)

                if "wavelength" not in wave_info:
                    logger.debug(
                        "No wavelength value given for wavelength %s", wavelength
                    )
                else:
                    logger.debug(
                        "Overriding value for wavelength %s to %8.6f",
                        wavelength,
                        float(wave_info["wavelength"]),
                    )

                # handle case where user writes f" in place of f''

                if 'f"' in wave_info and "f''" not in wave_info:
                    wave_info["f''"] = wave_info['f"']

                xw = XWavelength(
                    wavelength,
                    xc,
                    wavelength=wave_info.get("wavelength", 0.0),
                    f_pr=wave_info.get("f'", 0.0),
                    f_prpr=wave_info.get("f''", 0.0),
                    dmin=wave_info.get("dmin", 0.0),
                    dmax=wave_info.get("dmax", 0.0),
                )

                # in here I also need to look and see if we have
                # been given any scaled reflection files...

                # check to see if we have a user supplied lattice...
                if "user_spacegroup" in crystals[crystal]:
                    lattice = Syminfo.get_lattice(crystals[crystal]["user_spacegroup"])
                elif settings.space_group is not None:
                    # XXX do we ever actually get here?
                    lattice = Syminfo.get_lattice(
                        settings.space_group.type().lookup_symbol()
                    )
                else:
                    lattice = None

                # and also user supplied cell constants - from either
                # the xinfo file (the first port of call) or the
                # command-line.

                if "user_cell" in crystals[crystal]:
                    cell = crystals[crystal]["user_cell"]
                elif settings.unit_cell is not None:
                    # XXX do we ever actually get here?
                    cell = settings.unit_cell.parameters()
                else:
                    cell = None

                dmin = wave_info.get("dmin", 0.0)
                dmax = wave_info.get("dmax", 0.0)

                if dmin == 0.0 and dmax == 0.0:
                    dmin = PhilIndex.params.xia2.settings.resolution.d_min
                    dmax = PhilIndex.params.xia2.settings.resolution.d_max

                # want to be able to locally override the resolution limits
                # for this sweep while leaving the rest for the data set
                # intact...

                for sweep_name, sweep_info in crystals[crystal]["sweeps"].items():
                    sample_name = sweep_info.get("sample")
                    if sample_name is None:
                        if len(crystals[crystal]["samples"]) == 1:
                            sample_name = list(crystals[crystal]["samples"])[0]
                        else:
                            raise RuntimeError(
                                "No sample given for sweep %s" % sweep_name
                            )

                    xsample = xc.get_xsample(sample_name)
                    assert xsample is not None

                    dmin_old = dmin
                    dmax_old = dmax

                    if "RESOLUTION" in sweep_info:
                        values = [float(x) for x in sweep_info["RESOLUTION"].split()]
                        if len(values) == 1:
                            dmin = values[0]
                        elif len(values) == 2:
                            dmin = min(values)
                            dmax = max(values)
                        else:
                            raise RuntimeError(
                                "bad resolution for sweep %s" % sweep_name
                            )

                    if sweep_info["wavelength"] == wavelength:
                        frames_to_process = sweep_info.get("start_end")

                        xsweep = xw.add_sweep(
                            sweep_name,
                            sample=xsample,
                            directory=sweep_info.get("DIRECTORY"),
                            image=sweep_info.get("IMAGE"),
                            beam=sweep_info.get("beam"),
                            reversephi=sweep_info.get("reversephi", False),
                            distance=sweep_info.get("distance"),
                            gain=float(sweep_info.get("GAIN", 0.0)),
                            dmin=dmin,
                            dmax=dmax,
                            polarization=float(sweep_info.get("POLARIZATION", 0.0)),
                            frames_to_process=frames_to_process,
                            user_lattice=lattice,
                            user_cell=cell,
                            epoch=sweep_info.get("epoch", 0),
                            ice=sweep_info.get("ice", False),
                            excluded_regions=sweep_info.get("excluded_regions", []),
                        )

                        xsample.add_sweep(xsweep)

                    dmin = dmin_old
                    dmax = dmax_old

                xc.add_wavelength(xw)

            self.add_crystal(xc)
