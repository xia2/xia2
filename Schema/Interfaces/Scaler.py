import inspect
import json
import logging
import os
import pathlib

from dxtbx.serialize.load import _decode_dict
from xia2.Handlers.Streams import banner

logger = logging.getLogger("xia2.Schema.Interfaces.Scaler")


class Scaler:
    """An interface to present scaling functionality in a similar way to the
    integrater interface."""

    def __init__(self, base_path=None):
        # key this by the epoch, if available, else will need to
        # do something different.
        self._scalr_integraters = {}

        self._scalr_corrections = False
        self._scalr_correct_decay = None
        self._scalr_correct_modulation = None
        self._scalr_correct_absorption = None

        # integraters have the following methods for pulling interesting
        # information out:
        #
        # get_integrater_project_info() - pname, xname, dname
        # get_integrater_epoch() - measurement of first frame

        self.scaler_reset()

        self._scalr_reference_reflection_file = None
        self._scalr_freer_file = None

        # user input to guide spacegroup choices
        self._scalr_input_spacegroup = None
        self._scalr_input_pointgroup = None

        # places to hold the output

        # this should be a dictionary keyed by datset / format, or
        # format / dataset
        self._scalr_scaled_reflection_files = None

        # this needs to be a dictionary keyed by dataset etc, e.g.
        # key = pname, xname, dname
        self._scalr_statistics = None

        # and also the following keys:
        self._scalr_statistics_keys = [
            "High resolution limit",
            "Low resolution limit",
            "Completeness",
            "Multiplicity",
            "I/sigma",
            "Rmerge(I)",
            "Rmerge(I+/I-)",
            "Rmeas(I)",
            "Rmeas(I+/-)",
            "Rpim(I)",
            "Rpim(I+/-)",
            "CC half",
            "Wilson B factor",
            "Partial bias",
            "Anomalous completeness",
            "Anomalous multiplicity",
            "Anomalous correlation",
            "Anomalous slope",
            "dF/F",
            "dI/s(dI)",
            "Total observations",
            "Total unique",
        ]

        # information for returning "interesting facts" about the data
        self._scalr_highest_resolution = 0.0
        self._scalr_cell = None
        self._scalr_cell_esd = None
        self._scalr_cell_dict = {}
        self._scalr_likely_spacegroups = []
        self._scalr_unlikely_spacegroups = []

        # do we want anomalous pairs separating?
        self._scalr_anomalous = False

        # admin junk
        self._base_path = base_path
        self._working_directory = os.getcwd()
        self._scalr_pname = None
        self._scalr_xname = None

        # link to parent xcrystal
        self._scalr_xcrystal = None

        self._scalr_resolution_limits = {}

    # serialization functions

    def to_dict(self):
        obj = {}
        obj["__id__"] = "Scaler"
        obj["__module__"] = self.__class__.__module__
        obj["__name__"] = self.__class__.__name__
        if self._base_path:
            obj["_base_path"] = self._base_path.__fspath__()

        attributes = inspect.getmembers(self, lambda m: not inspect.isroutine(m))
        for a in attributes:
            if a[0] == "_scalr_xcrystal":
                # XXX I guess we probably want this?
                continue
            elif a[0] == "_scalr_integraters":
                d = {}
                for k, v in a[1].items():
                    d[k] = v.to_dict()
                obj[a[0]] = d
            elif a[0] == "_scalr_statistics" and a[1] is not None:
                # dictionary has tuples as keys - json can't handle this so serialize
                # keys in place
                d = {}
                for k, v in a[1].items():
                    k = json.dumps(k)
                    d[k] = v
                obj[a[0]] = d
            elif a[0] == "_scalr_resolution_limits":
                d = {}
                for k, v in a[1].items():
                    k = json.dumps(k)
                    d[k] = v
                obj[a[0]] = d
            elif a[0].startswith("_scalr_"):
                obj[a[0]] = a[1]
        return obj

    @classmethod
    def from_dict(cls, obj):
        assert obj["__id__"] == "Scaler"
        base_path = obj.get("_base_path")
        if base_path:
            base_path = pathlib.Path(base_path)
        else:
            base_path = None
        return_obj = cls(base_path=base_path)
        for k, v in obj.items():
            if k == "_scalr_integraters":
                for k_, v_ in v.items():
                    from libtbx.utils import import_python_object

                    integrater_cls = import_python_object(
                        import_path=".".join((v_["__module__"], v_["__name__"])),
                        error_prefix="",
                        target_must_be="",
                        where_str="",
                    ).object
                    v[k_] = integrater_cls.from_dict(v_)
            elif k == "_scalr_statistics" and v is not None:
                d = {}
                for k_, v_ in v.items():
                    k_ = tuple(str(s) for s in json.loads(k_))
                    d[k_] = v_
                v = d
            elif k == "_scalr_resolution_limits":
                d = {}
                for k_, v_ in v.items():
                    k_ = tuple(str(s) for s in json.loads(k_))
                    d[k_] = v_
                v = d
            elif k == "_base_path":
                continue
            setattr(return_obj, k, v)
        return return_obj

    def as_json(self, filename=None, compact=False):
        obj = self.to_dict()
        if compact:
            text = json.dumps(
                obj, skipkeys=False, separators=(",", ":"), ensure_ascii=True
            )
        else:
            text = json.dumps(obj, skipkeys=False, indent=2, ensure_ascii=True)

        # If a filename is set then dump to file otherwise return string
        if filename is not None:
            with open(filename, "w") as outfile:
                outfile.write(text)
        else:
            return text

    @classmethod
    def from_json(cls, filename=None, string=None):
        assert [filename, string].count(None) == 1
        if filename is not None:
            with open(filename) as f:
                string = f.read()
        obj = json.loads(string, object_hook=_decode_dict)
        return cls.from_dict(obj)

    def _scale_prepare(self):
        raise NotImplementedError("overload me")

    def _scale(self):
        raise NotImplementedError("overload me")

    def _scale_finish(self):
        pass

    def set_working_directory(self, working_directory):
        self._working_directory = working_directory

    def get_working_directory(self):
        return self._working_directory

    def set_scaler_input_spacegroup(self, spacegroup):
        self._scalr_input_spacegroup = spacegroup

    def set_scaler_input_pointgroup(self, pointgroup):
        self._scalr_input_pointgroup = pointgroup

    def set_scaler_xcrystal(self, xcrystal):
        self._scalr_xcrystal = xcrystal

    def get_scaler_xcrystal(self):
        return self._scalr_xcrystal

    def set_scaler_project_info(self, pname, xname):
        """Set the project and crystal this scaler is working with."""

        self._scalr_pname = pname
        self._scalr_xname = xname

    def set_scaler_reference_reflection_file(self, reference_reflection_file):
        self._scalr_reference_reflection_file = reference_reflection_file

    def get_scaler_reference_reflection_file(self):
        return self._scalr_reference_reflection_file

    def set_scaler_freer_file(self, freer_file):
        self._scalr_freer_file = freer_file

    def get_scaler_freer_file(self):
        return self._scalr_freer_file

    def get_scaler_resolution_limits(self):
        return self._scalr_resolution_limits

    def set_scaler_prepare_done(self, done=True):
        frm = inspect.stack()[1]
        mod = inspect.getmodule(frm[0])
        logger.debug(
            "Called scaler prepare done from %s %d (%s)"
            % (mod.__name__, frm[0].f_lineno, done)
        )

        self._scalr_prepare_done = done

    def set_scaler_done(self, done=True):
        frm = inspect.stack()[1]
        mod = inspect.getmodule(frm[0])
        logger.debug(
            "Called scaler done from %s %d (%s)" % (mod.__name__, frm[0].f_lineno, done)
        )

        self._scalr_done = done

    def set_scaler_finish_done(self, done=True):
        frm = inspect.stack()[1]
        mod = inspect.getmodule(frm[0])
        logger.debug(
            "Called scaler finish done from %s %d (%s)"
            % (mod.__name__, frm[0].f_lineno, done)
        )

        self._scalr_finish_done = done

    def set_scaler_anomalous(self, anomalous):
        self._scalr_anomalous = anomalous

    def get_scaler_anomalous(self):
        return self._scalr_anomalous

    def scaler_reset(self):
        logger.debug("Scaler reset")

        self._scalr_done = False
        self._scalr_prepare_done = False
        self._scalr_finish_done = False
        self._scalr_result = None

    # getters for the scaling model which was used - first see that the
    # corrections were applied, then the individual getters for the
    # separate corrections

    # getters of the status - note how the gets cascade to ensure that
    # everything is up-to-date...

    def get_scaler_prepare_done(self):
        return self._scalr_prepare_done

    def get_scaler_done(self):
        if not self.get_scaler_prepare_done():
            logger.debug("Resetting Scaler done as prepare not done")
            self.set_scaler_done(False)
        return self._scalr_done

    def get_scaler_finish_done(self):
        if not self.get_scaler_done():
            logger.debug("Resetting scaler finish done as scaling not done")
            self.set_scaler_finish_done(False)
        return self._scalr_finish_done

    def add_scaler_integrater(self, integrater):
        """Add an integrater to this scaler, to provide the input."""

        # epoch values are trusted as long as they are unique.
        # if a collision is detected, all epoch values are replaced by an
        # integer series, starting with 0

        if 0 in self._scalr_integraters:
            epoch = len(self._scalr_integraters)

        else:
            epoch = integrater.get_integrater_epoch()

            # FIXME This is now probably superflous?
            if epoch == 0 and self._scalr_integraters:
                raise RuntimeError("multi-sweep integrater has epoch 0")

            if epoch in self._scalr_integraters:
                logger.debug(
                    "integrater with epoch %d already exists. will not trust epoch values"
                    % epoch
                )

                # collision. Throw away all epoch keys, and replace with integer series
                self._scalr_integraters = dict(
                    enumerate(self._scalr_integraters.values())
                )
                epoch = len(self._scalr_integraters)

        self._scalr_integraters[epoch] = integrater

        self.scaler_reset()

    def scale(self):
        """Actually perform the scaling - this is delegated to the
        implementation."""

        if self._scalr_integraters == {}:
            raise RuntimeError("no Integrater implementations assigned for scaling")

        xname = self._scalr_xcrystal.get_name()

        while not self.get_scaler_finish_done():
            while not self.get_scaler_done():
                while not self.get_scaler_prepare_done():

                    logger.notice(banner("Preparing %s" % xname))

                    self._scalr_prepare_done = True
                    self._scale_prepare()

                logger.notice(banner("Scaling %s" % xname))

                self._scalr_done = True
                self._scalr_result = self._scale()

            self._scalr_finish_done = True
            self._scale_finish()

        return self._scalr_result

    def get_scaled_reflections(self, format):
        """Get a specific format of scaled reflection files. This may
        trigger transmogrification of files."""

        if format not in ("mtz", "sca", "mtz_unmerged", "sca_unmerged"):
            raise RuntimeError("format %s unknown" % format)

        self.scale()

        if format in self._scalr_scaled_reflection_files:
            return self._scalr_scaled_reflection_files[format]

        raise RuntimeError("unknown format %s" % format)

    def get_scaled_merged_reflections(self):
        """Return the reflection files and so on."""

        self.scale()
        return self._scalr_scaled_reflection_files

    def get_scaler_statistics(self):
        """Return the overall scaling statistics."""

        self.scale()
        return self._scalr_statistics

    def get_scaler_cell(self):
        """Return the final unit cell from scaling."""

        self.scale()
        return self._scalr_cell

    def get_scaler_cell_esd(self):
        """Return the estimated standard deviation of the final unit cell."""

        self.scale()
        return self._scalr_cell_esd

    def get_scaler_likely_spacegroups(self):
        """Return a list of likely spacegroups - you should try using
        the first in this list first."""

        self.scale()
        return self._scalr_likely_spacegroups

    def get_scaler_highest_resolution(self):
        """Get the highest resolution achieved by the crystal."""

        self.scale()
        return self._scalr_highest_resolution
