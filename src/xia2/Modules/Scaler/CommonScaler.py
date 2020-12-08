# Bits the scalers have in common - inherit from me!


import logging
import math
import os
import time

import iotbx.merging_statistics
from cctbx.xray import scatterer
from cctbx.xray.structure import structure
from iotbx import mtz
from iotbx.reflection_file_reader import any_reflection_file
from iotbx.shelx import writer
from iotbx.shelx.hklf import miller_array_export_as_shelx_hklf
from xia2.Handlers.CIF import CIF, mmCIF
from xia2.Handlers.Files import FileHandler
from xia2.Handlers.Phil import PhilIndex
from xia2.Handlers.Streams import banner
from xia2.lib.bits import auto_logfiler, nifty_power_of_ten
from xia2.lib.SymmetryLib import clean_reindex_operator
from xia2.Modules import MtzUtils
from xia2.Modules.AnalyseMyIntensities import AnalyseMyIntensities
from xia2.Modules.CCP4InterRadiationDamageDetector import (
    CCP4InterRadiationDamageDetector,
)
from xia2.Modules.Scaler.rebatch import rebatch
from xia2.Schema.Interfaces.Scaler import Scaler

# new resolution limit code
from xia2.Wrappers.Dials.EstimateResolution import EstimateResolution
from xia2.XIA2Version import Version

logger = logging.getLogger("xia2.Modules.Scaler.CommonScaler")


class CommonScaler(Scaler):
    """Unified bits which the scalers have in common over the interface."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._sweep_handler = None
        self._scalr_twinning_score = None
        self._scalr_twinning_conclusion = None
        self._spacegroup_reindex_operator = None

    def _sort_together_data_ccp4(self):
        """Sort together in the right order (rebatching as we go) the sweeps
        we want to scale together."""

        max_batches = 0

        for epoch in self._sweep_handler.get_epochs():
            si = self._sweep_handler.get_sweep_information(epoch)
            sname = si.get_sweep_name()
            hklin = si.get_reflections()

            # limit the reflections - e.g. if we are re-running the scaling step
            # on just a subset of the integrated data

            limit_batch_range = None
            for sweep in PhilIndex.params.xia2.settings.sweep:
                if sweep.id == sname and sweep.range is not None:
                    limit_batch_range = sweep.range
                    break

            if limit_batch_range is not None:
                logger.debug(
                    "Limiting batch range for %s: %s", sname, limit_batch_range
                )
                start, end = limit_batch_range
                hklout = os.path.splitext(hklin)[0] + "_tmp.mtz"
                FileHandler.record_temporary_file(hklout)
                rb = self._factory.Pointless()
                rb.set_hklin(hklin)
                rb.set_hklout(hklout)
                rb.limit_batches(start, end)
                si.set_reflections(hklout)
                si.set_batches(limit_batch_range)

            # keep a count of the maximum number of batches in a block -
            # this will be used to make rebatch work below.

            hklin = si.get_reflections()

            batches = MtzUtils.batches_from_mtz(hklin)
            if 1 + max(batches) - min(batches) > max_batches:
                max_batches = max(batches) - min(batches) + 1

        logger.debug("Biggest sweep has %d batches", max_batches)
        max_batches = nifty_power_of_ten(max_batches)

        # then rebatch the files, to make sure that the batch numbers are
        # in the same order as the epochs of data collection.

        counter = 0

        for epoch in self._sweep_handler.get_epochs():
            si = self._sweep_handler.get_sweep_information(epoch)

            hklin = si.get_reflections()

            pname, xname, dname = si.get_project_info()
            sname = si.get_sweep_name()

            hklout = os.path.join(
                self.get_working_directory(),
                f"{pname}_{xname}_{dname}_{sname}_integrated.mtz",
            )

            first_batch = min(si.get_batches())
            si.set_batch_offset(counter * max_batches - first_batch + 1)

            new_batches = rebatch(
                hklin,
                hklout,
                first_batch=counter * max_batches + 1,
                pname=pname,
                xname=xname,
                dname=dname,
            )

            # update the "input information"

            si.set_reflections(hklout)
            si.set_batches(new_batches)

            # update the counter & recycle

            counter += 1

        s = self._factory.Sortmtz()

        hklout = os.path.join(
            self.get_working_directory(),
            f"{self._scalr_pname}_{self._scalr_xname}_sorted.mtz",
        )

        s.set_hklout(hklout)

        for epoch in self._sweep_handler.get_epochs():
            s.add_hklin(
                self._sweep_handler.get_sweep_information(epoch).get_reflections()
            )

        s.sort()

        # verify that the measurements are in the correct setting
        # choice for the spacegroup

        hklin = hklout
        hklout = hklin.replace("sorted.mtz", "temp.mtz")

        if not self.get_scaler_reference_reflection_file():

            if PhilIndex.params.xia2.settings.symmetry.program == "dials":
                p = self._factory.dials_symmetry()
            else:
                p = self._factory.Pointless()

            FileHandler.record_log_file(
                f"{self._scalr_pname} {self._scalr_xname} pointless",
                p.get_log_file(),
            )

            if len(self._sweep_handler.get_epochs()) > 1:
                p.set_hklin(hklin)
            else:
                # permit the use of pointless preparation...
                epoch = self._sweep_handler.get_epochs()[0]
                p.set_hklin(
                    self._prepare_pointless_hklin(
                        hklin,
                        self._sweep_handler.get_sweep_information(epoch)
                        .get_integrater()
                        .get_phi_width(),
                    )
                )

            if self._scalr_input_spacegroup:
                logger.debug(
                    "Assigning user input spacegroup: %s", self._scalr_input_spacegroup
                )

                p.decide_spacegroup()
                spacegroup = p.get_spacegroup()
                reindex_operator = p.get_spacegroup_reindex_operator()

                logger.debug(
                    "Pointless thought %s (reindex as %s)", spacegroup, reindex_operator
                )

                spacegroup = self._scalr_input_spacegroup
                reindex_operator = "h,k,l"
                self._spacegroup_reindex_operator = reindex_operator

            else:
                p.decide_spacegroup()
                spacegroup = p.get_spacegroup()
                reindex_operator = p.get_spacegroup_reindex_operator()
                self._spacegroup_reindex_operator = clean_reindex_operator(
                    reindex_operator
                )
                logger.debug(
                    "Pointless thought %s (reindex as %s)", spacegroup, reindex_operator
                )

            if self._scalr_input_spacegroup:
                self._scalr_likely_spacegroups = [self._scalr_input_spacegroup]
            else:
                self._scalr_likely_spacegroups = p.get_likely_spacegroups()

            logger.info("Likely spacegroups:")
            for spag in self._scalr_likely_spacegroups:
                logger.info(str(spag))

            logger.info(
                "Reindexing to first spacegroup setting: %s (%s)",
                spacegroup,
                clean_reindex_operator(reindex_operator),
            )

        else:
            spacegroup = MtzUtils.space_group_name_from_mtz(
                self.get_scaler_reference_reflection_file()
            )
            reindex_operator = "h,k,l"

            self._scalr_likely_spacegroups = [spacegroup]

            logger.debug("Assigning spacegroup %s from reference", spacegroup)

        # then run reindex to set the correct spacegroup

        ri = self._factory.Reindex()
        ri.set_hklin(hklin)
        ri.set_hklout(hklout)
        ri.set_spacegroup(spacegroup)
        ri.set_operator(reindex_operator)
        ri.reindex()

        FileHandler.record_temporary_file(hklout)

        # then resort the reflections (one last time!)

        s = self._factory.Sortmtz()

        temp = hklin
        hklin = hklout
        hklout = temp

        s.add_hklin(hklin)
        s.set_hklout(hklout)

        s.sort()

        # done preparing!

        self._prepared_reflections = s.get_hklout()

    def _sort_together_data_xds(self):

        if len(self._sweep_information) == 1:
            return self._sort_together_data_xds_one_sweep()

        max_batches = 0

        for epoch in self._sweep_information:
            hklin = self._sweep_information[epoch]["scaled_reflections"]

            if self._sweep_information[epoch]["batches"] == [0, 0]:

                logger.info("Getting batches from %s", hklin)
                batches = MtzUtils.batches_from_mtz(hklin)
                self._sweep_information[epoch]["batches"] = [min(batches), max(batches)]
                logger.info("=> %d to %d", min(batches), max(batches))

            batches = self._sweep_information[epoch]["batches"]
            if 1 + max(batches) - min(batches) > max_batches:
                max_batches = max(batches) - min(batches) + 1

        logger.debug("Biggest sweep has %d batches", max_batches)
        max_batches = nifty_power_of_ten(max_batches)

        epochs = sorted(self._sweep_information.keys())

        counter = 0

        for epoch in epochs:
            hklin = self._sweep_information[epoch]["scaled_reflections"]
            pname = self._sweep_information[epoch]["pname"]
            xname = self._sweep_information[epoch]["xname"]
            dname = self._sweep_information[epoch]["dname"]

            hklout = os.path.join(
                self.get_working_directory(),
                "%s_%s_%s_%d.mtz" % (pname, xname, dname, counter),
            )

            # we will want to delete this one exit
            FileHandler.record_temporary_file(hklout)

            # record this for future reference - will be needed in the
            # radiation damage analysis...

            # hack - reset this as it gets in a muddle...
            intgr = self._sweep_information[epoch]["integrater"]
            self._sweep_information[epoch]["batches"] = intgr.get_integrater_batches()

            first_batch = min(self._sweep_information[epoch]["batches"])
            offset = counter * max_batches - first_batch + 1
            self._sweep_information[epoch]["batch_offset"] = offset

            new_batches = rebatch(
                hklin, hklout, add_batch=offset, pname=pname, xname=xname, dname=dname
            )

            # update the "input information"

            self._sweep_information[epoch]["hklin"] = hklout
            self._sweep_information[epoch]["batches"] = new_batches

            # update the counter & recycle

            counter += 1

        s = self._factory.Sortmtz()

        hklout = os.path.join(
            self.get_working_directory(),
            f"{self._scalr_pname}_{self._scalr_xname}_sorted.mtz",
        )

        s.set_hklout(hklout)

        for epoch in epochs:
            s.add_hklin(self._sweep_information[epoch]["hklin"])

        s.sort(vrset=-99999999.0)

        self._prepared_reflections = hklout

        if self.get_scaler_reference_reflection_file():
            spacegroups = [
                MtzUtils.space_group_name_from_mtz(
                    self.get_scaler_reference_reflection_file()
                )
            ]
            reindex_operator = "h,k,l"

        else:
            pointless = self._factory.Pointless()
            pointless.set_hklin(hklout)
            pointless.decide_spacegroup()

            FileHandler.record_log_file(
                f"{self._scalr_pname} {self._scalr_xname} pointless",
                pointless.get_log_file(),
            )

            spacegroups = pointless.get_likely_spacegroups()
            reindex_operator = pointless.get_spacegroup_reindex_operator()

            if self._scalr_input_spacegroup:
                logger.debug(
                    "Assigning user input spacegroup: %s", self._scalr_input_spacegroup
                )
                spacegroups = [self._scalr_input_spacegroup]
                reindex_operator = "h,k,l"

        self._scalr_likely_spacegroups = spacegroups
        spacegroup = self._scalr_likely_spacegroups[0]

        self._scalr_reindex_operator = reindex_operator

        logger.info("Likely spacegroups:")
        for spag in self._scalr_likely_spacegroups:
            logger.info(str(spag))

        logger.info(
            "Reindexing to first spacegroup setting: %s (%s)",
            spacegroup,
            clean_reindex_operator(reindex_operator),
        )

        hklin = self._prepared_reflections
        hklout = os.path.join(
            self.get_working_directory(),
            f"{self._scalr_pname}_{self._scalr_xname}_reindex.mtz",
        )

        FileHandler.record_temporary_file(hklout)

        ri = self._factory.Reindex()
        ri.set_hklin(hklin)
        ri.set_hklout(hklout)
        ri.set_spacegroup(spacegroup)
        ri.set_operator(reindex_operator)
        ri.reindex()

        hklin = hklout
        hklout = os.path.join(
            self.get_working_directory(),
            f"{self._scalr_pname}_{self._scalr_xname}_sorted.mtz",
        )

        s = self._factory.Sortmtz()
        s.set_hklin(hklin)
        s.set_hklout(hklout)

        s.sort(vrset=-99999999.0)

        self._prepared_reflections = hklout

        logger.debug(
            "Updating unit cell to %.2f %.2f %.2f %.2f %.2f %.2f" % tuple(ri.get_cell())
        )
        self._scalr_cell = tuple(ri.get_cell())

    def _sort_together_data_xds_one_sweep(self):

        assert len(self._sweep_information) == 1

        epoch = list(self._sweep_information)[0]
        hklin = self._sweep_information[epoch]["scaled_reflections"]

        if self.get_scaler_reference_reflection_file():
            spacegroups = [
                MtzUtils.space_group_name_from_mtz(
                    self.get_scaler_reference_reflection_file()
                )
            ]
            reindex_operator = "h,k,l"

        elif self._scalr_input_spacegroup:
            logger.debug(
                "Assigning user input spacegroup: %s", self._scalr_input_spacegroup
            )
            spacegroups = [self._scalr_input_spacegroup]
            reindex_operator = "h,k,l"

        else:
            pointless = self._factory.Pointless()
            pointless.set_hklin(hklin)
            pointless.decide_spacegroup()

            FileHandler.record_log_file(
                f"{self._scalr_pname} {self._scalr_xname} pointless",
                pointless.get_log_file(),
            )

            spacegroups = pointless.get_likely_spacegroups()
            reindex_operator = pointless.get_spacegroup_reindex_operator()

        self._scalr_likely_spacegroups = spacegroups
        spacegroup = self._scalr_likely_spacegroups[0]

        self._scalr_reindex_operator = clean_reindex_operator(reindex_operator)

        logger.info("Likely spacegroups:")
        for spag in self._scalr_likely_spacegroups:
            logger.info(str(spag))

        logger.info(
            "Reindexing to first spacegroup setting: %s (%s)",
            spacegroup,
            clean_reindex_operator(reindex_operator),
        )

        hklout = os.path.join(
            self.get_working_directory(),
            f"{self._scalr_pname}_{self._scalr_xname}_reindex.mtz",
        )

        FileHandler.record_temporary_file(hklout)

        if reindex_operator == "[h,k,l]":
            # just assign spacegroup

            from cctbx import sgtbx

            s = sgtbx.space_group(sgtbx.space_group_symbols(str(spacegroup)).hall())

            m = mtz.object(hklin)
            m.set_space_group(s).write(hklout)
            self._scalr_cell = m.crystals()[-1].unit_cell().parameters()
            logger.debug(
                "Updating unit cell to %.2f %.2f %.2f %.2f %.2f %.2f"
                % tuple(self._scalr_cell)
            )
            del m
            del s

        else:
            ri = self._factory.Reindex()
            ri.set_hklin(hklin)
            ri.set_hklout(hklout)
            ri.set_spacegroup(spacegroup)
            ri.set_operator(reindex_operator)
            ri.reindex()

            logger.debug(
                "Updating unit cell to %.2f %.2f %.2f %.2f %.2f %.2f"
                % tuple(ri.get_cell())
            )
            self._scalr_cell = tuple(ri.get_cell())

        hklin = hklout
        hklout = os.path.join(
            self.get_working_directory(),
            f"{self._scalr_pname}_{self._scalr_xname}_sorted.mtz",
        )

        s = self._factory.Sortmtz()
        s.set_hklin(hklin)
        s.set_hklout(hklout)

        s.sort(vrset=-99999999.0)

        self._prepared_reflections = hklout

    def _scale_finish(self):

        if not self._scalr_scaled_refl_files:
            raise RuntimeError("no reflection files stored")

        if not PhilIndex.params.xia2.settings.small_molecule:
            self._scale_finish_chunk_3_truncate()

        self._scale_finish_chunk_4_mad_mangling()

        if PhilIndex.params.xia2.settings.small_molecule:
            self._scale_finish_chunk_5_finish_small_molecule()
            self._scale_finish_export_shelxt()

            return

        # finally add a FreeR column, and record the new merged reflection
        # file with the free column added.

        self._scale_finish_chunk_6_add_free_r()

        # next have a look for radiation damage... if more than one wavelength

        if len(list(self._scalr_scaled_refl_files)) > 1:
            self._scale_finish_chunk_8_raddam()

        # finally add xia2 version to mtz history
        from iotbx.reflection_file_reader import any_reflection_file

        mtz_files = [self._scalr_scaled_reflection_files["mtz"]]
        mtz_files.extend(self._scalr_scaled_reflection_files["mtz_unmerged"].values())
        for mtz_file in mtz_files:
            reader = any_reflection_file(mtz_file)
            mtz_object = reader.file_content()
            date_str = time.strftime("%d/%m/%Y at %H:%M:%S", time.gmtime())
            mtz_object.add_history(f"From {Version}, run on {date_str}")
            mtz_object.write(mtz_file)

    def _scale_finish_chunk_3_truncate(self):
        for wavelength in self._scalr_scaled_refl_files:
            hklin = self._scalr_scaled_refl_files[wavelength]

            truncate = self._factory.Truncate()
            truncate.set_hklin(hklin)

            if self.get_scaler_anomalous():
                truncate.set_anomalous(True)
            else:
                truncate.set_anomalous(False)

            FileHandler.record_log_file(
                "%s %s %s truncate"
                % (self._scalr_pname, self._scalr_xname, wavelength),
                truncate.get_log_file(),
            )

            hklout = os.path.join(
                self.get_working_directory(), "%s_truncated.mtz" % wavelength
            )

            truncate.set_hklout(hklout)
            truncate.truncate()

            xmlout = truncate.get_xmlout()
            if xmlout is not None:
                FileHandler.record_xml_file(
                    "%s %s %s truncate"
                    % (self._scalr_pname, self._scalr_xname, wavelength),
                    xmlout,
                )

            logger.debug(
                "%d absent reflections in %s removed",
                truncate.get_nabsent(),
                wavelength,
            )

            b_factor = truncate.get_b_factor()
            if math.isnan(b_factor):
                b_factor = None

            # record the b factor somewhere (hopefully) useful...

            self._scalr_statistics[(self._scalr_pname, self._scalr_xname, wavelength)][
                "Wilson B factor"
            ] = [b_factor]

            # and record the reflection file..
            self._scalr_scaled_refl_files[wavelength] = hklout

    def _scale_finish_chunk_4_mad_mangling(self):
        if len(self._scalr_scaled_refl_files) > 1:
            reflection_files = {}

            for wavelength in self._scalr_scaled_refl_files:
                cad = self._factory.Cad()
                cad.add_hklin(self._scalr_scaled_refl_files[wavelength])
                cad.set_hklout(
                    os.path.join(
                        self.get_working_directory(), "cad-tmp-%s.mtz" % wavelength
                    )
                )
                cad.set_new_suffix(wavelength)
                cad.update()

                reflection_files[wavelength] = cad.get_hklout()
                FileHandler.record_temporary_file(cad.get_hklout())

            # now merge the reflection files together...
            hklout = os.path.join(
                self.get_working_directory(),
                f"{self._scalr_pname}_{self._scalr_xname}_merged.mtz",
            )
            FileHandler.record_temporary_file(hklout)

            logger.debug("Merging all data sets to %s", hklout)

            cad = self._factory.Cad()
            for rf in reflection_files.values():
                cad.add_hklin(rf)
            cad.set_hklout(hklout)
            cad.merge()

            self._scalr_scaled_reflection_files["mtz_merged"] = hklout

        else:

            self._scalr_scaled_reflection_files[
                "mtz_merged"
            ] = self._scalr_scaled_refl_files[list(self._scalr_scaled_refl_files)[0]]

    def _scale_finish_chunk_5_finish_small_molecule(self):
        # keep 'mtz' and remove 'mtz_merged' from the dictionary for
        # consistency with non-small-molecule workflow
        self._scalr_scaled_reflection_files[
            "mtz"
        ] = self._scalr_scaled_reflection_files["mtz_merged"]
        del self._scalr_scaled_reflection_files["mtz_merged"]

        FileHandler.record_data_file(self._scalr_scaled_reflection_files["mtz"])

    def _scale_finish_export_shelxt(self):
        """Read hklin (unmerged reflection file) and generate SHELXT input file
        and HKL file"""

        for wavelength_name in self._scalr_scaled_refl_files:
            prefix = wavelength_name
            if len(list(self._scalr_scaled_refl_files)) == 1:
                prefix = "shelxt"
            prefixpath = os.path.join(self.get_working_directory(), prefix)

            mtz_unmerged = self._scalr_scaled_reflection_files["mtz_unmerged"][
                wavelength_name
            ]
            reader = any_reflection_file(mtz_unmerged)
            intensities = [
                ma
                for ma in reader.as_miller_arrays(merge_equivalents=False)
                if ma.info().labels == ["I", "SIGI"]
            ][0]

            indices = reader.file_content().extract_original_index_miller_indices()
            intensities = intensities.customized_copy(
                indices=indices, info=intensities.info()
            )

            with open("%s.hkl" % prefixpath, "w") as hkl_file_handle:
                # limit values to 4 digits (before decimal point), as this is what shelxt
                # writes in its output files, and shelxl seems to read. ShelXL apparently
                # does not read values >9999 properly
                miller_array_export_as_shelx_hklf(
                    intensities,
                    hkl_file_handle,
                    scale_range=(-9999.0, 9999.0),
                    normalise_if_format_overflow=True,
                )

            crystal_symm = intensities.crystal_symmetry()

            unit_cell_dims = self._scalr_cell
            unit_cell_esds = self._scalr_cell_esd

            cb_op = crystal_symm.change_of_basis_op_to_reference_setting()

            if cb_op.c().r().as_hkl() == "h,k,l":
                print("Change of basis to reference setting: %s" % cb_op)
                crystal_symm = crystal_symm.change_basis(cb_op)
                if str(cb_op) != "a,b,c":
                    unit_cell_dims = None
                    unit_cell_esds = None
                    # Would need to apply operation to cell errors, too. Need a test case for this

            # crystal_symm.show_summary()
            xray_structure = structure(crystal_symmetry=crystal_symm)

            for element in "CNOH":
                xray_structure.add_scatterer(scatterer(label=element, occupancy=1))

            wavelength = self._scalr_xcrystal.get_xwavelength(
                wavelength_name
            ).get_wavelength()

            with open("%s.ins" % prefixpath, "w") as insfile:
                insfile.write(
                    "".join(
                        writer.generator(
                            xray_structure,
                            wavelength=wavelength,
                            full_matrix_least_squares_cycles=0,
                            title=prefix,
                            unit_cell_dims=unit_cell_dims,
                            unit_cell_esds=unit_cell_esds,
                        )
                    )
                )

            FileHandler.record_data_file("%s.ins" % prefixpath)
            FileHandler.record_data_file("%s.hkl" % prefixpath)

    def _scale_finish_chunk_6_add_free_r(self):
        hklout = os.path.join(
            self.get_working_directory(),
            f"{self._scalr_pname}_{self._scalr_xname}_free_temp.mtz",
        )

        FileHandler.record_temporary_file(hklout)

        scale_params = PhilIndex.params.xia2.settings.scale
        if self.get_scaler_freer_file():
            # e.g. via .xinfo file

            freein = self.get_scaler_freer_file()

            logger.debug("Copying FreeR_flag from %s", freein)

            c = self._factory.Cad()
            c.set_freein(freein)
            c.add_hklin(self._scalr_scaled_reflection_files["mtz_merged"])
            c.set_hklout(hklout)
            c.copyfree()

        elif scale_params.freer_file is not None:
            # e.g. via -freer_file command line argument

            freein = scale_params.freer_file

            logger.debug("Copying FreeR_flag from %s", freein)

            c = self._factory.Cad()
            c.set_freein(freein)
            c.add_hklin(self._scalr_scaled_reflection_files["mtz_merged"])
            c.set_hklout(hklout)
            c.copyfree()

        else:

            if scale_params.free_total:
                ntot = scale_params.free_total

                # need to get a fraction, so...
                nref = MtzUtils.nref_from_mtz(
                    self._scalr_scaled_reflection_files["mtz_merged"]
                )
                free_fraction = float(ntot) / float(nref)
            else:
                free_fraction = scale_params.free_fraction

            f = self._factory.Freerflag()
            f.set_free_fraction(free_fraction)
            f.set_hklin(self._scalr_scaled_reflection_files["mtz_merged"])
            f.set_hklout(hklout)
            f.add_free_flag()

        # then check that this FreeR set is complete

        hklin = hklout
        hklout = os.path.join(
            self.get_working_directory(),
            f"{self._scalr_pname}_{self._scalr_xname}_free.mtz",
        )

        # default fraction of 0.05
        free_fraction = 0.05

        if scale_params.free_fraction:
            free_fraction = scale_params.free_fraction
        elif scale_params.free_total:
            ntot = scale_params.free_total()

            # need to get a fraction, so...
            nref = MtzUtils.nref_from_mtz(hklin)
            free_fraction = float(ntot) / float(nref)

        f = self._factory.Freerflag()
        f.set_free_fraction(free_fraction)
        f.set_hklin(hklin)
        f.set_hklout(hklout)
        f.complete_free_flag()

        # remove 'mtz_merged' from the dictionary - this is made
        # redundant by the merged free...
        del self._scalr_scaled_reflection_files["mtz_merged"]

        # changed from mtz_merged_free to plain ol' mtz
        self._scalr_scaled_reflection_files["mtz"] = hklout

        # record this for future reference
        FileHandler.record_data_file(hklout)

    def _scale_finish_chunk_8_raddam(self):
        crd = CCP4InterRadiationDamageDetector()

        crd.set_working_directory(self.get_working_directory())

        crd.set_hklin(self._scalr_scaled_reflection_files["mtz"])

        if self.get_scaler_anomalous():
            crd.set_anomalous(True)

        hklout = os.path.join(self.get_working_directory(), "temp.mtz")
        FileHandler.record_temporary_file(hklout)

        crd.set_hklout(hklout)

        status = crd.detect()

        if status:
            logger.info("")
            logger.notice(banner("Local Scaling %s" % self._scalr_xname))
            for s in status:
                logger.info("%s %s" % s)
            logger.info(banner(""))
        else:
            logger.debug("Local scaling failed")

    def _estimate_resolution_limit(
        self, hklin, batch_range=None, reflections=None, experiments=None
    ):
        params = PhilIndex.params.xia2.settings.resolution
        m = EstimateResolution()
        m.set_working_directory(self.get_working_directory())

        auto_logfiler(m)
        if hklin:
            m.set_hklin(hklin)
        else:
            assert reflections and experiments
            m.set_reflections(reflections)
            m.set_experiments(experiments)
        m.set_limit_rmerge(params.rmerge)
        m.set_limit_completeness(params.completeness)
        m.set_limit_cc_half(params.cc_half)
        m.set_cc_half_fit(params.cc_half_fit)
        m.set_cc_half_significance_level(params.cc_half_significance_level)
        m.set_limit_isigma(params.isigma)
        m.set_limit_misigma(params.misigma)
        if PhilIndex.params.xia2.settings.small_molecule:
            m.set_nbins(20)
        if batch_range is not None:
            start, end = batch_range
            m.set_batch_range(start, end)
        m.run()

        resolution_limits = []
        reasoning = []

        if params.completeness is not None:
            r_comp = m.get_resolution_completeness()
            resolution_limits.append(r_comp)
            reasoning.append("completeness > %s" % params.completeness)

        if params.cc_half is not None:
            r_cc_half = m.get_resolution_cc_half()
            resolution_limits.append(r_cc_half)
            reasoning.append("cc_half > %s" % params.cc_half)

        if params.rmerge is not None:
            r_rm = m.get_resolution_rmerge()
            resolution_limits.append(r_rm)
            reasoning.append("rmerge > %s" % params.rmerge)

        if params.isigma is not None:
            r_uis = m.get_resolution_isigma()
            resolution_limits.append(r_uis)
            reasoning.append("unmerged <I/sigI> > %s" % params.isigma)

        if params.misigma is not None:
            r_mis = m.get_resolution_misigma()
            resolution_limits.append(r_mis)
            reasoning.append("merged <I/sigI> > %s" % params.misigma)

        if any(resolution_limits):
            resolution = max(r for r in resolution_limits if r is not None)
            reasoning = [
                reason
                for limit, reason in zip(resolution_limits, reasoning)
                if limit is not None and limit >= resolution
            ]
            reasoning = ", ".join(reasoning)
        else:
            resolution = 0.0
            reasoning = None

        return resolution, reasoning

    def _compute_scaler_statistics(
        self, scaled_unmerged_mtz, selected_band=None, wave=None
    ):
        """ selected_band = (d_min, d_max) with None for automatic determination. """
        # mapping of expected dictionary names to iotbx.merging_statistics attributes
        key_to_var = {
            "I/sigma": "i_over_sigma_mean",
            "Completeness": "completeness",
            "Low resolution limit": "d_max",
            "Multiplicity": "mean_redundancy",
            "Rmerge(I)": "r_merge",
            #'Wilson B factor':,
            "Rmeas(I)": "r_meas",
            "High resolution limit": "d_min",
            "Total observations": "n_obs",
            "Rpim(I)": "r_pim",
            "CC half": "cc_one_half",
            "Total unique": "n_uniq",
        }

        anom_key_to_var = {
            "Rmerge(I+/-)": "r_merge",
            "Rpim(I+/-)": "r_pim",
            "Rmeas(I+/-)": "r_meas",
            "Anomalous completeness": "anom_completeness",
            "Anomalous correlation": "anom_half_corr",
            "Anomalous multiplicity": "mean_redundancy",
        }

        stats = {}

        # don't call self.get_scaler_likely_spacegroups() since that calls
        # self.scale() which introduced a subtle bug
        from cctbx import sgtbx

        sg = sgtbx.space_group_info(str(self._scalr_likely_spacegroups[0])).group()

        log_directory = self._base_path / "LogFiles"
        log_directory.mkdir(parents=True, exist_ok=True)
        merging_stats_file = log_directory.joinpath(
            "%s_%s%s_merging-statistics.txt"
            % (
                self._scalr_pname,
                self._scalr_xname,
                "" if wave is None else "_%s" % wave,
            )
        )
        merging_stats_json = log_directory.joinpath(
            "%s_%s%s_merging-statistics.json"
            % (
                self._scalr_pname,
                self._scalr_xname,
                "" if wave is None else "_%s" % wave,
            )
        )

        result, select_result, anom_result, select_anom_result = None, None, None, None
        n_bins = PhilIndex.params.xia2.settings.merging_statistics.n_bins

        while result is None:
            try:

                result = self._iotbx_merging_statistics(
                    scaled_unmerged_mtz, anomalous=False, n_bins=n_bins
                )
                result.as_json(file_name=str(merging_stats_json))
                with open(str(merging_stats_file), "w") as fh:
                    result.show(out=fh)

                four_column_output = selected_band and any(selected_band)
                if four_column_output:
                    select_result = self._iotbx_merging_statistics(
                        scaled_unmerged_mtz,
                        anomalous=False,
                        d_min=selected_band[0],
                        d_max=selected_band[1],
                        n_bins=n_bins,
                    )

                if sg.is_centric():
                    anom_result = None
                    anom_key_to_var = {}
                else:
                    anom_result = self._iotbx_merging_statistics(
                        scaled_unmerged_mtz, anomalous=True, n_bins=n_bins
                    )
                    anom_probability_plot = (
                        anom_result.overall.anom_probability_plot_expected_delta
                    )
                    if anom_probability_plot is not None:
                        stats["Anomalous slope"] = [anom_probability_plot.slope]
                    stats["dF/F"] = [anom_result.overall.anom_signal]
                    stats["dI/s(dI)"] = [
                        anom_result.overall.delta_i_mean_over_sig_delta_i_mean
                    ]
                    if four_column_output:
                        select_anom_result = self._iotbx_merging_statistics(
                            scaled_unmerged_mtz,
                            anomalous=True,
                            d_min=selected_band[0],
                            d_max=selected_band[1],
                            n_bins=n_bins,
                        )

            except iotbx.merging_statistics.StatisticsError:
                # Too few reflections for too many bins. Reduce number of bins and try again.
                result = None
                n_bins = n_bins - 3
                if n_bins > 5:
                    continue
                else:
                    raise

        for d, r, s in (
            (key_to_var, result, select_result),
            (anom_key_to_var, anom_result, select_anom_result),
        ):
            for k, v in d.items():
                if four_column_output:
                    values = (
                        getattr(s.overall, v),
                        getattr(s.bins[0], v),
                        getattr(s.bins[-1], v),
                        getattr(r.overall, v),
                    )
                else:
                    values = (
                        getattr(r.overall, v),
                        getattr(r.bins[0], v),
                        getattr(r.bins[-1], v),
                    )
                if "completeness" in v:
                    values = [v_ * 100 for v_ in values]
                if values[0] is not None:
                    stats[k] = values

        return stats

    def _iotbx_merging_statistics(
        self, scaled_unmerged_mtz, anomalous=False, d_min=None, d_max=None, n_bins=None
    ):
        params = PhilIndex.params.xia2.settings.merging_statistics
        i_obs = iotbx.merging_statistics.select_data(
            scaled_unmerged_mtz, data_labels=None
        )
        i_obs = i_obs.customized_copy(anomalous_flag=True, info=i_obs.info())
        return iotbx.merging_statistics.dataset_statistics(
            i_obs=i_obs,
            d_min=d_min,
            d_max=d_max,
            n_bins=n_bins or params.n_bins,
            anomalous=anomalous,
            use_internal_variance=params.use_internal_variance,
            eliminate_sys_absent=params.eliminate_sys_absent,
            assert_is_not_unique_set_under_symmetry=False,
        )

    def _update_scaled_unit_cell(self):
        params = PhilIndex.params
        fast_mode = params.dials.fast_mode
        if (
            params.xia2.settings.integrater == "dials"
            and not fast_mode
            and params.xia2.settings.scale.two_theta_refine
        ):
            from xia2.Wrappers.Dials.TwoThetaRefine import TwoThetaRefine
            from xia2.lib.bits import auto_logfiler

            logger.notice(banner("Unit cell refinement"))

            # Collect a list of all sweeps, grouped by project, crystal, wavelength
            groups = {}
            self._scalr_cell_dict = {}
            tt_refine_experiments = []
            tt_refine_reflections = []
            tt_refine_reindex_ops = []
            for epoch in self._sweep_handler.get_epochs():
                si = self._sweep_handler.get_sweep_information(epoch)
                pi = "_".join(si.get_project_info())
                intgr = si.get_integrater()
                groups[pi] = groups.get(pi, []) + [
                    (
                        intgr.get_integrated_experiments(),
                        intgr.get_integrated_reflections(),
                        intgr.get_integrater_reindex_operator(),
                    )
                ]

            # Two theta refine the unit cell for each group
            p4p_file = os.path.join(
                self.get_working_directory(),
                f"{self._scalr_pname}_{self._scalr_xname}.p4p",
            )
            for pi in groups:
                tt_grouprefiner = TwoThetaRefine()
                tt_grouprefiner.set_working_directory(self.get_working_directory())
                auto_logfiler(tt_grouprefiner)
                args = list(zip(*groups[pi]))
                tt_grouprefiner.set_experiments(args[0])
                tt_grouprefiner.set_reflection_files(args[1])
                tt_grouprefiner.set_output_p4p(p4p_file)
                tt_refine_experiments.extend(args[0])
                tt_refine_reflections.extend(args[1])
                tt_refine_reindex_ops.extend(args[2])
                reindex_ops = args[2]
                from cctbx.sgtbx import change_of_basis_op as cb_op

                if self._spacegroup_reindex_operator is not None:
                    reindex_ops = [
                        (
                            cb_op(str(self._spacegroup_reindex_operator))
                            * cb_op(str(op))
                        ).as_hkl()
                        if op is not None
                        else self._spacegroup_reindex_operator
                        for op in reindex_ops
                    ]
                tt_grouprefiner.set_reindex_operators(reindex_ops)
                tt_grouprefiner.run()
                logger.info(
                    "%s: %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f"
                    % tuple(
                        ["".join(pi.split("_")[2:])]
                        + list(tt_grouprefiner.get_unit_cell())
                    )
                )
                self._scalr_cell_dict[pi] = (
                    tt_grouprefiner.get_unit_cell(),
                    tt_grouprefiner.get_unit_cell_esd(),
                    tt_grouprefiner.import_cif(),
                    tt_grouprefiner.import_mmcif(),
                )
                if len(groups) > 1:
                    cif_in = tt_grouprefiner.import_cif()
                    cif_out = CIF.get_block(pi)
                    for key in sorted(cif_in.keys()):
                        cif_out[key] = cif_in[key]
                    mmcif_in = tt_grouprefiner.import_mmcif()
                    mmcif_out = mmCIF.get_block(pi)
                    for key in sorted(mmcif_in.keys()):
                        mmcif_out[key] = mmcif_in[key]

            # Two theta refine everything together
            if len(groups) > 1:
                tt_refiner = TwoThetaRefine()
                tt_refiner.set_working_directory(self.get_working_directory())
                tt_refiner.set_output_p4p(p4p_file)
                auto_logfiler(tt_refiner)
                tt_refiner.set_experiments(tt_refine_experiments)
                tt_refiner.set_reflection_files(tt_refine_reflections)
                if self._spacegroup_reindex_operator is not None:
                    reindex_ops = [
                        (
                            cb_op(str(self._spacegroup_reindex_operator))
                            * cb_op(str(op))
                        ).as_hkl()
                        if op is not None
                        else self._spacegroup_reindex_operator
                        for op in tt_refine_reindex_ops
                    ]
                else:
                    reindex_ops = tt_refine_reindex_ops
                tt_refiner.set_reindex_operators(reindex_ops)
                tt_refiner.run()
                self._scalr_cell = tt_refiner.get_unit_cell()
                logger.info(
                    "Overall: %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f"
                    % tt_refiner.get_unit_cell()
                )
                self._scalr_cell_esd = tt_refiner.get_unit_cell_esd()
                cif_in = tt_refiner.import_cif()
                mmcif_in = tt_refiner.import_mmcif()
            else:
                self._scalr_cell, self._scalr_cell_esd, cif_in, mmcif_in = list(
                    self._scalr_cell_dict.values()
                )[0]
            if params.xia2.settings.small_molecule:
                FileHandler.record_data_file(p4p_file)

            import dials.util.version

            cif_out = CIF.get_block("xia2")
            mmcif_out = mmCIF.get_block("xia2")
            cif_out["_computing_cell_refinement"] = mmcif_out[
                "_computing.cell_refinement"
            ] = ("DIALS 2theta refinement, %s" % dials.util.version.dials_version())
            for key in sorted(cif_in.keys()):
                cif_out[key] = cif_in[key]
            for key in sorted(mmcif_in.keys()):
                mmcif_out[key] = mmcif_in[key]

            logger.debug("Unit cell obtained by two-theta refinement")

        else:
            ami = AnalyseMyIntensities()
            ami.set_working_directory(self.get_working_directory())

            average_unit_cell, ignore_sg = ami.compute_average_cell(
                list(self._scalr_scaled_refl_files.values())
            )

            logger.debug("Computed average unit cell (will use in all files)")
            self._scalr_cell = average_unit_cell
            self._scalr_cell_esd = None

            # Write average unit cell to .cif
            cif_out = CIF.get_block("xia2")
            cif_out["_computing_cell_refinement"] = "AIMLESS averaged unit cell"
            for cell, cifname in zip(
                self._scalr_cell,
                [
                    "length_a",
                    "length_b",
                    "length_c",
                    "angle_alpha",
                    "angle_beta",
                    "angle_gamma",
                ],
            ):
                cif_out["_cell_%s" % cifname] = cell

        logger.debug("%7.3f %7.3f %7.3f %7.3f %7.3f %7.3f" % self._scalr_cell)

    def unify_setting(self):
        """Unify the setting for the sweeps."""
        # Currently implemented for CCP4ScalerA and DialsScaler
        from scitbx.matrix import sqr

        reference_U = None
        i3 = sqr((1, 0, 0, 0, 1, 0, 0, 0, 1))

        for epoch in self._sweep_handler.get_epochs():
            si = self._sweep_handler.get_sweep_information(epoch)
            intgr = si.get_integrater()
            fixed = sqr(intgr.get_goniometer().get_fixed_rotation())
            # delegate UB lattice symmetry calculation to individual Scalers.
            u, b, s = self.get_UBlattsymm_from_sweep_info(si)
            U = fixed.inverse() * sqr(u).transpose()
            B = sqr(b)

            if reference_U is None:
                reference_U = U
                continue

            results = []
            for op in s.all_ops():
                R = B * sqr(op.r().as_double()).transpose() * B.inverse()
                nearly_i3 = (U * R).inverse() * reference_U
                score = sum(abs(_n - _i) for (_n, _i) in zip(nearly_i3, i3))
                results.append((score, op.r().as_hkl(), op))

            results.sort()
            best = results[0]
            logger.debug("Best reindex: %s %.3f", best[1], best[0])
            reindex_op = best[2].r().inverse().as_hkl()
            # delegate reindexing to individual Scalers.
            self.apply_reindex_operator_to_sweep_info(
                si, reindex_op, reason="unifying [U] setting"
            )
            # recalculate to verify
            u, _, __ = self.get_UBlattsymm_from_sweep_info(si)
            U = fixed.inverse() * sqr(u).transpose()
            logger.debug("New reindex: %s", U.inverse() * reference_U)

            # FIXME I should probably raise an exception at this stage if this
            # is not about I3...

    def brehm_diederichs_reindexing(self):
        """Run brehm diederichs reindexing algorithm."""
        # Currently implemented for CCP4ScalerA and DialsScaler
        brehm_diederichs_files_in = []

        for epoch in self._sweep_handler.get_epochs():
            si = self._sweep_handler.get_sweep_information(epoch)
            brehm_diederichs_files_in.append(self.get_mtz_data_from_sweep_info(si))

        # now run cctbx.brehm_diederichs to figure out the indexing hand for
        # each sweep
        from xia2.Wrappers.Cctbx.BrehmDiederichs import BrehmDiederichs

        brehm_diederichs = BrehmDiederichs()
        brehm_diederichs.set_working_directory(self.get_working_directory())
        auto_logfiler(brehm_diederichs)
        brehm_diederichs.set_input_filenames(brehm_diederichs_files_in)
        # 1 or 3? 1 seems to work better?
        brehm_diederichs.set_asymmetric(1)
        brehm_diederichs.run()
        reindexing_dict = brehm_diederichs.get_reindexing_dict()

        for i, epoch in enumerate(self._sweep_handler.get_epochs()):
            si = self._sweep_handler.get_sweep_information(epoch)
            hklin = brehm_diederichs_files_in[i]
            reindex_op = reindexing_dict.get(os.path.abspath(hklin))
            assert reindex_op is not None
            if reindex_op != "h,k,l":
                self.apply_reindex_operator_to_sweep_info(
                    si, reindex_op, reason="match reference"
                )

    def assess_resolution_limits(
        self, hklin, user_resolution_limits, experiments=None, reflections=None
    ):
        """Assess resolution limits from hklin and sweep batch info"""
        # Implemented for DialsScaler and CCP4ScalerA
        highest_resolution = 100.0
        highest_suggested_resolution = None

        for epoch in self._sweep_handler.get_epochs():
            si = self._sweep_handler.get_sweep_information(epoch)
            _, __, dname = si.get_project_info()
            sname = si.get_sweep_name()
            intgr = si.get_integrater()
            start, end = si.get_batch_range()

            if (dname, sname) in self._scalr_resolution_limits:
                continue

            elif (dname, sname) in user_resolution_limits:
                limit = user_resolution_limits[(dname, sname)]
                self._scalr_resolution_limits[(dname, sname)] = (limit, None)
                if limit < highest_resolution:
                    highest_resolution = limit
                logger.info(
                    "Resolution limit for %s: %5.2f (user provided)", dname, limit
                )
                continue

            if hklin:
                limit, reasoning = self._estimate_resolution_limit(
                    hklin, batch_range=(start, end)
                )
            else:
                limit, reasoning = self._estimate_resolution_limit(
                    hklin=None,
                    batch_range=(start, end),
                    reflections=reflections,
                    experiments=experiments,
                )

            if PhilIndex.params.xia2.settings.resolution.keep_all_reflections:
                suggested = limit
                if (
                    highest_suggested_resolution is None
                    or limit < highest_suggested_resolution
                ):
                    highest_suggested_resolution = limit
                limit = intgr.get_detector().get_max_resolution(
                    intgr.get_beam_obj().get_s0()
                )
                self._scalr_resolution_limits[(dname, sname)] = (limit, suggested)
                logger.debug("keep_all_reflections set, using detector limits")
            logger.debug("Resolution for sweep %s: %.2f", sname, limit)

            if (dname, sname) not in self._scalr_resolution_limits:
                self._scalr_resolution_limits[(dname, sname)] = (limit, None)
                self.set_scaler_done(False)

            if limit < highest_resolution:
                highest_resolution = limit

            limit, suggested = self._scalr_resolution_limits[(dname, sname)]
            if suggested is None or limit == suggested:
                reasoning_str = ""
                if reasoning:
                    reasoning_str = " (%s)" % reasoning
                logger.info(
                    "Resolution for sweep %s/%s: %.2f%s",
                    dname,
                    sname,
                    limit,
                    reasoning_str,
                )
            else:
                logger.info(
                    "Resolution limit for %s/%s: %5.2f (%5.2f suggested)",
                    dname,
                    sname,
                    limit,
                    suggested,
                )

        if highest_suggested_resolution is not None and highest_resolution >= (
            highest_suggested_resolution - 0.004
        ):
            logger.debug(
                "Dropping resolution cut-off suggestion since it is"
                " essentially identical to the actual resolution limit."
            )
            highest_suggested_resolution = None
        self._scalr_highest_resolution = highest_resolution
        if highest_suggested_resolution is not None:
            logger.debug(
                "Suggested highest resolution is %5.2f (%5.2f suggested)",
                highest_resolution,
                highest_suggested_resolution,
            )
        else:
            logger.debug("Scaler highest resolution set to %5.2f", highest_resolution)

        return highest_suggested_resolution
