#!/usr/bin/env python
# CommonScaler.py
#   Copyright (C) 2011 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Bits the scalers have in common - inherit from me!

from iotbx import mtz
from xia2.Schema.Interfaces.Scaler import Scaler
from xia2.Handlers.Streams import Debug, Chatter
from xia2.Handlers.Phil import PhilIndex
from CCP4ScalerHelpers import anomalous_signals
from xia2.Modules.CCP4InterRadiationDamageDetector import \
     CCP4InterRadiationDamageDetector

from xia2.lib.bits import nifty_power_of_ten
import os

from xia2.Handlers.Files import FileHandler

# new resolution limit code
from xia2.Wrappers.XIA.Merger import Merger

def clean_reindex_operator(reindex_operator):
  return reindex_operator.replace('[', '').replace(']', '')

class CommonScaler(Scaler):
  '''Unified bits which the scalers have in common over the interface.'''

  def __init__(self):
    super(CommonScaler, self).__init__()

    self._sweep_handler = None
    self._scalr_twinning_score = None
    self._scalr_twinning_conclusion = None
    self._spacegroup_reindex_operator = None

  def _sort_together_data_ccp4(self):
    '''Sort together in the right order (rebatching as we go) the sweeps
    we want to scale together.'''

    max_batches = 0

    for e in self._sweep_handler.get_epochs():
      if PhilIndex.params.xia2.settings.small_molecule == True:
        continue
      si = self._sweep_handler.get_sweep_information(e)

      pname, xname, dname = si.get_project_info()
      sname = si.get_sweep_name()



    for epoch in self._sweep_handler.get_epochs():

      si = self._sweep_handler.get_sweep_information(epoch)
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
        Debug.write('Limiting batch range for %s: %s' %(sname, limit_batch_range))
        start, end = limit_batch_range
        hklout = os.path.splitext(hklin)[0] + '_tmp.mtz'
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
      md = self._factory.Mtzdump()
      md.set_hklin(hklin)
      md.dump()

      batches = md.get_batches()
      if 1 + max(batches) - min(batches) > max_batches:
        max_batches = max(batches) - min(batches) + 1

      datasets = md.get_datasets()

      Debug.write('In reflection file %s found:' % hklin)
      for d in datasets:
        Debug.write('... %s' % d)

      dataset_info = md.get_dataset_info(datasets[0])

    Debug.write('Biggest sweep has %d batches' % max_batches)
    max_batches = nifty_power_of_ten(max_batches)

    # then rebatch the files, to make sure that the batch numbers are
    # in the same order as the epochs of data collection.

    counter = 0

    for epoch in self._sweep_handler.get_epochs():

      si = self._sweep_handler.get_sweep_information(epoch)
      rb = self._factory.Rebatch()

      hklin = si.get_reflections()

      pname, xname, dname = si.get_project_info()
      sname = si.get_sweep_name()

      hklout = os.path.join(self.get_working_directory(),
                            '%s_%s_%s_%s_integrated.mtz' % \
                            (pname, xname, dname, sname))

      first_batch = min(si.get_batches())
      si.set_batch_offset(counter * max_batches - first_batch + 1)

      rb.set_hklin(hklin)
      rb.set_first_batch(counter * max_batches + 1)
      rb.set_project_info(pname, xname, dname)
      rb.set_hklout(hklout)

      new_batches = rb.rebatch()

      # update the "input information"

      si.set_reflections(hklout)
      si.set_batches(new_batches)

      # update the counter & recycle

      counter += 1

    s = self._factory.Sortmtz()

    hklout = os.path.join(self.get_working_directory(),
                          '%s_%s_sorted.mtz' % \
                          (self._scalr_pname, self._scalr_xname))

    s.set_hklout(hklout)

    for epoch in self._sweep_handler.get_epochs():
      s.add_hklin(self._sweep_handler.get_sweep_information(
          epoch).get_reflections())

    s.sort()

    # verify that the measurements are in the correct setting
    # choice for the spacegroup

    hklin = hklout
    hklout = hklin.replace('sorted.mtz', 'temp.mtz')

    if not self.get_scaler_reference_reflection_file():

      p = self._factory.Pointless()

      FileHandler.record_log_file('%s %s pointless' % \
                                  (self._scalr_pname,
                                   self._scalr_xname),
                                  p.get_log_file())

      if len(self._sweep_handler.get_epochs()) > 1:
        p.set_hklin(hklin)
      else:
        # permit the use of pointless preparation...
        epoch = self._sweep_handler.get_epochs()[0]
        p.set_hklin(self._prepare_pointless_hklin(
            hklin, self._sweep_handler.get_sweep_information(
            epoch).get_integrater().get_phi_width()))

      if self._scalr_input_spacegroup:
        Debug.write('Assigning user input spacegroup: %s' % \
                    self._scalr_input_spacegroup)

        p.decide_spacegroup()
        spacegroup = p.get_spacegroup()
        reindex_operator = p.get_spacegroup_reindex_operator()

        Debug.write('Pointless thought %s (reindex as %s)' % \
                    (spacegroup, reindex_operator))

        spacegroup = self._scalr_input_spacegroup
        reindex_operator = 'h,k,l'
        self._spacegroup_reindex_operator = reindex_operator

      else:
        p.decide_spacegroup()
        spacegroup = p.get_spacegroup()
        reindex_operator = p.get_spacegroup_reindex_operator()
        self._spacegroup_reindex_operator = clean_reindex_operator(reindex_operator)
        Debug.write('Pointless thought %s (reindex as %s)' % \
                    (spacegroup, reindex_operator))

      if self._scalr_input_spacegroup:
        self._scalr_likely_spacegroups = [self._scalr_input_spacegroup]
      else:
        self._scalr_likely_spacegroups = p.get_likely_spacegroups()

      Chatter.write('Likely spacegroups:')
      for spag in self._scalr_likely_spacegroups:
        Chatter.write('%s' % spag)

      Chatter.write(
          'Reindexing to first spacegroup setting: %s (%s)' % \
          (spacegroup, clean_reindex_operator(reindex_operator)))

    else:

      md = self._factory.Mtzdump()
      md.set_hklin(self.get_scaler_reference_reflection_file())
      md.dump()

      spacegroup = md.get_spacegroup()
      reindex_operator = 'h,k,l'

      self._scalr_likely_spacegroups = [spacegroup]

      Debug.write('Assigning spacegroup %s from reference' % \
                  spacegroup)

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

      hklin = self._sweep_information[epoch]['scaled_reflections']

      md = self._factory.Mtzdump()
      md.set_hklin(hklin)
      md.dump()

      if self._sweep_information[epoch]['batches'] == [0, 0]:

        Chatter.write('Getting batches from %s' % hklin)
        batches = md.get_batches()
        self._sweep_information[epoch]['batches'] = [min(batches),
                                                     max(batches)]
        Chatter.write('=> %d to %d' % (min(batches),
                                       max(batches)))

      batches = self._sweep_information[epoch]['batches']
      if 1 + max(batches) - min(batches) > max_batches:
        max_batches = max(batches) - min(batches) + 1

      datasets = md.get_datasets()

      Debug.write('In reflection file %s found:' % hklin)
      for d in datasets:
        Debug.write('... %s' % d)

      dataset_info = md.get_dataset_info(datasets[0])

    Debug.write('Biggest sweep has %d batches' % max_batches)
    max_batches = nifty_power_of_ten(max_batches)

    epochs = self._sweep_information.keys()
    epochs.sort()

    counter = 0

    for epoch in epochs:
      rb = self._factory.Rebatch()

      hklin = self._sweep_information[epoch]['scaled_reflections']

      pname = self._sweep_information[epoch]['pname']
      xname = self._sweep_information[epoch]['xname']
      dname = self._sweep_information[epoch]['dname']

      sname = self._sweep_information[epoch]['sname']

      hklout = os.path.join(self.get_working_directory(),
                            '%s_%s_%s_%d.mtz' % \
                            (pname, xname, dname, counter))

      # we will want to delete this one exit
      FileHandler.record_temporary_file(hklout)

      # record this for future reference - will be needed in the
      # radiation damage analysis...

      # hack - reset this as it gets in a muddle...
      intgr = self._sweep_information[epoch]['integrater']
      self._sweep_information[epoch][
          'batches'] = intgr.get_integrater_batches()

      first_batch = min(self._sweep_information[epoch]['batches'])
      self._sweep_information[epoch][
          'batch_offset'] = counter * max_batches - first_batch + 1

      rb.set_hklin(hklin)
      rb.set_first_batch(counter * max_batches + 1)
      rb.set_hklout(hklout)

      new_batches = rb.rebatch()

      # update the "input information"

      self._sweep_information[epoch]['hklin'] = hklout
      self._sweep_information[epoch]['batches'] = new_batches

      # update the counter & recycle

      counter += 1

    s = self._factory.Sortmtz()

    hklout = os.path.join(self.get_working_directory(),
                          '%s_%s_sorted.mtz' % \
                          (self._scalr_pname, self._scalr_xname))

    s.set_hklout(hklout)

    for epoch in epochs:
      s.add_hklin(self._sweep_information[epoch]['hklin'])

    s.sort(vrset = -99999999.0)

    self._prepared_reflections = hklout

    if self.get_scaler_reference_reflection_file():
      md = self._factory.Mtzdump()
      md.set_hklin(self.get_scaler_reference_reflection_file())
      md.dump()

      spacegroups = [md.get_spacegroup()]
      reindex_operator = 'h,k,l'

    else:

      pointless = self._factory.Pointless()
      pointless.set_hklin(hklout)
      pointless.decide_spacegroup()

      FileHandler.record_log_file('%s %s pointless' % \
                                  (self._scalr_pname,
                                   self._scalr_xname),
                                  pointless.get_log_file())

      spacegroups = pointless.get_likely_spacegroups()
      reindex_operator = pointless.get_spacegroup_reindex_operator()

      if self._scalr_input_spacegroup:
        Debug.write('Assigning user input spacegroup: %s' % \
                    self._scalr_input_spacegroup)
        spacegroups = [self._scalr_input_spacegroup]
        reindex_operator = 'h,k,l'

    self._scalr_likely_spacegroups = spacegroups
    spacegroup = self._scalr_likely_spacegroups[0]

    self._scalr_reindex_operator = reindex_operator

    Chatter.write('Likely spacegroups:')
    for spag in self._scalr_likely_spacegroups:
      Chatter.write('%s' % spag)

    Chatter.write(
        'Reindexing to first spacegroup setting: %s (%s)' % \
        (spacegroup, clean_reindex_operator(reindex_operator)))

    hklin = self._prepared_reflections
    hklout = os.path.join(self.get_working_directory(),
                          '%s_%s_reindex.mtz' % \
                          (self._scalr_pname, self._scalr_xname))

    FileHandler.record_temporary_file(hklout)

    ri = self._factory.Reindex()
    ri.set_hklin(hklin)
    ri.set_hklout(hklout)
    ri.set_spacegroup(spacegroup)
    ri.set_operator(reindex_operator)
    ri.reindex()

    hklin = hklout
    hklout = os.path.join(self.get_working_directory(),
                          '%s_%s_sorted.mtz' % \
                          (self._scalr_pname, self._scalr_xname))

    s = self._factory.Sortmtz()
    s.set_hklin(hklin)
    s.set_hklout(hklout)

    s.sort(vrset = -99999999.0)

    self._prepared_reflections = hklout

    Debug.write(
        'Updating unit cell to %.2f %.2f %.2f %.2f %.2f %.2f' % \
        tuple(ri.get_cell()))
    self._scalr_cell = tuple(ri.get_cell())

    return

  def _sort_together_data_xds_one_sweep(self):

    assert(len(self._sweep_information) == 1)

    epoch = self._sweep_information.keys()[0]
    hklin = self._sweep_information[epoch]['scaled_reflections']

    if self.get_scaler_reference_reflection_file():
      md = self._factory.Mtzdump()
      md.set_hklin(self.get_scaler_reference_reflection_file())
      md.dump()

      spacegroups = [md.get_spacegroup()]
      reindex_operator = 'h,k,l'

    elif self._scalr_input_spacegroup:
      Debug.write('Assigning user input spacegroup: %s' % \
                  self._scalr_input_spacegroup)
      spacegroups = [self._scalr_input_spacegroup]
      reindex_operator = 'h,k,l'

    else:
      pointless = self._factory.Pointless()
      pointless.set_hklin(hklin)
      pointless.decide_spacegroup()

      FileHandler.record_log_file('%s %s pointless' % \
                                  (self._scalr_pname,
                                   self._scalr_xname),
                                  pointless.get_log_file())

      spacegroups = pointless.get_likely_spacegroups()
      reindex_operator = pointless.get_spacegroup_reindex_operator()


    self._scalr_likely_spacegroups = spacegroups
    spacegroup = self._scalr_likely_spacegroups[0]

    self._scalr_reindex_operator = clean_reindex_operator(reindex_operator)

    Chatter.write('Likely spacegroups:')
    for spag in self._scalr_likely_spacegroups:
      Chatter.write('%s' % spag)

    Chatter.write(
        'Reindexing to first spacegroup setting: %s (%s)' % \
        (spacegroup, clean_reindex_operator(reindex_operator)))

    hklout = os.path.join(self.get_working_directory(),
                          '%s_%s_reindex.mtz' % \
                          (self._scalr_pname, self._scalr_xname))

    FileHandler.record_temporary_file(hklout)

    if reindex_operator == '[h,k,l]':
      # just assign spacegroup

      from cctbx import sgtbx

      s = sgtbx.space_group(sgtbx.space_group_symbols(
           str(spacegroup)).hall())

      m = mtz.object(hklin)
      m.set_space_group(s).write(hklout)
      self._scalr_cell = m.crystals()[-1].unit_cell().parameters()
      Debug.write(
          'Updating unit cell to %.2f %.2f %.2f %.2f %.2f %.2f' % \
          tuple(self._scalr_cell))
      del(m)
      del(s)

    else:
      ri = self._factory.Reindex()
      ri.set_hklin(hklin)
      ri.set_hklout(hklout)
      ri.set_spacegroup(spacegroup)
      ri.set_operator(reindex_operator)
      ri.reindex()

      Debug.write(
          'Updating unit cell to %.2f %.2f %.2f %.2f %.2f %.2f' % \
          tuple(ri.get_cell()))
      self._scalr_cell = tuple(ri.get_cell())

    hklin = hklout
    hklout = os.path.join(self.get_working_directory(),
                          '%s_%s_sorted.mtz' % \
                          (self._scalr_pname, self._scalr_xname))

    s = self._factory.Sortmtz()
    s.set_hklin(hklin)
    s.set_hklout(hklout)

    s.sort(vrset = -99999999.0)

    self._prepared_reflections = hklout

  def _scale_finish(self):

    # compute anomalous signals if anomalous
    if self.get_scaler_anomalous():
      self._scale_finish_chunk_1_compute_anomalous()

    # next transform to F's from I's etc.

    if not self._scalr_scaled_refl_files:
      raise RuntimeError, 'no reflection files stored'

    # run xia2.report on each unmerged mtz file
    self._scale_finish_chunk_2_report()

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

  def _scale_finish_chunk_1_compute_anomalous(self):
     for key in self._scalr_scaled_refl_files:
        f = self._scalr_scaled_refl_files[key]
        m = mtz.object(f)
        if m.space_group().is_centric():
          Debug.write('Spacegroup is centric: %s' % f)
          continue
        Debug.write('Running anomalous signal analysis on %s' % f)
        a_s = anomalous_signals(f)
        self._scalr_statistics[
            (self._scalr_pname, self._scalr_xname, key)
            ]['dF/F'] = [a_s[0]]
        self._scalr_statistics[
            (self._scalr_pname, self._scalr_xname, key)
            ]['dI/s(dI)'] = [a_s[1]]

  def _scale_finish_chunk_2_report(self):
    from cctbx.array_family import flex
    from iotbx.reflection_file_reader import any_reflection_file
    from xia2.lib.bits import auto_logfiler
    from xia2.Wrappers.XIA.Report import Report

    for wavelength in self._scalr_scaled_refl_files.keys():
      mtz_unmerged = self._scalr_scaled_reflection_files['mtz_unmerged'][wavelength]
      reader = any_reflection_file(mtz_unmerged)
      mtz_object = reader.file_content()
      batches = mtz_object.as_miller_arrays_dict()['HKL_base', 'HKL_base', 'BATCH']
      dose = flex.double(batches.size(), -1)
      batch_to_dose = self.get_batch_to_dose()
      for i, b in enumerate(batches.data()):
        dose[i] = batch_to_dose[b]
      c = mtz_object.crystals()[0]
      d = c.datasets()[0]
      d.add_column('DOSE', 'R').set_values(dose.as_float())
      tmp_mtz = os.path.join(self.get_working_directory(), 'dose_tmp.mtz')
      mtz_object.write(tmp_mtz)
      hklin = tmp_mtz
      FileHandler.record_temporary_file(hklin)

      report = Report()
      report.set_working_directory(self.get_working_directory())
      report.set_mtz_filename(hklin)
      htmlout = os.path.join(
        self.get_working_directory(), '%s_%s_%s_report.html' %(
          self._scalr_pname, self._scalr_xname, wavelength))
      report.set_html_filename(htmlout)
      report.set_chef_min_completeness(0.95) # sensible?
      auto_logfiler(report)
      try:
        report.run()
        FileHandler.record_html_file(
          '%s %s %s report' %(
            self._scalr_pname, self._scalr_xname, wavelength), htmlout)
      except Exception, e:
        Debug.write('xia2.report failed:')
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

        FileHandler.record_log_file('%s %s %s truncate' % \
                                    (self._scalr_pname,
                                     self._scalr_xname,
                                     wavelength),
                                    truncate.get_log_file())

        hklout = os.path.join(self.get_working_directory(),
                              '%s_truncated.mtz' % wavelength)

        truncate.set_hklout(hklout)
        truncate.truncate()

        xmlout = truncate.get_xmlout()
        if xmlout is not None:
          FileHandler.record_xml_file('%s %s %s truncate' % \
                                      (self._scalr_pname,
                                       self._scalr_xname,
                                       wavelength),
                                      xmlout)

        Debug.write('%d absent reflections in %s removed' % \
                    (truncate.get_nabsent(), wavelength))

        b_factor = truncate.get_b_factor()

        # record the b factor somewhere (hopefully) useful...

        self._scalr_statistics[
            (self._scalr_pname, self._scalr_xname, wavelength)
            ]['Wilson B factor'] = [b_factor]

        # and record the reflection file..
        self._scalr_scaled_refl_files[wavelength] = hklout

  def _scale_finish_chunk_4_mad_mangling(self):
    if len(self._scalr_scaled_refl_files.keys()) > 1:

      reflection_files = { }

      for wavelength in self._scalr_scaled_refl_files.keys():
        cad = self._factory.Cad()
        cad.add_hklin(self._scalr_scaled_refl_files[wavelength])
        cad.set_hklout(os.path.join(
            self.get_working_directory(),
            'cad-tmp-%s.mtz' % wavelength))
        cad.set_new_suffix(wavelength)
        cad.update()

        reflection_files[wavelength] = cad.get_hklout()
        FileHandler.record_temporary_file(cad.get_hklout())

      # now merge the reflection files together...
      hklout = os.path.join(self.get_working_directory(),
                            '%s_%s_merged.mtz' % (self._scalr_pname,
                                                  self._scalr_xname))
      FileHandler.record_temporary_file(hklout)

      Debug.write('Merging all data sets to %s' % hklout)

      cad = self._factory.Cad()
      for wavelength in reflection_files.keys():
        cad.add_hklin(reflection_files[wavelength])
      cad.set_hklout(hklout)
      cad.merge()

      self._scalr_scaled_reflection_files['mtz_merged'] = hklout

    else:

      self._scalr_scaled_reflection_files[
          'mtz_merged'] = self._scalr_scaled_refl_files[
          self._scalr_scaled_refl_files.keys()[0]]

  def _scale_finish_chunk_5_finish_small_molecule(self):
      # keep 'mtz' and remove 'mtz_merged' from the dictionary for
      # consistency with non-small-molecule workflow
      self._scalr_scaled_reflection_files['mtz'] = \
        self._scalr_scaled_reflection_files['mtz_merged']
      del self._scalr_scaled_reflection_files['mtz_merged']

      FileHandler.record_data_file(self._scalr_scaled_reflection_files['mtz'])

  def _scale_finish_export_shelxt(self):
    '''Read hklin (unmerged reflection file) and generate SHELXT input file
    and HKL file'''

    from iotbx.reflection_file_reader import any_reflection_file
    from iotbx.shelx import writer
    from iotbx.shelx.hklf import miller_array_export_as_shelx_hklf
    from cctbx.xray.structure import structure
    from cctbx.xray import scatterer

    for wavelength_name in self._scalr_scaled_refl_files.keys():
      prefix = wavelength_name
      if len(self._scalr_scaled_refl_files.keys()) == 1:
        prefix = 'shelxt'
      prefixpath = os.path.join(self.get_working_directory(), prefix)

      mtz_unmerged = self._scalr_scaled_reflection_files['mtz_unmerged'][wavelength_name]
      reader = any_reflection_file(mtz_unmerged)
      intensities = [ma for ma in reader.as_miller_arrays(merge_equivalents=False)
                     if ma.info().labels == ['I', 'SIGI']][0]

      # FIXME do I need to reindex to a conventional setting here

      indices = reader.file_content().extract_original_index_miller_indices()
      intensities = intensities.customized_copy(indices=indices, info=intensities.info())

      with open('%s.hkl' % prefixpath, 'wb') as hkl_file_handle:
        # limit values to 4 digits (before decimal point), as this is what shelxt
        # writes in its output files, and shelxl seems to read. ShelXL apparently
        # does not read values >9999 properly
        miller_array_export_as_shelx_hklf(intensities, hkl_file_handle,
          scale_range=(-9999., 9999.), normalise_if_format_overflow=True)

      crystal_symm = intensities.crystal_symmetry()

      unit_cell_dims = self._scalr_cell
      unit_cell_esds = self._scalr_cell_esd

      cb_op = crystal_symm.change_of_basis_op_to_reference_setting()

      if cb_op.c().r().as_hkl() == 'h,k,l':
        print 'Change of basis to reference setting: %s' % cb_op
        crystal_symm = crystal_symm.change_basis(cb_op)
        if str(cb_op) != "a,b,c":
          unit_cell_dims = None
          unit_cell_esds = None
          # Would need to apply operation to cell errors, too. Need a test case for this

      # crystal_symm.show_summary()
      xray_structure = structure(crystal_symmetry=crystal_symm)

      compound = 'CNOH'
      if compound:
        from xia2.command_line.to_shelx import parse_compound
        result = parse_compound(compound)
        for element in result:
          xray_structure.add_scatterer(scatterer(label=element,
                                                 occupancy=result[element]))

      wavelength = self._scalr_xcrystal.get_xwavelength(wavelength_name).get_wavelength()

      with open('%s.ins' % prefixpath, 'w') as insfile:
        insfile.write(''.join(writer.generator(
               xray_structure,
               wavelength=wavelength,
               full_matrix_least_squares_cycles=0,
               title=prefix,
               unit_cell_dims=unit_cell_dims,
               unit_cell_esds=unit_cell_esds)))

      FileHandler.record_data_file('%s.ins' % prefixpath)
      FileHandler.record_data_file('%s.hkl' % prefixpath)

  def _scale_finish_chunk_6_add_free_r(self):
    hklout = os.path.join(self.get_working_directory(),
                          '%s_%s_free_temp.mtz' % (self._scalr_pname,
                                                   self._scalr_xname))

    FileHandler.record_temporary_file(hklout)

    scale_params = PhilIndex.params.xia2.settings.scale
    if self.get_scaler_freer_file():
      # e.g. via .xinfo file

      freein = self.get_scaler_freer_file()

      Debug.write('Copying FreeR_flag from %s' % freein)

      c = self._factory.Cad()
      c.set_freein(freein)
      c.add_hklin(self._scalr_scaled_reflection_files['mtz_merged'])
      c.set_hklout(hklout)
      c.copyfree()

    elif scale_params.freer_file is not None:
      # e.g. via -freer_file command line argument

      freein = scale_params.freer_file

      Debug.write('Copying FreeR_flag from %s' % freein)

      c = self._factory.Cad()
      c.set_freein(freein)
      c.add_hklin(self._scalr_scaled_reflection_files['mtz_merged'])
      c.set_hklout(hklout)
      c.copyfree()

    else:

      if scale_params.free_total:
        ntot = scale_params.free_total

        # need to get a fraction, so...
        mtzdump = self._factory.Mtzdump()
        mtzdump.set_hklin(hklin)
        mtzdump.dump()
        nref = mtzdump.get_reflections()
        free_fraction = float(ntot) / float(nref)
      else:
        free_fraction = scale_params.free_fraction

      f = self._factory.Freerflag()
      f.set_free_fraction(free_fraction)
      f.set_hklin(self._scalr_scaled_reflection_files['mtz_merged'])
      f.set_hklout(hklout)
      f.add_free_flag()

    # then check that this FreeR set is complete

    hklin = hklout
    hklout = os.path.join(self.get_working_directory(),
                          '%s_%s_free.mtz' % (self._scalr_pname,
                                              self._scalr_xname))

    # default fraction of 0.05
    free_fraction = 0.05

    if scale_params.free_fraction:
      free_fraction = scale_params.free_fraction
    elif scale_params.free_total:
      ntot = scale_params.free_total()

      # need to get a fraction, so...
      mtzdump = self._factory.Mtzdump()
      mtzdump.set_hklin(hklin)
      mtzdump.dump()
      nref = mtzdump.get_reflections()
      free_fraction = float(ntot) / float(nref)

    f = self._factory.Freerflag()
    f.set_free_fraction(free_fraction)
    f.set_hklin(hklin)
    f.set_hklout(hklout)
    f.complete_free_flag()

    # remove 'mtz_merged' from the dictionary - this is made
    # redundant by the merged free...
    del self._scalr_scaled_reflection_files['mtz_merged']

    # changed from mtz_merged_free to plain ol' mtz
    self._scalr_scaled_reflection_files['mtz'] = hklout

    # record this for future reference
    FileHandler.record_data_file(hklout)

  def _scale_finish_chunk_7_twinning(self):
    hklout = self._scalr_scaled_reflection_files['mtz']

    m = mtz.object(hklout)
    # FIXME in here should be able to just drop down to the lowest symmetry
    # space group with the rotational elements for this calculation? I.e.
    # P422 for P4/mmm?
    if not m.space_group().is_centric():
      from xia2.Toolkit.E4 import E4_mtz
      E4s = E4_mtz(hklout, native = True)
      self._scalr_twinning_score = E4s.items()[0][1]

      if self._scalr_twinning_score > 1.9:
        self._scalr_twinning_conclusion = 'Your data do not appear twinned'
      elif self._scalr_twinning_score < 1.6:
        self._scalr_twinning_conclusion = 'Your data appear to be twinned'
      else:
        self._scalr_twinning_conclusion = 'Ambiguous score (1.6 < score < 1.9)'

    else:
      self._scalr_twinning_conclusion = 'Data are centric'
      self._scalr_twinning_score = 0

    Chatter.write('Overall twinning score: %4.2f' % self._scalr_twinning_score)
    Chatter.write(self._scalr_twinning_conclusion)

  def _scale_finish_chunk_8_raddam(self):
      crd = CCP4InterRadiationDamageDetector()

      crd.set_working_directory(self.get_working_directory())

      crd.set_hklin(self._scalr_scaled_reflection_files['mtz'])

      if self.get_scaler_anomalous():
        crd.set_anomalous(True)

      hklout = os.path.join(self.get_working_directory(), 'temp.mtz')
      FileHandler.record_temporary_file(hklout)

      crd.set_hklout(hklout)

      status = crd.detect()

      if status:
        Chatter.write('')
        Chatter.banner('Local Scaling %s' % self._scalr_xname)
        for s in status:
          Chatter.write('%s %s' % s)
        Chatter.banner('')
      else:
        Debug.write('Local scaling failed')

  def _estimate_resolution_limit(self, hklin, batch_range=None):
    params = PhilIndex.params.xia2.settings.resolution
    m = Merger()
    m.set_working_directory(self.get_working_directory())
    from xia2.lib.bits import auto_logfiler
    auto_logfiler(m)
    m.set_hklin(hklin)
    m.set_limit_rmerge(params.rmerge)
    m.set_limit_completeness(params.completeness)
    m.set_limit_cc_half(params.cc_half)
    m.set_cc_half_significance_level(params.cc_half_significance_level)
    m.set_limit_isigma(params.isigma)
    m.set_limit_misigma(params.misigma)
    if PhilIndex.params.xia2.settings.small_molecule == True:
      m.set_nbins(20)
    if batch_range is not None:
      start, end = batch_range
      m.set_batch_range(start, end)
    m.run()

    if params.completeness:
      r_comp = m.get_resolution_completeness()
    else:
      r_comp = 0.0

    if params.cc_half:
      r_cc_half = m.get_resolution_cc_half()
    else:
      r_cc_half = 0.0

    if params.rmerge:
      r_rm = m.get_resolution_rmerge()
    else:
      r_rm = 0.0

    if params.isigma:
      r_uis = m.get_resolution_isigma()
    else:
      r_uis = 0.0

    if params.misigma:
      r_mis = m.get_resolution_misigma()
    else:
      r_mis = 0.0

    resolution = max([r_comp, r_rm, r_uis, r_mis, r_cc_half])

    return resolution

  def _compute_scaler_statistics(self, scaled_unmerged_mtz, selected_band=None, wave=None):
    ''' selected_band = (d_min, d_max) with None for automatic determination. '''
    # mapping of expected dictionary names to iotbx.merging_statistics attributes
    key_to_var = {
      'I/sigma': 'i_over_sigma_mean',
      'Completeness': 'completeness',
      'Low resolution limit': 'd_max',
      'Multiplicity': 'mean_redundancy',
      'Rmerge(I)': 'r_merge',
      #'Wilson B factor':,
      'Rmeas(I)': 'r_meas',
      'High resolution limit': 'd_min',
      'Total observations': 'n_obs',
      'Rpim(I)': 'r_pim',
      'CC half': 'cc_one_half',
      'Total unique': 'n_uniq',
    }

    anom_key_to_var = {
      'Rmerge(I+/-)': 'r_merge',
      'Rpim(I+/-)': 'r_pim',
      'Rmeas(I+/-)': 'r_meas',
      'Anomalous completeness': 'anom_completeness',
      'Anomalous correlation': 'anom_half_corr',
      'Anomalous multiplicity': 'mean_redundancy',
    }

    stats = {}
    select_result, select_anom_result = None, None

    # don't call self.get_scaler_likely_spacegroups() since that calls
    # self.scale() which introduced a subtle bug
    from cctbx import sgtbx
    sg = sgtbx.space_group_info(str(self._scalr_likely_spacegroups[0])).group()

    result = self._iotbx_merging_statistics(
      scaled_unmerged_mtz, anomalous=False)

    from xia2.Handlers.Environment import Environment
    log_directory = Environment.generate_directory('LogFiles')
    merging_stats_file = '%s_%s%s_merging-statistics.txt' % (
      self._scalr_pname, self._scalr_xname, '' if wave is None else '_%s' % wave)
    with open(os.path.join(log_directory, merging_stats_file), 'w') as fh:
      result.show(out=fh)

    four_column_output = selected_band and any(selected_band)
    if four_column_output:
      select_result = self._iotbx_merging_statistics(
        scaled_unmerged_mtz, anomalous=False,
        d_min=selected_band[0], d_max=selected_band[1])

    if sg.is_centric():
      anom_result = None
      anom_key_to_var = {}
    else:
      anom_result = self._iotbx_merging_statistics(
        scaled_unmerged_mtz, anomalous=True)
      stats['Anomalous slope'] = [anom_result.anomalous_np_slope]
      if four_column_output:
        select_anom_result = self._iotbx_merging_statistics(
          scaled_unmerged_mtz, anomalous=True,
          d_min=selected_band[0], d_max=selected_band[1])

    import cStringIO as StringIO
    result_cache = StringIO.StringIO()
    result.show(out=result_cache)

    for d, r, s in ((key_to_var, result, select_result), (anom_key_to_var, anom_result, select_anom_result)):
      for k, v in d.iteritems():
        if four_column_output:
          values = (
            getattr(s.overall, v),
            getattr(s.bins[0], v),
            getattr(s.bins[-1], v),
            getattr(r.overall, v))
        else:
          values = (
            getattr(r.overall, v),
            getattr(r.bins[0], v),
            getattr(r.bins[-1], v))
        if 'completeness' in v:
          values = [v_ * 100 for v_ in values]
        if values[0] is not None:
          stats[k] = values

    return stats

  def _iotbx_merging_statistics(self, scaled_unmerged_mtz, anomalous=False, d_min=None, d_max=None):
    import iotbx.merging_statistics

    params = PhilIndex.params.xia2.settings.merging_statistics

    i_obs = iotbx.merging_statistics.select_data(scaled_unmerged_mtz, data_labels=None)
    i_obs = i_obs.customized_copy(anomalous_flag=True, info=i_obs.info())

    result = iotbx.merging_statistics.dataset_statistics(
      i_obs=i_obs,
      #crystal_symmetry=symm,
      d_min=d_min,
      d_max=d_max,
      n_bins=params.n_bins,
      anomalous=anomalous,
      #debug=params.debug,
      #file_name=params.file_name,
      #sigma_filtering=params.sigma_filtering,
      use_internal_variance=params.use_internal_variance,
      eliminate_sys_absent=params.eliminate_sys_absent,
      #extend_d_max_min=params.extend_d_max_min,
      #log=out
    )

    if anomalous:
      merged_intensities = i_obs.merge_equivalents(
        use_internal_variance=params.use_internal_variance).array()
      slope, intercept, n_pairs = anomalous_probability_plot(merged_intensities)

      Debug.write('Anomalous difference normal probability plot:')
      Debug.write('Slope: %.2f' %slope)
      Debug.write('Intercept: %.2f' %intercept)
      Debug.write('Number of pairs: %i' %n_pairs)

      slope, intercept, n_pairs = anomalous_probability_plot(
        merged_intensities, expected_delta=0.9)
      result.anomalous_np_slope = slope

      Debug.write('Anomalous difference normal probability plot (within expected delta 0.9):')
      Debug.write('Slope: %.2f' %slope)
      Debug.write('Intercept: %.2f' %intercept)
      Debug.write('Number of pairs: %i' %n_pairs)

    else:
      result.anomalous_np_slope = None

    return result

def anomalous_probability_plot(intensities, expected_delta=None):
  from scitbx.math import distributions
  from scitbx.array_family import flex

  assert intensities.is_unique_set_under_symmetry()
  assert intensities.anomalous_flag()

  dI = intensities.anomalous_differences()
  y = dI.data()/dI.sigmas()
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
