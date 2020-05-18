# A versioning object representing the wavelength level in the .xinfo
# hierarchy. This will include all of the methods for performing operations
# on a wavelength as well as stuff for integration with the rest of the
# .xinfo hierarchy.
#
# The following are properties defined for an XWavelength object:
#
# wavelength
# f_pr
# f_prpr
#
# However, these objects are not versioned, since they do not (in the current
# implementation) impact on the data reduction process. These are mostly
# passed through.
#
# FIXME 05/SEP/06 this also needs to be able to handle the information
#                 pertaining to the lattice, because it is critcial that
#                 all of the sweeps for a wavelength share the same
#                 lattice.
#
# FIXME 05/SEP/06 also don't forget about ordering the sweeps in collection
#                 order for the data reduction, to make sure that we
#                 reduce the least damaged data first.


import inspect
import logging

from xia2.Handlers.Phil import PhilIndex
from xia2.Schema.XSweep import XSweep

logger = logging.getLogger("xia2.Schema.XWavelength")


class XWavelength:
    """An object representation of a wavelength, which will after data
    reduction correspond to an MTZ hierarchy dataset."""

    def __init__(
        self, name, crystal, wavelength, f_pr=0.0, f_prpr=0.0, dmin=0.0, dmax=0.0
    ):
        """Create a new wavelength named name, belonging to XCrystal object
        crystal, with wavelength and optionally f_pr, f_prpr assigned."""

        # set up this object

        self._name = name
        self._crystal = crystal
        self._wavelength = wavelength
        self._f_pr = f_pr
        self._f_prpr = f_prpr
        self._resolution_high = dmin
        self._resolution_low = dmax

        # then create space to store things which are contained
        # in here - the sweeps

        self._sweeps = []

    # serialization functions

    def to_dict(self):
        obj = {"__id__": "XWavelength"}
        attributes = inspect.getmembers(self, lambda m: not (inspect.isroutine(m)))
        for a in attributes:
            if a[0] == "_sweeps":
                sweeps = []
                for sweep in a[1]:
                    sweeps.append(sweep.to_dict())
                obj[a[0]] = sweeps
            elif a[0] == "_crystal":
                # don't serialize this since the parent xwavelength *should* contain
                # the reference to the child xsweep
                continue
            elif a[0].startswith("__"):
                continue
            else:
                obj[a[0]] = a[1]
        return obj

    @classmethod
    def from_dict(cls, obj):
        assert obj["__id__"] == "XWavelength"
        return_obj = cls(name=None, crystal=None, wavelength=None)
        for k, v in obj.items():
            if k == "_sweeps":
                v = [XSweep.from_dict(s_dict) for s_dict in v]
                for sweep in v:
                    sweep._wavelength = return_obj
            setattr(return_obj, k, v)
        return return_obj

    def get_output(self):
        result = "Wavelength name: %s\n" % self._name
        result += "Wavelength %7.5f\n" % self._wavelength
        if self._f_pr != 0.0 and self._f_prpr != 0.0:
            result += f"F', F'' = ({self._f_pr:5.2f}, {self._f_prpr:5.2f})\n"

        result += "Sweeps:\n"

        remove = []

        params = PhilIndex.get_python_object()
        failover = params.xia2.settings.failover

        for s in self._sweeps:
            # would be nice to put this somewhere else in the hierarchy - not
            # sure how to do that though (should be handled in Interfaces?)
            try:
                result += "%s\n" % s.get_output()
            except Exception as e:
                if failover:
                    logger.warning(
                        "Processing sweep %s failed: %s", s.get_name(), str(e)
                    )
                    remove.append(s)
                else:
                    raise

        for s in remove:
            self._sweeps.remove(s)

        return result[:-1]

    def summarise(self):
        summary = [f"Wavelength: {self._name} ({self._wavelength:7.5f})"]

        for s in self._sweeps:
            for record in s.summarise():
                summary.append(record)

        return summary

    def get_wavelength(self):
        return self._wavelength

    def set_wavelength(self, wavelength):
        if self._wavelength != 0.0:
            raise RuntimeError("setting wavelength when already set")
        self._wavelength = wavelength

    def set_resolution_high(self, resolution_high):
        self._resolution_high = resolution_high

    def set_resolution_low(self, resolution_low):
        self._resolution_low = resolution_low

    def get_resolution_high(self):
        return self._resolution_high

    def get_resolution_low(self):
        return self._resolution_low

    def get_f_pr(self):
        return self._f_pr

    def get_f_prpr(self):
        return self._f_prpr

    def get_crystal(self):
        return self._crystal

    def get_name(self):
        return self._name

    def get_all_image_names(self):
        """Get a full list of all images in this wavelength..."""

        # for RD analysis ...

        result = []
        for sweep in self._sweeps:
            result.extend(sweep.get_all_image_names())
        return result

    def add_sweep(
        self,
        name,
        sample,
        directory=None,
        image=None,
        beam=None,
        reversephi=False,
        distance=None,
        gain=0.0,
        dmin=0.0,
        dmax=0.0,
        polarization=0.0,
        frames_to_process=None,
        user_lattice=None,
        user_cell=None,
        epoch=0,
        ice=False,
        excluded_regions=None,
    ):
        """Add a sweep to this wavelength."""
        if excluded_regions is None:
            excluded_regions = []

        xsweep = XSweep(
            name,
            self,
            sample=sample,
            directory=directory,
            image=image,
            beam=beam,
            reversephi=reversephi,
            distance=distance,
            gain=gain,
            dmin=dmin,
            dmax=dmax,
            polarization=polarization,
            frames_to_process=frames_to_process,
            user_lattice=user_lattice,
            user_cell=user_cell,
            epoch=epoch,
            ice=ice,
            excluded_regions=excluded_regions,
        )
        self._sweeps.append(xsweep)

        return xsweep

    def get_sweeps(self):
        return self._sweeps

    def remove_sweep(self, sweep):
        """Remove a sweep object from this wavelength."""

        try:
            self._sweeps.remove(sweep)
        except ValueError:
            pass

    def _get_integraters(self):
        return [s._get_integrater() for s in self._sweeps]

    def _get_indexers(self):
        return [s._get_indexer() for s in self._sweeps]
