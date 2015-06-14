#!/usr/bin/env python
# CommonScaler.py
#   Copyright (C) 2011 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Bits the scalers have in common - inherit from me!

from Schema.Interfaces.Scaler import Scaler
from Handlers.Streams import Debug, Chatter
from Handlers.Flags import Flags
from CCP4ScalerHelpers import anomalous_signals
from Modules.CCP4InterRadiationDamageDetector import \
     CCP4InterRadiationDamageDetector

from lib.bits import nifty_power_of_ten
import os
import math

from Handlers.Files import FileHandler

# new resolution limit code
from Wrappers.XIA.Merger import Merger

def clean_reindex_operator(reindex_operator):
  return reindex_operator.replace('[', '').replace(']', '')

class CommonScaler(Scaler):
  '''Unified bits which the scalers have in common over the interface.'''

  def __init__(self):
    super(CommonScaler, self).__init__()

    self._sweep_handler = None
    self._scalr_twinning_score = None
    self._scalr_twinning_conclusion = None

  def _sort_together_data_ccp4(self):
    '''Sort together in the right order (rebatching as we go) the sweeps
    we want to scale together.'''

    max_batches = 0

    for epoch in self._sweep_handler.get_epochs():

      # keep a count of the maximum number of batches in a block -
      # this will be used to make rebatch work below.

      si = self._sweep_handler.get_sweep_information(epoch)
      hklin = si.get_reflections()

      md = self._factory.Mtzdump()
      md.set_hklin(hklin)
      md.dump()

      batches = si.get_batches()
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

      else:
        p.decide_spacegroup()
        spacegroup = p.get_spacegroup()
        reindex_operator = p.get_spacegroup_reindex_operator()

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

    return

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

    if Flags.get_chef():
      self._sweep_information_to_chef()

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

    if Flags.get_chef():
      self._sweep_information_to_chef()

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

    self._scalr_reindex_operator = reindex_operator

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

      from iotbx import mtz
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

    return

  def _sweep_information_to_chef(self):
    '''Analyse the sweep_information data structure to work out which
    measurements should be compared in chef. This will then print out
    an opinion of what should be compared by sweep epoch / image name.'''

    dose_rates = []
    wavelengths = []
    groups = { }
    batch_groups = { }
    resolutions = { }

    # FIXME need to estimate the inscribed circle resolution from the
    # image header information - the lowest for each group will be used
    # for the analysis... Actually - this will be the lowest resolution
    # of all of the integrater resolutions *and* all of the inscribed
    # circle resolutions...

    for epoch in sorted(self._sweep_information):
      header = self._sweep_information[epoch]['header']
      batches = self._sweep_information[epoch]['batches']
      dr = header['exposure_time'] / header['phi_width']
      wave = self._sweep_information[epoch]['dname']
      template = self._sweep_information[epoch][
          'integrater'].get_template()

      # FIXME should these not really just be inherited / propogated
      # through the FrameProcessor interface? Trac #255.

      indxr = self._sweep_information[epoch][
          'integrater'].get_integrater_indexer()
      beam = indxr.get_indexer_beam_centre()
      distance = indxr.get_indexer_distance()
      wavelength = self._sweep_information[epoch][
          'integrater'].get_wavelength()

      # ok, in here decide the minimum distance from the beam centre to
      # the edge... which will depend on the size of the detector

      detector_width = header['size'][0] * header['pixel'][0]
      detector_height = header['size'][1] * header['pixel'][1]

      radius = min([beam[0], detector_width - beam[0],
                    beam[1], detector_height - beam[1]])

      theta = 0.5 * math.atan(radius / distance)

      resolution = wavelength / (2 * math.sin(theta))

      if not wave in wavelengths:
        wavelengths.append(wave)

      # cluster on power of sqrt(two), perhaps? also need to get the
      # batch ranges which they will end up as so that I can fetch
      # out the reflections I want from the scaled MTZ files.
      # When it comes to doing this it will also need to know where
      # those reflections may be found... - this is in sweep_information
      # [epoch]['batches'] so should be pretty handy to get to in here.

      found = False

      for rate in dose_rates:
        r = rate[1]
        if dr / r > math.sqrt(0.5) and dr / r < math.sqrt(2.0):
          # copy this for grouping
          found = True
          if (wave, rate[0]) in groups:
            groups[(wave, rate[0])].append((epoch, template))
            batch_groups[(wave, rate[0])].append(batches)
            if rate[0] in resolutions:
              resolutions[rate[0]] = max(resolutions[rate[0]],
                                         resolution)
            else:
              resolutions[rate[0]] = resolution


          else:
            groups[(wave, rate[0])] = [(epoch, template)]
            batch_groups[(wave, rate[0])] = [batches]
            if rate[0] in resolutions:
              resolutions[rate[0]] = max(resolutions[rate[0]],
                                         resolution)
            else:
              resolutions[rate[0]] = resolution

      if not found:
        rate = (len(dose_rates), dr)
        dose_rates.append(rate)
        groups[(wave, rate[0])] = [(epoch, template)]
        batch_groups[(wave, rate[0])] = [batches]

        if rate[0] in resolutions:
          resolutions[rate[0]] = max(resolutions[rate[0]],
                                     resolution)
        else:
          resolutions[rate[0]] = resolution

    # now work through the groups and print out the results, as well
    # as storing them for future reference...

    self._chef_analysis_groups = { }
    self._chef_analysis_times = { }
    self._chef_analysis_resolutions = { }

    for rate in dose_rates:
      self._chef_analysis_groups[rate[0]] = []
      self._chef_analysis_times[rate[0]] = rate[1]
      Debug.write('Dose group %d (%s s)' % rate)
      Debug.write('Resolution limit: %.2f' % resolutions[rate[0]])
      self._chef_analysis_resolutions[rate[0]] = resolutions[rate[0]]
      for wave in wavelengths:
        if (wave, rate[0]) in groups:
          for j in range(len(groups[(wave, rate[0])])):
            et = groups[(wave, rate[0])][j]
            batches = batch_groups[(wave, rate[0])][j]
            self._chef_analysis_groups[rate[0]].append(
                (wave, et[1], batches[0], batches[1]))
            Debug.write('%d %s %s (%d to %d)' % \
                        (et[0], wave, et[1],
                         batches[0], batches[1]))

    return

  def _scale_finish(self):

    # compute anomalous signals if anomalous

    if self.get_scaler_anomalous():
      for key in self._scalr_scaled_refl_files:
        f = self._scalr_scaled_refl_files[key]
        from iotbx import mtz
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

    # next transform to F's from I's etc.

    if len(self._scalr_scaled_refl_files.keys()) == 0:
      raise RuntimeError, 'no reflection files stored'

    if not Flags.get_small_molecule():

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

        Debug.write('%d absent reflections in %s removed' % \
                    (truncate.get_nabsent(), wavelength))

        b_factor = truncate.get_b_factor()

        # record the b factor somewhere (hopefully) useful...

        self._scalr_statistics[
            (self._scalr_pname, self._scalr_xname, wavelength)
            ]['Wilson B factor'] = [b_factor]

        # and record the reflection file..
        self._scalr_scaled_refl_files[wavelength] = hklout

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

    if Flags.get_small_molecule():
      return

    # finally add a FreeR column, and record the new merged reflection
    # file with the free column added.

    hklout = os.path.join(self.get_working_directory(),
                          '%s_%s_free_temp.mtz' % (self._scalr_pname,
                                                   self._scalr_xname))

    FileHandler.record_temporary_file(hklout)

    if self.get_scaler_freer_file():
      # e.g. via .xinfo file

      freein = self.get_scaler_freer_file()

      Debug.write('Copying FreeR_flag from %s' % freein)

      c = self._factory.Cad()
      c.set_freein(freein)
      c.add_hklin(self._scalr_scaled_reflection_files['mtz_merged'])
      c.set_hklout(hklout)
      c.copyfree()

    elif Flags.get_freer_file():
      # e.g. via -freer_file command line argument

      freein = Flags.get_freer_file()

      Debug.write('Copying FreeR_flag from %s' % freein)

      c = self._factory.Cad()
      c.set_freein(freein)
      c.add_hklin(self._scalr_scaled_reflection_files['mtz_merged'])
      c.set_hklout(hklout)
      c.copyfree()

    else:

      # default fraction of 0.05
      free_fraction = 0.05

      if Flags.get_free_fraction():
        free_fraction = Flags.get_free_fraction()
      elif Flags.get_free_total():
        ntot = Flags.get_free_total()

        # need to get a fraction, so...
        mtzdump = self._factory.Mtzdump()
        mtzdump.set_hklin(hklin)
        mtzdump.dump()
        nref = mtzdump.get_reflections()
        free_fraction = float(ntot) / float(nref)

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

    if Flags.get_free_fraction():
      free_fraction = Flags.get_free_fraction()
    elif Flags.get_free_total():
      ntot = Flags.get_free_total()

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

    from iotbx import mtz
    m = mtz.object(hklout)
    if not m.space_group().is_centric():
      from Toolkit.E4 import E4_mtz
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

    # next have a look for radiation damage... if more than one wavelength

    if len(self._scalr_scaled_refl_files.keys()) > 1 and \
           not Flags.get_small_molecule():
      crd = CCP4InterRadiationDamageDetector()

      crd.set_working_directory(self.get_working_directory())

      crd.set_hklin(hklout)

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

    return

  def _estimate_resolution_limit(self, hklin, batch_range=None):
    m = Merger()
    m.set_hklin(hklin)
    if Flags.get_rmerge():
      m.set_limit_rmerge(Flags.get_rmerge())
    if Flags.get_completeness():
      m.set_limit_completeness(Flags.get_completeness())
    if Flags.get_cc_half():
      m.set_limit_cc_half(Flags.get_cc_half())
    if Flags.get_isigma():
      m.set_limit_isigma(Flags.get_isigma())
    if Flags.get_misigma():
      m.set_limit_misigma(Flags.get_misigma())
    if Flags.get_small_molecule():
      m.set_nbins(20)
    if batch_range is not None:
      start, end = batch_range
      m.set_batch_range(start, end)
    m.run()

    if Flags.get_completeness():
      r_comp = m.get_resolution_completeness()
    else:
      r_comp = 0.0

    if Flags.get_cc_half():
      r_cc_half = m.get_resolution_cc_half()
    else:
      r_cc_half = 0.0

    if Flags.get_rmerge():
      r_rm = m.get_resolution_rmerge()
    else:
      r_rm = 0.0

    if Flags.get_isigma():
      r_uis = m.get_resolution_isigma()
    else:
      r_uis = 0.0

    if Flags.get_misigma():
      r_mis = m.get_resolution_misigma()
    else:
      r_mis = 0.0

    resolution = max([r_comp, r_rm, r_uis, r_mis, r_cc_half])

    return resolution
