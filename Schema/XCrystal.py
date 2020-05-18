import collections
import inspect
import os

from xia2.Handlers.CIF import CIF, mmCIF
from xia2.Handlers.Files import FileHandler
from xia2.Handlers.Phil import PhilIndex
from xia2.Handlers.Streams import banner
from xia2.Handlers.Syminfo import Syminfo
from xia2.lib.NMolLib import compute_nmol, compute_solvent
from xia2.Modules.Scaler.ScalerFactory import Scaler
from dxtbx.util import format_float_with_standard_uncertainty


class _aa_sequence:
    """An object to represent the amino acid sequence."""

    def __init__(self, sequence):
        self._sequence = sequence

    def set_sequence(self, sequence):
        self._sequence = sequence

    def get_sequence(self):
        return self._sequence

    # serialization functions

    def to_dict(self):
        obj = {}
        obj["__id__"] = "aa_sequence"

        attributes = inspect.getmembers(self, lambda m: not inspect.isroutine(m))
        for a in attributes:
            if a[0].startswith("__"):
                continue
            else:
                obj[a[0]] = a[1]
        return obj

    @classmethod
    def from_dict(cls, obj):
        assert obj["__id__"] == "aa_sequence"
        return_obj = cls(obj["_sequence"])
        for k, v in obj.items():
            setattr(return_obj, k, v)
        return return_obj


class _ha_info:
    """A versioned class to represent the heavy atom information."""

    # FIXME in theory we could have > 1 of these to represent e.g. different
    # metal ions naturally present in the molecule, but for the moment
    # just think in terms of a single one (though couldn't hurt to
    # keep them in a list.)

    def __init__(self, atom, number_per_monomer=0, number_total=0):
        self._atom = atom
        self._number_per_monomer = number_per_monomer
        self._number_total = number_total

    def set_number_per_monomer(self, number_per_monomer):
        self._number_per_monomer = number_per_monomer

    def set_number_total(self, number_total):
        self._number_total = number_total

    def to_dict(self):
        obj = {}
        obj["__id__"] = "ha_info"

        attributes = inspect.getmembers(self, lambda m: not (inspect.isroutine(m)))
        for a in attributes:
            if a[0].startswith("__"):
                continue
            else:
                obj[a[0]] = a[1]
        return obj

    @classmethod
    def from_dict(cls, obj):
        assert obj["__id__"] == "ha_info"
        return_obj = cls(obj["_atom"])
        for k, v in obj.items():
            setattr(return_obj, k, v)
        return return_obj


formats = collections.OrderedDict(
    [
        ("High resolution limit", " %7.2f"),
        ("Low resolution limit", " %7.2f"),
        ("Completeness", "%7.1f"),
        ("Multiplicity", "%7.1f"),
        ("I/sigma", "%7.1f"),
        ("Rmerge(I)", "%7.3f"),
        ("Rmerge(I+/-)", "%7.3f"),
        ("Rmeas(I)", "%7.3f"),
        ("Rmeas(I+/-)", "%7.3f"),
        ("Rpim(I)", "%7.3f"),
        ("Rpim(I+/-)", "%7.3f"),
        ("CC half", "%7.3f"),
        ("Wilson B factor", "%7.3f"),
        ("Partial bias", "%7.3f"),
        ("Anomalous completeness", "%7.1f"),
        ("Anomalous multiplicity", "%7.1f"),
        ("Anomalous correlation", "%7.3f"),
        ("Anomalous slope", "%7.3f"),
        ("dF/F", "%7.3f"),
        ("dI/s(dI)", "%7.3f"),
        ("Total observations", "%7d"),
        ("Total unique", "%7d"),
    ]
)


def format_statistics(statistics, caption=None):
    """Format for printing statistics from data processing, removing from
    the main XCrystal __repr__ method. See DLS #1291"""

    available = list(statistics.keys())

    result = ""
    columns = len(statistics.get("Completeness", [1, 2, 3]))
    if caption:
        result += caption.ljust(44)
        if columns == 3:
            result += " Overall    Low     High"
        elif columns == 4:
            result += "Suggested   Low    High  Overall"
        result += "\n"

    for k, format_str in formats.items():
        if k in available:
            try:
                row_data = statistics[k]
                if columns == 4 and len(row_data) == 1:  # place value in suggest column
                    row_data = [None] * (columns - 1) + row_data
                row_format = [format_str] + [format_str.strip()] * (len(row_data) - 1)
                formatted = " ".join(
                    (f % k) if k is not None else (" " * len(f % 0))
                    for f, k in zip(row_format, row_data)
                )
            except TypeError:
                formatted = "(error)"
            result += k.ljust(44) + formatted + "\n"

    return result


class XCrystal:
    """An object to maintain all of the information about a crystal. This
    will contain the experimental information in XWavelength objects,
    and also amino acid sequence, heavy atom information."""

    def __init__(self, name, project):
        self._name = name

        # separate out the anomalous pairs or merge them together?
        self._anomalous = False

        # FIXME check that project is an XProject
        self._project = project

        # these should be populated with the objects defined above
        self._aa_sequence = None

        # note that I am making allowances for > 1 heavy atom class...
        # FIXME 18/SEP/06 these should be in a dictionary which is keyed
        # by the element name...
        self._ha_info = {}
        self._wavelengths = {}
        self._samples = {}

        # hooks to dangle command interfaces from
        self._scaler = None
        self._refiner = None

        # things to store input reflections which are used to define
        # the setting... this will be passed into the Scaler if
        # defined... likewise the FreeR column file
        self._reference_reflection_file = None
        self._freer_file = None
        self._user_spacegroup = None

        # things to help the great passing on of information
        self._scaled_merged_reflections = None

        # derived information
        self._nmol = 1

    # serialization functions

    def to_dict(self):
        obj = {"__id__": "XCrystal"}

        attributes = inspect.getmembers(self, lambda m: not (inspect.isroutine(m)))
        for a in attributes:
            if a[0] == "_scaler" and a[1] is not None:
                obj[a[0]] = a[1].to_dict()
            elif a[0] == "_wavelengths":
                wavs = {}
                for wname, wav in a[1].items():
                    wavs[wname] = wav.to_dict()
                obj[a[0]] = wavs
            elif a[0] == "_samples":
                samples = {}
                for sname, sample in a[1].items():
                    samples[sname] = sample.to_dict()
                obj[a[0]] = samples
            elif a[0] == "_project":
                # don't serialize this since the parent xproject *should* contain
                # the pointer to the child xcrystal
                continue
            elif a[0] == "_aa_sequence" and a[1] is not None:
                obj[a[0]] = a[1].to_dict()
            elif a[0] == "_ha_info" and a[1] is not None:
                d = {}
                for k, v in a[1].items():
                    d[k] = v.to_dict()
                obj[a[0]] = d
            elif a[0].startswith("__"):
                continue
            else:
                obj[a[0]] = a[1]
        return obj

    @classmethod
    def from_dict(cls, obj):
        from xia2.Schema.XWavelength import XWavelength
        from xia2.Schema.XSample import XSample

        assert obj["__id__"] == "XCrystal"
        return_obj = cls(name=None, project=None)
        for k, v in obj.items():
            if k == "_scaler" and v is not None:
                from libtbx.utils import import_python_object

                cls = import_python_object(
                    import_path=".".join((v["__module__"], v["__name__"])),
                    error_prefix="",
                    target_must_be="",
                    where_str="",
                ).object
                v = cls.from_dict(v)
                v._scalr_xcrystal = return_obj
            elif k == "_wavelengths":
                v_ = {}
                for wname, wdict in v.items():
                    wav = XWavelength.from_dict(wdict)
                    wav._crystal = return_obj
                    v_[wname] = wav
                v = v_
            elif k == "_samples":
                v_ = {}
                for sname, sdict in v.items():
                    sample = XSample.from_dict(sdict)
                    sample._crystal = return_obj
                    v_[sname] = sample
                v = v_
            elif k == "_aa_sequence" and v is not None:
                v = _aa_sequence.from_dict(v)
            elif k == "_ha_info" and v is not None:
                for k_, v_ in v.items():
                    v[k_] = _ha_info.from_dict(v_)
            setattr(return_obj, k, v)
        for sample in return_obj._samples.values():
            for i, sname in enumerate(sample._sweeps):
                found_sweep = False
                for wav in list(return_obj._wavelengths.values()):
                    if found_sweep:
                        break
                    for sweep in wav._sweeps:
                        if sweep.get_name() == sname:
                            sample._sweeps[i] = sweep
                            sweep.sample = sample
                            found_sweep = True
                            break
            for s in sample._sweeps:
                assert not isinstance(s, str)
        if return_obj._scaler is not None:
            for intgr in return_obj._get_integraters():
                return_obj._scaler._scalr_integraters[
                    intgr.get_integrater_epoch()
                ] = intgr
                if (
                    hasattr(return_obj._scaler, "_sweep_handler")
                    and return_obj._scaler._sweep_handler is not None
                ):
                    if (
                        intgr.get_integrater_epoch()
                        in return_obj._scaler._sweep_handler._sweep_information
                    ):
                        return_obj._scaler._sweep_handler._sweep_information[
                            intgr.get_integrater_epoch()
                        ]._integrater = intgr
        return return_obj

    def get_output(self):
        result = "Crystal: %s\n" % self._name

        if self._aa_sequence:
            result += "Sequence: %s\n" % self._aa_sequence.get_sequence()
        for wavelength in list(self._wavelengths.keys()):
            result += self._wavelengths[wavelength].get_output()

        scaler = self._get_scaler()
        if scaler.get_scaler_finish_done():
            for wname, xwav in self._wavelengths.items():
                for xsweep in xwav.get_sweeps():
                    idxr = xsweep._get_indexer()
                    if PhilIndex.params.xia2.settings.show_template:
                        result += "%s\n" % banner(
                            "Autoindexing %s (%s)"
                            % (idxr.get_indexer_sweep_name(), idxr.get_template())
                        )
                    else:
                        result += "%s\n" % banner(
                            "Autoindexing %s" % idxr.get_indexer_sweep_name()
                        )
                    result += "%s\n" % idxr.show_indexer_solutions()

                    intgr = xsweep._get_integrater()
                    if PhilIndex.params.xia2.settings.show_template:
                        result += "%s\n" % banner(
                            "Integrating %s (%s)"
                            % (intgr.get_integrater_sweep_name(), intgr.get_template())
                        )
                    else:
                        result += "%s\n" % banner(
                            "Integrating %s" % intgr.get_integrater_sweep_name()
                        )
                    result += "%s\n" % intgr.show_per_image_statistics()

            result += "%s\n" % banner("Scaling %s" % self.get_name())

            for (
                (dname, sname),
                (limit, suggested),
            ) in scaler.get_scaler_resolution_limits().items():
                if suggested is None or limit == suggested:
                    result += "Resolution limit for %s/%s: %5.2f\n" % (
                        dname,
                        sname,
                        limit,
                    )
                else:
                    result += (
                        "Resolution limit for %s/%s: %5.2f (%5.2f suggested)\n"
                        % (dname, sname, limit, suggested)
                    )

        # this is now deprecated - be explicit in what you are
        # asking for...
        reflections_all = self.get_scaled_merged_reflections()
        statistics_all = self._get_scaler().get_scaler_statistics()

        # print some of these statistics, perhaps?

        for key in list(statistics_all.keys()):
            result += format_statistics(
                statistics_all[key], caption="For %s/%s/%s" % key
            )

        # then print out some "derived" information based on the
        # scaling - this is presented through the Scaler interface
        # explicitly...

        cell = self._get_scaler().get_scaler_cell()
        cell_esd = self._get_scaler().get_scaler_cell_esd()
        spacegroups = self._get_scaler().get_scaler_likely_spacegroups()

        spacegroup = spacegroups[0]
        resolution = self._get_scaler().get_scaler_highest_resolution()

        from cctbx import sgtbx

        sg = sgtbx.space_group_type(str(spacegroup))
        spacegroup = sg.lookup_symbol()
        CIF.set_spacegroup(sg)
        mmCIF.set_spacegroup(sg)

        if len(self._wavelengths) == 1:
            CIF.set_wavelengths(
                [w.get_wavelength() for w in self._wavelengths.values()]
            )
            mmCIF.set_wavelengths(
                [w.get_wavelength() for w in self._wavelengths.values()]
            )
        else:
            for wavelength in list(self._wavelengths.keys()):
                full_wave_name = "%s_%s_%s" % (
                    self._project._name,
                    self._name,
                    wavelength,
                )
                CIF.get_block(full_wave_name)[
                    "_diffrn_radiation_wavelength"
                ] = self._wavelengths[wavelength].get_wavelength()
                mmCIF.get_block(full_wave_name)[
                    "_diffrn_radiation_wavelength"
                ] = self._wavelengths[wavelength].get_wavelength()
            CIF.set_wavelengths(
                {
                    name: wave.get_wavelength()
                    for name, wave in self._wavelengths.items()
                }
            )
            mmCIF.set_wavelengths(
                {
                    name: wave.get_wavelength()
                    for name, wave in self._wavelengths.items()
                }
            )

        result += "Assuming spacegroup: %s\n" % spacegroup
        if len(spacegroups) > 1:
            result += "Other likely alternatives are:\n"
            for sg in spacegroups[1:]:
                result += "%s\n" % sg

        if cell_esd:

            def match_formatting(dimA, dimB):
                def conditional_split(s):
                    return (
                        (s[: s.index(".")], s[s.index(".") :]) if "." in s else (s, "")
                    )

                A, B = conditional_split(dimA), conditional_split(dimB)
                maxlen = (max(len(A[0]), len(B[0])), max(len(A[1]), len(B[1])))
                return (
                    A[0].rjust(maxlen[0]) + A[1].ljust(maxlen[1]),
                    B[0].rjust(maxlen[0]) + B[1].ljust(maxlen[1]),
                )

            formatted_cell_esds = tuple(
                format_float_with_standard_uncertainty(v, sd)
                for v, sd in zip(cell, cell_esd)
            )
            formatted_rows = (formatted_cell_esds[0:3], formatted_cell_esds[3:6])
            formatted_rows = list(
                zip(*(match_formatting(l, a) for l, a in zip(*formatted_rows)))
            )
            result += "Unit cell (with estimated std devs):\n"
            result += "%s %s %s\n%s %s %s\n" % (formatted_rows[0] + formatted_rows[1])
        else:
            result += "Unit cell:\n"
            result += "%7.3f %7.3f %7.3f\n%7.3f %7.3f %7.3f\n" % tuple(cell)

        # now, use this information and the sequence (if provided)
        # and also matthews_coef (should I be using this directly, here?)
        # to compute a likely number of molecules in the ASU and also
        # the solvent content...

        if self._aa_sequence:
            residues = self._aa_sequence.get_sequence()
            if residues:
                nres = len(residues)

                # first compute the number of molecules using the K&R
                # method

                nmol = compute_nmol(
                    cell[0],
                    cell[1],
                    cell[2],
                    cell[3],
                    cell[4],
                    cell[5],
                    spacegroup,
                    resolution,
                    nres,
                )

                # then compute the solvent fraction

                solvent = compute_solvent(
                    cell[0],
                    cell[1],
                    cell[2],
                    cell[3],
                    cell[4],
                    cell[5],
                    spacegroup,
                    nmol,
                    nres,
                )

                result += "Likely number of molecules in ASU: %d\n" % nmol
                result += "Giving solvent fraction:        %4.2f\n" % solvent

                self._nmol = nmol

        if isinstance(reflections_all, type({})):
            for format in list(reflections_all.keys()):
                result += "%s format:\n" % format
                reflections = reflections_all[format]

                if isinstance(reflections, type({})):
                    for wavelength in list(reflections.keys()):
                        target = FileHandler.get_data_file(
                            self._project.path, reflections[wavelength]
                        )
                        result += f"Scaled reflections ({wavelength}): {target}\n"

                else:
                    target = FileHandler.get_data_file(self._project.path, reflections)
                    result += "Scaled reflections: %s\n" % target

        CIF.write_cif(self._project.path / "DataFiles")
        mmCIF.write_cif(self._project.path / "DataFiles")

        return result

    def summarise(self):
        """Produce a short summary of this crystal."""

        summary = ["Crystal: %s" % self._name]

        if self._aa_sequence:
            summary.append(
                "Sequence length: %d" % len(self._aa_sequence.get_sequence())
            )

        for wavelength in list(self._wavelengths.keys()):
            for record in self._wavelengths[wavelength].summarise():
                summary.append(record)

        statistics_all = self._get_scaler().get_scaler_statistics()

        keys = (
            "High resolution limit",
            "Low resolution limit",
            "Completeness",
            "Multiplicity",
            "I/sigma",
            "Rmerge(I+/-)",
            "CC half",
            "Anomalous completeness",
            "Anomalous multiplicity",
        )
        for key in statistics_all:
            summary.append("For %s/%s/%s:" % key)
            available = statistics_all[key].keys()

            for s in keys:
                if s not in available:
                    continue

                format_str = formats[s]
                if isinstance(statistics_all[key][s], float):
                    expanded_format_str = " ".join(
                        [format_str]
                        + [format_str.strip()] * (len(statistics_all[key][s]) - 1)
                    )
                    summary.append(
                        "%s: " % (s.ljust(40))
                        + expanded_format_str % (statistics_all[key][s])
                    )
                elif isinstance(statistics_all[key][s], str):
                    summary.append("%s: %s" % (s.ljust(40), statistics_all[key][s]))
                else:
                    expanded_format_str = " ".join(
                        [format_str]
                        + [format_str.strip()] * (len(statistics_all[key][s]) - 1)
                    )
                    summary.append(
                        "%s " % s.ljust(43)
                        + expanded_format_str % tuple(statistics_all[key][s])
                    )

        cell = self._get_scaler().get_scaler_cell()
        spacegroup = self._get_scaler().get_scaler_likely_spacegroups()[0]

        summary.append("Cell: %7.3f %7.3f %7.3f %7.3f %7.3f %7.3f" % tuple(cell))
        summary.append("Spacegroup: %s" % spacegroup)

        return summary

    def set_reference_reflection_file(self, reference_reflection_file):
        """Set a reference reflection file to use to standardise the
        setting, FreeR etc."""

        # check here it is an MTZ file

        self._reference_reflection_file = reference_reflection_file

    def set_freer_file(self, freer_file):
        """Set a FreeR column file to use to standardise the FreeR column."""
        self._freer_file = freer_file

    def set_user_spacegroup(self, user_spacegroup):
        """Set a user assigned spacegroup - which needs to be propogated."""
        self._user_spacegroup = user_spacegroup

    def set_scaled_merged_reflections(self, scaled_merged_reflections):
        self._scaled_merged_reflections = scaled_merged_reflections

    def get_project(self):
        return self._project

    def get_name(self):
        return self._name

    def set_aa_sequence(self, aa_sequence):
        if not self._aa_sequence:
            self._aa_sequence = _aa_sequence(aa_sequence)
        else:
            self._aa_sequence.set_sequence(aa_sequence)

    def set_ha_info(self, ha_info_dict):
        self._anomalous = True

        atom = ha_info_dict["atom"]

        if atom in self._ha_info:
            # update this description
            if "number_per_monomer" in ha_info_dict:
                self._ha_info[atom].set_number_per_monomer(
                    ha_info_dict["number_per_monomer"]
                )
            if "number_total" in ha_info_dict:
                self._ha_info[atom].set_number_total(ha_info_dict["number_total"])

        else:
            # implant a new atom
            self._ha_info[atom] = _ha_info(atom)
            if "number_per_monomer" in ha_info_dict:
                self._ha_info[atom].set_number_per_monomer(
                    ha_info_dict["number_per_monomer"]
                )
            if "number_total" in ha_info_dict:
                self._ha_info[atom].set_number_total(ha_info_dict["number_total"])

    def get_wavelength_names(self):
        """Get a list of wavelengths belonging to this crystal."""
        return sorted(self._wavelengths)

    def get_xwavelength(self, wavelength_name):
        """Get a named xwavelength object back."""
        return self._wavelengths[wavelength_name]

    def add_wavelength(self, xwavelength):
        if xwavelength.__class__.__name__ != "XWavelength":
            raise RuntimeError("input should be an XWavelength object")

        if xwavelength.get_name() in list(self._wavelengths.keys()):
            raise RuntimeError(
                "XWavelength with name %s already exists" % xwavelength.get_name()
            )

        self._wavelengths[xwavelength.get_name()] = xwavelength

        # bug # 2326 - need to decide when we're anomalous
        if len(self._wavelengths.keys()) > 1:
            self._anomalous = True

        if xwavelength.get_f_pr() != 0.0 or xwavelength.get_f_prpr() != 0.0:
            self._anomalous = True

    def get_xsample(self, sample_name):
        """Get a named xsample object back."""
        return self._samples[sample_name]

    def add_sample(self, xsample):
        if xsample.__class__.__name__ != "XSample":
            raise RuntimeError("input should be an XSample object")

        if xsample.get_name() in list(self._samples.keys()):
            raise RuntimeError(
                "XSample with name %s already exists" % xsample.get_name()
            )

        self._samples[xsample.get_name()] = xsample

    def remove_sweep(self, s):
        """Find and remove the sweep s from this crystal."""

        for wave in list(self._wavelengths.keys()):
            self._wavelengths[wave].remove_sweep(s)

    def _get_integraters(self):
        integraters = []

        for wave in list(self._wavelengths.keys()):
            for i in self._wavelengths[wave]._get_integraters():
                integraters.append(i)

        return integraters

    def _get_indexers(self):
        indexers = []

        for wave in list(self._wavelengths.keys()):
            for i in self._wavelengths[wave]._get_indexers():
                indexers.append(i)

        return indexers

    def get_all_image_names(self):
        """Get a full list of all images from this crystal..."""

        # for RD analysis ...

        result = []
        for wavelength in list(self._wavelengths.keys()):
            result.extend(self._wavelengths[wavelength].get_all_image_names())
        return result

    def set_anomalous(self, anomalous=True):
        self._anomalous = anomalous

    def get_anomalous(self):
        return self._anomalous

    # "power" methods - now where these actually perform some real calculations
    # to get some real information out - beware, this will actually run
    # programs...

    def get_scaled_merged_reflections(self):
        """Return a reflection file (or files) containing all of the
        merged reflections for this XCrystal."""

        return self._get_scaler().get_scaled_merged_reflections()

    def get_scaled_reflections(self, format):
        """Get specific reflection files."""

        return self._get_scaler().get_scaled_reflections(format)

    def get_cell(self):
        """Get the final unit cell from scaling."""
        return self._get_scaler().get_scaler_cell()

    def get_likely_spacegroups(self):
        """Get the list if likely spacegroups from the scaling."""
        return self._get_scaler().get_scaler_likely_spacegroups()

    def get_statistics(self):
        """Get the scaling statistics for this sample."""
        return self._get_scaler().get_scaler_statistics()

    def _get_scaler(self):
        if self._scaler is None:

            # in here check if
            #
            # (1) self._scaled_merged_reflections is set and
            # (2) there is no sweep information
            #
            # if both of these are true then produce a null scaler
            # which will wrap this information

            from libtbx import Auto

            scale_dir = PhilIndex.params.xia2.settings.scale.directory
            if scale_dir is Auto:
                scale_dir = "scale"
            working_path = self._project.path.joinpath(self._name, scale_dir)
            working_path.mkdir(parents=True, exist_ok=True)

            self._scaler = Scaler(base_path=self._project.path)

            # put an inverse link in place... to support RD analysis
            # involved change to Scaler interface definition

            self._scaler.set_scaler_xcrystal(self)

            if self._anomalous:
                self._scaler.set_scaler_anomalous(True)

            # set up a sensible working directory
            self._scaler.set_working_directory(str(working_path))

            # set the reference reflection file, if we have one...
            if self._reference_reflection_file:
                self._scaler.set_scaler_reference_reflection_file(
                    self._reference_reflection_file
                )

            # and FreeR file
            if self._freer_file:
                self._scaler.set_scaler_freer_file(self._freer_file)

            # and spacegroup information
            if self._user_spacegroup:
                # compute the lattice and pointgroup from this...

                pointgroup = Syminfo.get_pointgroup(self._user_spacegroup)

                self._scaler.set_scaler_input_spacegroup(self._user_spacegroup)
                self._scaler.set_scaler_input_pointgroup(pointgroup)

            integraters = self._get_integraters()

            # then feed them to the scaler

            for i in integraters:
                self._scaler.add_scaler_integrater(i)

        return self._scaler

    def serialize(self):
        scaler = self._get_scaler()
        if scaler.get_scaler_finish_done():
            scaler.as_json(
                filename=os.path.join(scaler.get_working_directory(), "xia2.json")
            )
