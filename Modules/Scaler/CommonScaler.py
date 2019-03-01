#!/usr/bin/env python
# CommonScaler.py
#   Copyright (C) 2011 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Bits the scalers have in common - inherit from me!

from __future__ import absolute_import, division, print_function

import os

from iotbx import mtz
from xia2.Handlers.Files import FileHandler
from xia2.Handlers.Phil import PhilIndex
from xia2.Handlers.Streams import Chatter, Debug
from xia2.Handlers.CIF import CIF, mmCIF
from xia2.lib.bits import nifty_power_of_ten
from xia2.Modules.AnalyseMyIntensities import AnalyseMyIntensities
from xia2.Modules import MtzUtils
from xia2.Modules.CCP4InterRadiationDamageDetector import (
    CCP4InterRadiationDamageDetector,
)
from xia2.Modules.Scaler.CCP4ScalerHelpers import anomalous_signals
from xia2.Schema.Interfaces.Scaler import Scaler

# new resolution limit code
from xia2.Wrappers.XIA.Merger import Merger


def clean_reindex_operator(reindex_operator):
    return reindex_operator.replace("[", "").replace("]", "")


class CommonScaler(Scaler):
    """Unified bits which the scalers have in common over the interface."""

    def __init__(self):
        super(CommonScaler, self).__init__()

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
            pname, xname, dname = si.get_project_info()
            sname = si.get_sweep_name()
            hklin = si.get_reflections()

            # limit the reflections - e.g. if we are re-running the scaling step
            # on just a subset of the integrated data

            hklin = si.get_reflections()
            limit_batch_range = None
            for sweep in PhilIndex.params.xia2.settings.sweep:
                if sweep.id == sname and sweep.range is not None:
                    limit_batch_range = sweep.range
                    break

            if limit_batch_range is not None:
                Debug.write(
                    "Limiting batch range for %s: %s" % (sname, limit_batch_range)
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

        Debug.write("Biggest sweep has %d batches" % max_batches)
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
                "%s_%s_%s_%s_integrated.mtz" % (pname, xname, dname, sname),
            )

            first_batch = min(si.get_batches())
            si.set_batch_offset(counter * max_batches - first_batch + 1)

            from xia2.Modules.Scaler.rebatch import rebatch

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
            "%s_%s_sorted.mtz" % (self._scalr_pname, self._scalr_xname),
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
                "%s %s pointless" % (self._scalr_pname, self._scalr_xname),
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
                Debug.write(
                    "Assigning user input spacegroup: %s" % self._scalr_input_spacegroup
                )

                p.decide_spacegroup()
                spacegroup = p.get_spacegroup()
                reindex_operator = p.get_spacegroup_reindex_operator()

                Debug.write(
                    "Pointless thought %s (reindex as %s)"
                    % (spacegroup, reindex_operator)
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
                Debug.write(
                    "Pointless thought %s (reindex as %s)"
                    % (spacegroup, reindex_operator)
                )

            if self._scalr_input_spacegroup:
                self._scalr_likely_spacegroups = [self._scalr_input_spacegroup]
            else:
                self._scalr_likely_spacegroups = p.get_likely_spacegroups()

            Chatter.write("Likely spacegroups:")
            for spag in self._scalr_likely_spacegroups:
                Chatter.write("%s" % spag)

            Chatter.write(
                "Reindexing to first spacegroup setting: %s (%s)"
                % (spacegroup, clean_reindex_operator(reindex_operator))
            )

        else:
            spacegroup = MtzUtils.space_group_name_from_mtz(
                self.get_scaler_reference_reflection_file()
            )
            reindex_operator = "h,k,l"

            self._scalr_likely_spacegroups = [spacegroup]

            Debug.write("Assigning spacegroup %s from reference" % spacegroup)

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

        for epoch in self._sweep_information.keys():

            hklin = self._sweep_information[epoch]["scaled_reflections"]

            if self._sweep_information[epoch]["batches"] == [0, 0]:

                Chatter.write("Getting batches from %s" % hklin)
                batches = MtzUtils.batches_from_mtz(hklin)
                self._sweep_information[epoch]["batches"] = [min(batches), max(batches)]
                Chatter.write("=> %d to %d" % (min(batches), max(batches)))

            batches = self._sweep_information[epoch]["batches"]
            if 1 + max(batches) - min(batches) > max_batches:
                max_batches = max(batches) - min(batches) + 1

        Debug.write("Biggest sweep has %d batches" % max_batches)
        max_batches = nifty_power_of_ten(max_batches)

        epochs = sorted(self._sweep_information.keys())

        counter = 0

        for epoch in epochs:

            hklin = self._sweep_information[epoch]["scaled_reflections"]

            pname = self._sweep_information[epoch]["pname"]
            xname = self._sweep_information[epoch]["xname"]
            dname = self._sweep_information[epoch]["dname"]

            sname = self._sweep_information[epoch]["sname"]

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

            from xia2.Modules.Scaler.rebatch import rebatch

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
            "%s_%s_sorted.mtz" % (self._scalr_pname, self._scalr_xname),
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
                "%s %s pointless" % (self._scalr_pname, self._scalr_xname),
                pointless.get_log_file(),
            )

            spacegroups = pointless.get_likely_spacegroups()
            reindex_operator = pointless.get_spacegroup_reindex_operator()

            if self._scalr_input_spacegroup:
                Debug.write(
                    "Assigning user input spacegroup: %s" % self._scalr_input_spacegroup
                )
                spacegroups = [self._scalr_input_spacegroup]
                reindex_operator = "h,k,l"

        self._scalr_likely_spacegroups = spacegroups
        spacegroup = self._scalr_likely_spacegroups[0]

        self._scalr_reindex_operator = reindex_operator

        Chatter.write("Likely spacegroups:")
        for spag in self._scalr_likely_spacegroups:
            Chatter.write("%s" % spag)

        Chatter.write(
            "Reindexing to first spacegroup setting: %s (%s)"
            % (spacegroup, clean_reindex_operator(reindex_operator))
        )

        hklin = self._prepared_reflections
        hklout = os.path.join(
            self.get_working_directory(),
            "%s_%s_reindex.mtz" % (self._scalr_pname, self._scalr_xname),
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
            "%s_%s_sorted.mtz" % (self._scalr_pname, self._scalr_xname),
        )

        s = self._factory.Sortmtz()
        s.set_hklin(hklin)
        s.set_hklout(hklout)

        s.sort(vrset=-99999999.0)

        self._prepared_reflections = hklout

        Debug.write(
            "Updating unit cell to %.2f %.2f %.2f %.2f %.2f %.2f" % tuple(ri.get_cell())
        )
        self._scalr_cell = tuple(ri.get_cell())

        return

    def _sort_together_data_xds_one_sweep(self):

        assert len(self._sweep_information) == 1

        epoch = self._sweep_information.keys()[0]
        hklin = self._sweep_information[epoch]["scaled_reflections"]

        if self.get_scaler_reference_reflection_file():
            spacegroups = [
                MtzUtils.space_group_name_from_mtz(
                    self.get_scaler_reference_reflection_file()
                )
            ]
            reindex_operator = "h,k,l"

        elif self._scalr_input_spacegroup:
            Debug.write(
                "Assigning user input spacegroup: %s" % self._scalr_input_spacegroup
            )
            spacegroups = [self._scalr_input_spacegroup]
            reindex_operator = "h,k,l"

        else:
            pointless = self._factory.Pointless()
            pointless.set_hklin(hklin)
            pointless.decide_spacegroup()

            FileHandler.record_log_file(
                "%s %s pointless" % (self._scalr_pname, self._scalr_xname),
                pointless.get_log_file(),
            )

            spacegroups = pointless.get_likely_spacegroups()
            reindex_operator = pointless.get_spacegroup_reindex_operator()

        self._scalr_likely_spacegroups = spacegroups
        spacegroup = self._scalr_likely_spacegroups[0]

        self._scalr_reindex_operator = clean_reindex_operator(reindex_operator)

        Chatter.write("Likely spacegroups:")
        for spag in self._scalr_likely_spacegroups:
            Chatter.write("%s" % spag)

        Chatter.write(
            "Reindexing to first spacegroup setting: %s (%s)"
            % (spacegroup, clean_reindex_operator(reindex_operator))
        )

        hklout = os.path.join(
            self.get_working_directory(),
            "%s_%s_reindex.mtz" % (self._scalr_pname, self._scalr_xname),
        )

        FileHandler.record_temporary_file(hklout)

        if reindex_operator == "[h,k,l]":
            # just assign spacegroup

            from cctbx import sgtbx

            s = sgtbx.space_group(sgtbx.space_group_symbols(str(spacegroup)).hall())

            m = mtz.object(hklin)
            m.set_space_group(s).write(hklout)
            self._scalr_cell = m.crystals()[-1].unit_cell().parameters()
            Debug.write(
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

            Debug.write(
                "Updating unit cell to %.2f %.2f %.2f %.2f %.2f %.2f"
                % tuple(ri.get_cell())
            )
            self._scalr_cell = tuple(ri.get_cell())

        hklin = hklout
        hklout = os.path.join(
            self.get_working_directory(),
            "%s_%s_sorted.mtz" % (self._scalr_pname, self._scalr_xname),
        )

        s = self._factory.Sortmtz()
        s.set_hklin(hklin)
        s.set_hklout(hklout)

        s.sort(vrset=-99999999.0)

        self._prepared_reflections = hklout

    def _scale_finish(self):

        # compute anomalous signals if anomalous
        if self.get_scaler_anomalous():
            self._scale_finish_chunk_1_compute_anomalous()

        # next transform to F's from I's etc.

        if not self._scalr_scaled_refl_files:
            raise RuntimeError("no reflection files stored")

        # run xia2.report on each unmerged mtz file
        # self._scale_finish_chunk_2_report()

        if PhilIndex.params.xia2.settings.small_molecule == False:
            self._scale_finish_chunk_3_truncate()

        self._scale_finish_chunk_4_mad_mangling()

        if PhilIndex.params.xia2.settings.small_molecule == True:
            self._scale_finish_chunk_5_finish_small_molecule()
            self._scale_finish_export_shelxt()

            return

        # finally add a FreeR column, and record the new merged reflection
        # file with the free column added.

        self._scale_finish_chunk_6_add_free_r()

        self._scale_finish_chunk_7_twinning()

        # next have a look for radiation damage... if more than one wavelength

        if len(self._scalr_scaled_refl_files.keys()) > 1:
            self._scale_finish_chunk_8_raddam()

        # finally add xia2 version to mtz history
        from iotbx.reflection_file_reader import any_reflection_file
        from xia2.XIA2Version import Version
        import time

        mtz_files = [self._scalr_scaled_reflection_files["mtz"]]
        mtz_files.extend(self._scalr_scaled_reflection_files["mtz_unmerged"].values())
        for mtz_file in mtz_files:
            reader = any_reflection_file(mtz_file)
            mtz_object = reader.file_content()
            date_str = time.strftime("%d/%m/%Y at %H:%M:%S", time.gmtime())
            mtz_object.add_history("From %s, run on %s" % (Version, date_str))
            mtz_object.write(mtz_file)

    def _scale_finish_chunk_1_compute_anomalous(self):
        for key in self._scalr_scaled_refl_files:
            f = self._scalr_scaled_refl_files[key]
            m = mtz.object(f)
            if m.space_group().is_centric():
                Debug.write("Spacegroup is centric: %s" % f)
                continue
            Debug.write("Running anomalous signal analysis on %s" % f)
            a_s = anomalous_signals(f)
            if a_s is not None:
                self._scalr_statistics[(self._scalr_pname, self._scalr_xname, key)][
                    "dF/F"
                ] = [a_s[0]]
                self._scalr_statistics[(self._scalr_pname, self._scalr_xname, key)][
                    "dI/s(dI)"
                ] = [a_s[1]]

    def _scale_finish_chunk_2_report(self):
        from cctbx.array_family import flex
        from iotbx.reflection_file_reader import any_reflection_file
        from xia2.lib.bits import auto_logfiler
        from xia2.Wrappers.XIA.Report import Report

        for wavelength in self._scalr_scaled_refl_files.keys():
            mtz_unmerged = self._scalr_scaled_reflection_files["mtz_unmerged"][
                wavelength
            ]
            reader = any_reflection_file(mtz_unmerged)
            mtz_object = reader.file_content()
            batches = mtz_object.as_miller_arrays_dict()[
                "HKL_base", "HKL_base", "BATCH"
            ]
            dose = flex.double(batches.size(), -1)
            batch_to_dose = self.get_batch_to_dose()
            for i, b in enumerate(batches.data()):
                dose[i] = batch_to_dose[b]
            c = mtz_object.crystals()[0]
            d = c.datasets()[0]
            d.add_column("DOSE", "R").set_values(dose.as_float())
            tmp_mtz = os.path.join(self.get_working_directory(), "dose_tmp.mtz")
            mtz_object.write(tmp_mtz)
            hklin = tmp_mtz
            FileHandler.record_temporary_file(hklin)

            report = Report()
            report.set_working_directory(self.get_working_directory())
            report.set_mtz_filename(hklin)
            htmlout = os.path.join(
                self.get_working_directory(),
                "%s_%s_%s_report.html"
                % (self._scalr_pname, self._scalr_xname, wavelength),
            )
            report.set_html_filename(htmlout)
            report.set_chef_min_completeness(0.95)  # sensible?
            auto_logfiler(report)
            try:
                report.run()
                FileHandler.record_html_file(
                    "%s %s %s report"
                    % (self._scalr_pname, self._scalr_xname, wavelength),
                    htmlout,
                )
            except Exception as e:
                Debug.write("xia2.report failed:")
                Debug.write(str(e))

    def _scale_finish_chunk_3_truncate(self):
        for wavelength in self._scalr_scaled_refl_files.keys():

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

            Debug.write(
                "%d absent reflections in %s removed"
                % (truncate.get_nabsent(), wavelength)
            )

            b_factor = truncate.get_b_factor()

            # record the b factor somewhere (hopefully) useful...

            self._scalr_statistics[(self._scalr_pname, self._scalr_xname, wavelength)][
                "Wilson B factor"
            ] = [b_factor]

            # and record the reflection file..
            self._scalr_scaled_refl_files[wavelength] = hklout

    def _scale_finish_chunk_4_mad_mangling(self):
        if len(self._scalr_scaled_refl_files.keys()) > 1:

            reflection_files = {}

            for wavelength in self._scalr_scaled_refl_files.keys():
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
                "%s_%s_merged.mtz" % (self._scalr_pname, self._scalr_xname),
            )
            FileHandler.record_temporary_file(hklout)

            Debug.write("Merging all data sets to %s" % hklout)

            cad = self._factory.Cad()
            for wavelength in reflection_files.keys():
                cad.add_hklin(reflection_files[wavelength])
            cad.set_hklout(hklout)
            cad.merge()

            self._scalr_scaled_reflection_files["mtz_merged"] = hklout

        else:

            self._scalr_scaled_reflection_files[
                "mtz_merged"
            ] = self._scalr_scaled_refl_files[self._scalr_scaled_refl_files.keys()[0]]

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

        from iotbx.reflection_file_reader import any_reflection_file
        from iotbx.shelx import writer
        from iotbx.shelx.hklf import miller_array_export_as_shelx_hklf
        from cctbx.xray.structure import structure
        from cctbx.xray import scatterer

        for wavelength_name in self._scalr_scaled_refl_files.keys():
            prefix = wavelength_name
            if len(self._scalr_scaled_refl_files.keys()) == 1:
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

            # FIXME do I need to reindex to a conventional setting here

            indices = reader.file_content().extract_original_index_miller_indices()
            intensities = intensities.customized_copy(
                indices=indices, info=intensities.info()
            )

            with open("%s.hkl" % prefixpath, "wb") as hkl_file_handle:
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
            "%s_%s_free_temp.mtz" % (self._scalr_pname, self._scalr_xname),
        )

        FileHandler.record_temporary_file(hklout)

        scale_params = PhilIndex.params.xia2.settings.scale
        if self.get_scaler_freer_file():
            # e.g. via .xinfo file

            freein = self.get_scaler_freer_file()

            Debug.write("Copying FreeR_flag from %s" % freein)

            c = self._factory.Cad()
            c.set_freein(freein)
            c.add_hklin(self._scalr_scaled_reflection_files["mtz_merged"])
            c.set_hklout(hklout)
            c.copyfree()

        elif scale_params.freer_file is not None:
            # e.g. via -freer_file command line argument

            freein = scale_params.freer_file

            Debug.write("Copying FreeR_flag from %s" % freein)

            c = self._factory.Cad()
            c.set_freein(freein)
            c.add_hklin(self._scalr_scaled_reflection_files["mtz_merged"])
            c.set_hklout(hklout)
            c.copyfree()

        else:

            if scale_params.free_total:
                ntot = scale_params.free_total

                # need to get a fraction, so...
                nref = MtzUtils.nref_from_mtz(hklin)
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
            "%s_%s_free.mtz" % (self._scalr_pname, self._scalr_xname),
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

    def _scale_finish_chunk_7_twinning(self):
        hklout = self._scalr_scaled_reflection_files["mtz"]

        m = mtz.object(hklout)
        # FIXME in here should be able to just drop down to the lowest symmetry
        # space group with the rotational elements for this calculation? I.e.
        # P422 for P4/mmm?
        if not m.space_group().is_centric():
            from xia2.Toolkit.E4 import E4_mtz

            E4s = E4_mtz(hklout, native=True)
            self._scalr_twinning_score = E4s.items()[0][1]

            if self._scalr_twinning_score > 1.9:
                self._scalr_twinning_conclusion = "Your data do not appear twinned"
            elif self._scalr_twinning_score < 1.6:
                self._scalr_twinning_conclusion = "Your data appear to be twinned"
            else:
                self._scalr_twinning_conclusion = "Ambiguous score (1.6 < score < 1.9)"

        else:
            self._scalr_twinning_conclusion = "Data are centric"
            self._scalr_twinning_score = 0

        Chatter.write("Overall twinning score: %4.2f" % self._scalr_twinning_score)
        Chatter.write(self._scalr_twinning_conclusion)

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
            Chatter.write("")
            Chatter.banner("Local Scaling %s" % self._scalr_xname)
            for s in status:
                Chatter.write("%s %s" % s)
            Chatter.banner("")
        else:
            Debug.write("Local scaling failed")

    def _estimate_resolution_limit(
        self, hklin, batch_range=None, use_isigma=True, use_misigma=True
    ):
        params = PhilIndex.params.xia2.settings.resolution
        m = Merger()
        m.set_working_directory(self.get_working_directory())
        from xia2.lib.bits import auto_logfiler

        auto_logfiler(m)
        m.set_hklin(hklin)
        m.set_limit_rmerge(params.rmerge)
        m.set_limit_completeness(params.completeness)
        m.set_limit_cc_half(params.cc_half)
        m.set_cc_half_fit(params.cc_half_fit)
        m.set_cc_half_significance_level(params.cc_half_significance_level)
        if use_isigma:
            m.set_limit_isigma(params.isigma)
        if use_misigma:
            m.set_limit_misigma(params.misigma)
        if PhilIndex.params.xia2.settings.small_molecule == True:
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
            resolution = max(resolution_limits)
            reasoning = [
                reason
                for limit, reason in zip(resolution_limits, reasoning)
                if limit >= resolution
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
        select_result, select_anom_result = None, None

        # don't call self.get_scaler_likely_spacegroups() since that calls
        # self.scale() which introduced a subtle bug
        from cctbx import sgtbx

        sg = sgtbx.space_group_info(str(self._scalr_likely_spacegroups[0])).group()
        from xia2.Handlers.Environment import Environment

        log_directory = Environment.generate_directory("LogFiles")
        merging_stats_file = os.path.join(
            log_directory,
            "%s_%s%s_merging-statistics.txt"
            % (
                self._scalr_pname,
                self._scalr_xname,
                "" if wave is None else "_%s" % wave,
            ),
        )
        merging_stats_json = os.path.join(
            log_directory,
            "%s_%s%s_merging-statistics.json"
            % (
                self._scalr_pname,
                self._scalr_xname,
                "" if wave is None else "_%s" % wave,
            ),
        )

        result, select_result, anom_result, select_anom_result = None, None, None, None
        n_bins = PhilIndex.params.xia2.settings.merging_statistics.n_bins
        import iotbx.merging_statistics

        while result is None:
            try:

                result = self._iotbx_merging_statistics(
                    scaled_unmerged_mtz, anomalous=False, n_bins=n_bins
                )
                result.as_json(file_name=merging_stats_json)
                with open(merging_stats_file, "w") as fh:
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
                    stats["Anomalous slope"] = [anom_result.anomalous_np_slope]
                    if four_column_output:
                        select_anom_result = self._iotbx_merging_statistics(
                            scaled_unmerged_mtz,
                            anomalous=True,
                            d_min=selected_band[0],
                            d_max=selected_band[1],
                            n_bins=n_bins,
                        )

            except iotbx.merging_statistics.StatisticsErrorNoReflectionsInRange:
                # Too few reflections for too many bins. Reduce number of bins and try again.
                result = None
                n_bins = n_bins - 3
                if n_bins > 5:
                    continue
                else:
                    raise

        from six.moves import cStringIO as StringIO

        result_cache = StringIO()
        result.show(out=result_cache)

        for d, r, s in (
            (key_to_var, result, select_result),
            (anom_key_to_var, anom_result, select_anom_result),
        ):
            for k, v in d.iteritems():
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
        import iotbx.merging_statistics

        params = PhilIndex.params.xia2.settings.merging_statistics

        i_obs = iotbx.merging_statistics.select_data(
            scaled_unmerged_mtz, data_labels=None
        )
        i_obs = i_obs.customized_copy(anomalous_flag=True, info=i_obs.info())

        result = iotbx.merging_statistics.dataset_statistics(
            i_obs=i_obs,
            d_min=d_min,
            d_max=d_max,
            n_bins=n_bins or params.n_bins,
            anomalous=anomalous,
            use_internal_variance=params.use_internal_variance,
            eliminate_sys_absent=params.eliminate_sys_absent,
            assert_is_not_unique_set_under_symmetry=False,
        )

        result.anomalous_np_slope = None
        if anomalous:
            merged_intensities = i_obs.merge_equivalents(
                use_internal_variance=params.use_internal_variance
            ).array()

            slope, intercept, n_pairs = anomalous_probability_plot(merged_intensities)
            if slope is not None:
                Debug.write("Anomalous difference normal probability plot:")
                Debug.write("Slope: %.2f" % slope)
                Debug.write("Intercept: %.2f" % intercept)
                Debug.write("Number of pairs: %i" % n_pairs)

            slope, intercept, n_pairs = anomalous_probability_plot(
                merged_intensities, expected_delta=0.9
            )
            if slope is not None:
                result.anomalous_np_slope = slope
                Debug.write(
                    "Anomalous difference normal probability plot (within expected delta 0.9):"
                )
                Debug.write("Slope: %.2f" % slope)
                Debug.write("Intercept: %.2f" % intercept)
                Debug.write("Number of pairs: %i" % n_pairs)

        return result

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

            Chatter.banner("Unit cell refinement")

            # Collect a list of all sweeps, grouped by project, crystal, wavelength
            groups = {}
            self._scalr_cell_dict = {}
            tt_refine_experiments = []
            tt_refine_pickles = []
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
                "%s_%s.p4p" % (self._scalr_pname, self._scalr_xname),
            )
            for pi in groups.keys():
                tt_grouprefiner = TwoThetaRefine()
                tt_grouprefiner.set_working_directory(self.get_working_directory())
                auto_logfiler(tt_grouprefiner)
                args = zip(*groups[pi])
                tt_grouprefiner.set_experiments(args[0])
                tt_grouprefiner.set_pickles(args[1])
                tt_grouprefiner.set_output_p4p(p4p_file)
                tt_refine_experiments.extend(args[0])
                tt_refine_pickles.extend(args[1])
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
                Chatter.write(
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
                tt_refiner.set_pickles(tt_refine_pickles)
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
                tt_refiner.set_reindex_operators(reindex_ops)
                tt_refiner.run()
                self._scalr_cell = tt_refiner.get_unit_cell()
                Chatter.write(
                    "Overall: %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f"
                    % tt_refiner.get_unit_cell()
                )
                self._scalr_cell_esd = tt_refiner.get_unit_cell_esd()
                cif_in = tt_refiner.import_cif()
                mmcif_in = tt_refiner.import_mmcif()
            else:
                self._scalr_cell, self._scalr_cell_esd, cif_in, mmcif_in = self._scalr_cell_dict.values()[
                    0
                ]
            if params.xia2.settings.small_molecule == True:
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

            Debug.write("Unit cell obtained by two-theta refinement")

        else:
            ami = AnalyseMyIntensities()
            ami.set_working_directory(self.get_working_directory())

            average_unit_cell, ignore_sg = ami.compute_average_cell(
                [
                    self._scalr_scaled_refl_files[key]
                    for key in self._scalr_scaled_refl_files
                ]
            )

            Debug.write("Computed average unit cell (will use in all files)")
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

        Debug.write("%7.3f %7.3f %7.3f %7.3f %7.3f %7.3f" % self._scalr_cell)


def anomalous_probability_plot(intensities, expected_delta=None):
    from scitbx.math import distributions
    from scitbx.array_family import flex

    assert intensities.is_unique_set_under_symmetry()
    assert intensities.anomalous_flag()

    dI = intensities.anomalous_differences()
    if not dI.size():
        return None, None, None

    y = dI.data() / dI.sigmas()
    perm = flex.sort_permutation(y)
    y = y.select(perm)
    distribution = distributions.normal_distribution()

    x = distribution.quantiles(y.size())
    if expected_delta is not None:
        sel = flex.abs(x) < expected_delta
        x = x.select(sel)
        y = y.select(sel)

    fit = flex.linear_regression(x, y)
    correlation = flex.linear_correlation(x, y)
    assert fit.is_well_defined()

    if 0:
        from matplotlib import pyplot

        pyplot.scatter(x, y)
        m = fit.slope()
        c = fit.y_intercept()
        pyplot.plot(pyplot.xlim(), [m * x_ + c for x_ in pyplot.xlim()])
        pyplot.show()

    return fit.slope(), fit.y_intercept(), x.size()
