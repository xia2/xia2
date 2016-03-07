#!/usr/bin/env python
# CCP4ScalerA.py
#   Copyright (C) 2011 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 07/OCT/2011
#
# An implementation of the Scaler interface using CCP4 programs and Aimless.
#

import os
import sys
import math
import copy

if not os.environ.has_key('XIA2_ROOT'):
  raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
  sys.path.append(os.environ['XIA2_ROOT'])

# the interface definition that this will conform to
# from Schema.Interfaces.Scaler import Scaler
from CommonScaler import CommonScaler as Scaler

from Wrappers.CCP4.CCP4Factory import CCP4Factory

from Handlers.Streams import Chatter, Debug, Journal
from Handlers.Files import FileHandler
from Handlers.Citations import Citations
from Handlers.Flags import Flags
from Handlers.Syminfo import Syminfo
from Handlers.Phil import PhilIndex

# jiffys
from lib.bits import is_mtz_file
from lib.bits import transpose_loggraph
from lib.SymmetryLib import sort_lattices

from CCP4ScalerHelpers import _prepare_pointless_hklin, \
     CCP4ScalerHelper, SweepInformationHandler, erzatz_resolution, \
     get_umat_bmat_lattice_symmetry_from_mtz

from Modules.AnalyseMyIntensities import AnalyseMyIntensities

class CCP4ScalerA(Scaler):
  '''An implementation of the Scaler interface using CCP4 programs.'''

  def __init__(self):
    super(CCP4ScalerA, self).__init__()

    self._sweep_handler = None

    self._scalr_scaled_refl_files = { }
    self._wavelengths_in_order = []

    # flags to keep track of the corrections we will be applying

    self._scale_model_b = None
    self._scale_model_secondary = None
    self._scale_model_tails = None

    # useful handles...!

    self._prepared_reflections = None

    self._reference = None

    self._factory = CCP4Factory()
    self._helper = CCP4ScalerHelper()

    return

  # overloaded from the Scaler interface... to plumb in the factory

  def to_dict(self):
    import json
    obj = super(CCP4ScalerA, self).to_dict()
    if self._sweep_handler is not None:
      obj['_sweep_handler'] = self._sweep_handler.to_dict()
    obj['_prepared_reflections'] = self._prepared_reflections
    return obj

  @classmethod
  def from_dict(cls, obj):
    import json
    return_obj = super(CCP4ScalerA, cls).from_dict(obj)
    if return_obj._sweep_handler is not None:
      return_obj._sweep_handler = SweepInformationHandler.from_dict(
        return_obj._sweep_handler)
    return_obj._prepared_reflections = obj['_prepared_reflections']
    return return_obj

  def set_working_directory(self, working_directory):
    self._working_directory = working_directory
    self._factory.set_working_directory(working_directory)
    self._helper.set_working_directory(working_directory)
    return

  # this is an overload from the factory - it returns Aimless wrapper set up
  # with the desired corrections

  def _updated_aimless(self):
    '''Generate a correctly configured Aimless...'''

    aimless = None

    if not self._scalr_corrections:
      aimless = self._factory.Aimless()
    else:

      aimless = self._factory.Aimless(
          partiality_correction = self._scalr_correct_partiality,
          absorption_correction = self._scalr_correct_absorption,
          decay_correction = self._scalr_correct_decay)

    if Flags.get_microcrystal():

      # fiddly little data sets - allow more rapid scaling...

      aimless.set_scaling_parameters('rotation', 2.0)
      if self._scalr_correct_decay:
        aimless.set_bfactor(bfactor=True, brotation = 2.0)

    if Flags.get_small_molecule():
      aimless.set_scaling_parameters('rotation', 15.0)
      aimless.set_bfactor(bfactor=False)

    aimless.set_surface_tie(PhilIndex.params.ccp4.aimless.surface_tie)
    aimless.set_surface_link(PhilIndex.params.ccp4.aimless.surface_link)

    return aimless

  def _pointless_indexer_jiffy(self, hklin, refiner):
    return self._helper.pointless_indexer_jiffy(hklin, refiner)

  def _assess_scaling_model(self, tails, bfactor, secondary):

    epochs = self._sweep_handler.get_epochs()

    sc_tst = self._updated_aimless()
    sc_tst.set_cycles(5)

    sc_tst.set_hklin(self._prepared_reflections)
    sc.set_intensities(PhilIndex.params.ccp4.aimless.intensities)
    sc_tst.set_hklout('temp.mtz')

    sc_tst.set_tails(tails = tails)
    sc_tst.set_bfactor(bfactor = bfactor)

    resolutions = self._resolution_limit_estimates

    if secondary:
      sc_tst.set_scaling_parameters(
          'rotation', secondary = Flags.get_aimless_secondary())
    else:
      sc_tst.set_scaling_parameters('rotation', secondary = 0)

    for epoch in epochs:

      si = self._sweep_handler.get_sweep_information(epoch)

      start, end = si.get_batch_range()

      resolution = resolutions[(start, end)]

      pname, xname, dname = si.get_project_info()
      sname = si.get_sweep_name()

      sc_tst.add_run(start, end, exclude = False,
                     resolution = resolution, name = sname)

      if self.get_scaler_anomalous():
        sc_tst.set_anomalous()

    if True:
      # try:
      sc_tst.scale()
    else:
      # except RuntimeError, e:
      if 'scaling not converged' in str(e):
        return -1, -1
      if 'negative scales' in str(e):
        return -1, -1
      raise e

    data_tst = sc_tst.get_summary()

    # compute average Rmerge, number of cycles to converge - these are
    # what will form the basis of the comparison

    target = {'overall':0, 'low':1, 'high':2}

    rmerges_tst = [data_tst[k]['Rmerge'][target[
        Flags.get_rmerge_target()]] for k in data_tst]
    rmerge_tst = sum(rmerges_tst) / len(rmerges_tst)

    return rmerge_tst

  def _determine_best_scale_model_8way(self):
    '''Determine the best set of corrections to apply to the data,
    testing all eight permutations.'''

    # if we have already defined the best scaling model just return

    if self._scalr_corrections:
      return

    # or see if we set one on the command line...

    if Flags.get_scale_model():
      self._scalr_correct_absorption = Flags.get_scale_model_absorption()
      self._scalr_correct_partiality = Flags.get_scale_model_partiality()
      self._scalr_correct_decay = Flags.get_scale_model_decay()

      self._scalr_corrections = True

      return

    Debug.write('Optimising scaling corrections...')

    rmerge_def = self._assess_scaling_model(
        tails = False, bfactor = False, secondary = False)

    results = { }

    consider = []

    log_results = []

    for partiality in True, False:
      for decay in True, False:
        for absorption in True, False:
          if partiality or decay or absorption:
            r = self._assess_scaling_model(
                tails = partiality, bfactor = decay,
                secondary = absorption)
          else:
            r = rmerge_def

          results[(partiality, decay, absorption)] = r

          log_results.append((partiality, decay, absorption, r))

          consider.append(
              (r, partiality, decay, absorption))


    Debug.write('. Tails Decay  Abs  R(%s)' % \
                Flags.get_rmerge_target())

    for result in log_results:
      Debug.write('. %5s %5s %5s %.3f' % result)

    consider.sort()
    rmerge, partiality, decay, absorption = consider[0]

    if absorption:
      Debug.write('Absorption correction: on')
    else:
      Debug.write('Absorption correction: off')

    if partiality:
      Debug.write('Partiality correction: on')
    else:
      Debug.write('Partiality correction: off')

    if decay:
      Debug.write('Decay correction: on')
    else:
      Debug.write('Decay correction: off')

    self._scalr_correct_absorption = absorption
    self._scalr_correct_partiality = partiality
    self._scalr_correct_decay = decay

    self._scalr_corrections = True

    return

  def _scale_prepare(self):
    '''Perform all of the preparation required to deliver the scaled
    data. This should sort together the reflection files, ensure that
    they are correctly indexed (via pointless) and generally tidy
    things up.'''

    # acknowledge all of the programs we are about to use...

    Citations.cite('pointless')
    Citations.cite('aimless')
    Citations.cite('ccp4')

    # ---------- GATHER ----------

    self._sweep_handler = SweepInformationHandler(self._scalr_integraters)

    Journal.block(
        'gathering', self.get_scaler_xcrystal().get_name(), 'CCP4',
        {'working directory':self.get_working_directory()})

    for epoch in self._sweep_handler.get_epochs():
      si = self._sweep_handler.get_sweep_information(epoch)
      pname, xname, dname = si.get_project_info()
      sname = si.get_sweep_name()

      exclude_sweep = False

      for sweep in PhilIndex.params.xia2.settings.sweep:
        if sweep.id == sname and sweep.exclude:
          exclude_sweep = True
          break

      if exclude_sweep:
        self._sweep_handler.remove_epoch(epoch)
        Debug.write('Excluding sweep %s' %sname)
      else:
        Journal.entry({'adding data from':'%s/%s/%s' % \
                       (xname, dname, sname)})

    # gather data for all images which belonged to the parent
    # crystal - allowing for the fact that things could go wrong
    # e.g. epoch information not available, exposure times not in
    # headers etc...

    for e in self._sweep_handler.get_epochs():
      si = self._sweep_handler.get_sweep_information(e)
      assert is_mtz_file(si.get_reflections())

    p, x = self._sweep_handler.get_project_info()
    self._scalr_pname = p
    self._scalr_xname = x

    # verify that the lattices are consistent, calling eliminate if
    # they are not N.B. there could be corner cases here

    need_to_return = False

    multi_sweep_indexing = \
      PhilIndex.params.xia2.settings.developmental.multi_sweep_indexing


    if len(self._sweep_handler.get_epochs()) > 1:

      if multi_sweep_indexing and not self._scalr_input_pointgroup:
        pointless_hklins = []

        max_batches = 0
        for epoch in self._sweep_handler.get_epochs():
          si = self._sweep_handler.get_sweep_information(epoch)
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

        from lib.bits import nifty_power_of_ten
        Debug.write('Biggest sweep has %d batches' % max_batches)
        max_batches = nifty_power_of_ten(max_batches)

        counter = 0

        for epoch in self._sweep_handler.get_epochs():
          si = self._sweep_handler.get_sweep_information(epoch)
          hklin = si.get_reflections()
          integrater = si.get_integrater()
          refiner = integrater.get_integrater_refiner()

          hklin = self._prepare_pointless_hklin(
            hklin, si.get_integrater().get_phi_width())

          rb = self._factory.Rebatch()

          hklout = os.path.join(self.get_working_directory(),
                                '%s_%s_%s_%s_prepointless.mtz' % \
                                (pname, xname, dname, si.get_sweep_name()))

          # we will want to delete this one exit
          FileHandler.record_temporary_file(hklout)

          first_batch = min(si.get_batches())
          si.set_batch_offset(counter * max_batches - first_batch + 1)

          rb.set_hklin(hklin)
          rb.set_first_batch(counter * max_batches + 1)
          rb.set_project_info(pname, xname, dname)
          rb.set_hklout(hklout)

          new_batches = rb.rebatch()

          pointless_hklins.append(hklout)

          # update the counter & recycle
          counter += 1

        s = self._factory.Sortmtz()

        pointless_hklin = os.path.join(self.get_working_directory(),
                              '%s_%s_prepointless_sorted.mtz' % \
                              (self._scalr_pname, self._scalr_xname))

        s.set_hklout(pointless_hklin)

        for hklin in pointless_hklins:
          s.add_hklin(hklin)

        s.sort()

        pointgroup, reindex_op, ntr, pt = \
                    self._pointless_indexer_jiffy(
            pointless_hklin, refiner)

        Debug.write('X1698: %s: %s' % (pointgroup, reindex_op))

        lattices = [Syminfo.get_lattice(pointgroup)]

        for epoch in self._sweep_handler.get_epochs():
          si = self._sweep_handler.get_sweep_information(epoch)
          intgr = si.get_integrater()
          hklin = si.get_reflections()
          refiner = intgr.get_integrater_refiner()

          if ntr:
            intgr.integrater_reset_reindex_operator()
            need_to_return = True

      else:
        lattices = []

        for epoch in self._sweep_handler.get_epochs():

          si = self._sweep_handler.get_sweep_information(epoch)
          intgr = si.get_integrater()
          hklin = si.get_reflections()
          refiner = intgr.get_integrater_refiner()

          if self._scalr_input_pointgroup:
            pointgroup = self._scalr_input_pointgroup
            reindex_op = 'h,k,l'
            ntr = False

          else:
            pointless_hklin = self._prepare_pointless_hklin(
              hklin, si.get_integrater().get_phi_width())

            pointgroup, reindex_op, ntr, pt = \
                        self._pointless_indexer_jiffy(
                pointless_hklin, refiner)

            Debug.write('X1698: %s: %s' % (pointgroup, reindex_op))

          lattice = Syminfo.get_lattice(pointgroup)

          if not lattice in lattices:
            lattices.append(lattice)

          if ntr:

            intgr.integrater_reset_reindex_operator()
            need_to_return = True

      if len(lattices) > 1:

        # why not using pointless indexer jiffy??!

        correct_lattice = sort_lattices(lattices)[0]

        Chatter.write('Correct lattice asserted to be %s' % \
                      correct_lattice)

        # transfer this information back to the indexers
        for epoch in self._sweep_handler.get_epochs():

          si = self._sweep_handler.get_sweep_information(epoch)
          refiner = si.get_integrater().get_integrater_refiner()
          sname = si.get_sweep_name()

          state = refiner.set_refiner_asserted_lattice(
              correct_lattice)

          if state == refiner.LATTICE_CORRECT:
            Chatter.write('Lattice %s ok for sweep %s' % \
                          (correct_lattice, sname))
          elif state == refiner.LATTICE_IMPOSSIBLE:
            raise RuntimeError, 'Lattice %s impossible for %s' \
                  % (correct_lattice, sname)
          elif state == refiner.LATTICE_POSSIBLE:
            Chatter.write('Lattice %s assigned for sweep %s' % \
                          (correct_lattice, sname))
            need_to_return = True

    # if one or more of them was not in the lowest lattice,
    # need to return here to allow reprocessing

    if need_to_return:
      self.set_scaler_done(False)
      self.set_scaler_prepare_done(False)
      return

    # ---------- REINDEX ALL DATA TO CORRECT POINTGROUP ----------

    # all should share the same pointgroup, unless twinned... in which
    # case force them to be...

    pointgroups = { }
    reindex_ops = { }
    probably_twinned = False

    need_to_return = False

    multi_sweep_indexing = \
      PhilIndex.params.xia2.settings.developmental.multi_sweep_indexing

    if multi_sweep_indexing and not self._scalr_input_pointgroup:
      pointless_hklins = []

      max_batches = 0
      for epoch in self._sweep_handler.get_epochs():
        si = self._sweep_handler.get_sweep_information(epoch)
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

      from lib.bits import nifty_power_of_ten
      Debug.write('Biggest sweep has %d batches' % max_batches)
      max_batches = nifty_power_of_ten(max_batches)

      counter = 0

      for epoch in self._sweep_handler.get_epochs():
        si = self._sweep_handler.get_sweep_information(epoch)
        hklin = si.get_reflections()
        integrater = si.get_integrater()
        refiner = integrater.get_integrater_refiner()

        hklin = self._prepare_pointless_hklin(
            hklin, si.get_integrater().get_phi_width())

        rb = self._factory.Rebatch()

        hklout = os.path.join(self.get_working_directory(),
                              '%s_%s_%s_%s_prepointless.mtz' % \
                              (pname, xname, dname, si.get_sweep_name()))

        # we will want to delete this one exit
        FileHandler.record_temporary_file(hklout)

        first_batch = min(si.get_batches())
        si.set_batch_offset(counter * max_batches - first_batch + 1)

        rb.set_hklin(hklin)
        rb.set_first_batch(counter * max_batches + 1)
        rb.set_project_info(pname, xname, dname)
        rb.set_hklout(hklout)

        new_batches = rb.rebatch()

        pointless_hklins.append(hklout)

        # update the counter & recycle
        counter += 1

      s = self._factory.Sortmtz()

      pointless_hklin = os.path.join(self.get_working_directory(),
                            '%s_%s_prepointless_sorted.mtz' % \
                            (self._scalr_pname, self._scalr_xname))

      s.set_hklout(pointless_hklin)

      for hklin in pointless_hklins:
        s.add_hklin(hklin)

      s.sort()

      pointgroup, reindex_op, ntr, pt = \
                  self._pointless_indexer_jiffy(
          pointless_hklin, refiner)

      for epoch in self._sweep_handler.get_epochs():
        pointgroups[epoch] = pointgroup
        reindex_ops[epoch] = reindex_op

    else:
      for epoch in self._sweep_handler.get_epochs():
        si = self._sweep_handler.get_sweep_information(epoch)

        hklin = si.get_reflections()
        #hklout = os.path.join(
            #self.get_working_directory(),
            #os.path.split(hklin)[-1].replace('.mtz', '_rdx.mtz'))

        #FileHandler.record_temporary_file(hklout)

        integrater = si.get_integrater()
        refiner = integrater.get_integrater_refiner()

        if self._scalr_input_pointgroup:
          Debug.write('Using input pointgroup: %s' % \
                      self._scalr_input_pointgroup)
          pointgroup = self._scalr_input_pointgroup
          reindex_op = 'h,k,l'
          pt = False

        else:

          pointless_hklin = self._prepare_pointless_hklin(
              hklin, si.get_integrater().get_phi_width())

          pointgroup, reindex_op, ntr, pt = \
                      self._pointless_indexer_jiffy(
              pointless_hklin, refiner)

          Debug.write('X1698: %s: %s' % (pointgroup, reindex_op))

          if ntr:

            integrater.integrater_reset_reindex_operator()
            need_to_return = True

        if pt and not probably_twinned:
          probably_twinned = True

        Debug.write('Pointgroup: %s (%s)' % (pointgroup, reindex_op))

        pointgroups[epoch] = pointgroup
        reindex_ops[epoch] = reindex_op

    overall_pointgroup = None

    pointgroup_set = set([pointgroups[e] for e in pointgroups])

    if len(pointgroup_set) > 1 and \
       not probably_twinned:
      raise RuntimeError, 'non uniform pointgroups'

    if len(pointgroup_set) > 1:
      Debug.write('Probably twinned, pointgroups: %s' % \
                  ' '.join([p.replace(' ', '') for p in \
                            list(pointgroup_set)]))
      numbers = [Syminfo.spacegroup_name_to_number(s) for s in \
                 pointgroup_set]
      overall_pointgroup = Syminfo.spacegroup_number_to_name(
          min(numbers))
      self._scalr_input_pointgroup = overall_pointgroup

      Chatter.write('Twinning detected, assume pointgroup %s' % \
                    overall_pointgroup)

      need_to_return = True

    else:
      overall_pointgroup = pointgroup_set.pop()

    for epoch in self._sweep_handler.get_epochs():
      si = self._sweep_handler.get_sweep_information(epoch)

      integrater = si.get_integrater()

      integrater.set_integrater_spacegroup_number(
          Syminfo.spacegroup_name_to_number(overall_pointgroup))
      integrater.set_integrater_reindex_operator(
          reindex_ops[epoch], reason='setting point group')
      # This will give us the reflections in the correct point group
      si.set_reflections(integrater.get_integrater_intensities())

    if need_to_return:
      self.set_scaler_done(False)
      self.set_scaler_prepare_done(False)
      return

    # in here now optinally work through the data files which should be
    # indexed with a consistent point group, and transform the orientation
    # matrices by the lattice symmetry operations (if possible) to get a
    # consistent definition of U matrix modulo fixed rotations

    if PhilIndex.params.xia2.settings.unify_setting:

      from scitbx.matrix import sqr
      reference_U = None
      i3 = sqr((1, 0, 0, 0, 1, 0, 0, 0, 1))

      for epoch in self._sweep_handler.get_epochs():
        si = self._sweep_handler.get_sweep_information(epoch)
        intgr = si.get_integrater()
        fixed = sqr(intgr.get_goniometer().get_fixed_rotation())
        u, b, s = get_umat_bmat_lattice_symmetry_from_mtz(si.get_reflections())
        U = fixed.inverse() * sqr(u).transpose()
        B = sqr(b)

        if reference_U is None:
          reference_U = U
          continue

        results = []
        for op in s.all_ops():
          R = B * sqr(op.r().as_double()).transpose() * B.inverse()
          nearly_i3 = (U * R).inverse() * reference_U
          score = sum([abs(_n - _i) for (_n, _i) in zip(nearly_i3, i3)])
          results.append((score, op.r().as_hkl(), op))

        results.sort()
        best = results[0]
        Debug.write('Best reindex: %s %.3f' % (best[1], best[0]))
        intgr.set_integrater_reindex_operator(best[2].r().inverse().as_hkl(),
                                              reason='unifying [U] setting')
        si.set_reflections(intgr.get_integrater_intensities())

        # recalculate to verify
        u, b, s = get_umat_bmat_lattice_symmetry_from_mtz(si.get_reflections())
        U = fixed.inverse() * sqr(u).transpose()
        Debug.write('New reindex: %s' % (U.inverse() * reference_U))

        # FIXME I should probably raise an exception at this stage if this
        # is not about I3...

    if self.get_scaler_reference_reflection_file():
      self._reference = self.get_scaler_reference_reflection_file()
      Debug.write('Using HKLREF %s' % self._reference)

    elif Flags.get_reference_reflection_file():
      self._reference = Flags.get_reference_reflection_file()
      Debug.write('Using HKLREF %s' % self._reference)

    params = PhilIndex.params
    use_brehm_diederichs = params.xia2.settings.use_brehm_diederichs
    if len(self._sweep_handler.get_epochs()) > 1 and use_brehm_diederichs:

      brehm_diederichs_files_in = []
      for epoch in self._sweep_handler.get_epochs():

        si = self._sweep_handler.get_sweep_information(epoch)
        hklin = si.get_reflections()
        brehm_diederichs_files_in.append(hklin)

      # now run cctbx.brehm_diederichs to figure out the indexing hand for
      # each sweep
      from Wrappers.Cctbx.BrehmDiederichs import BrehmDiederichs
      from lib.bits import auto_logfiler
      brehm_diederichs = BrehmDiederichs()
      brehm_diederichs.set_working_directory(self.get_working_directory())
      auto_logfiler(brehm_diederichs)
      brehm_diederichs.set_input_filenames(brehm_diederichs_files_in)
      # 1 or 3? 1 seems to work better?
      brehm_diederichs.set_asymmetric(1)
      brehm_diederichs.run()
      reindexing_dict = brehm_diederichs.get_reindexing_dict()

      for epoch in self._sweep_handler.get_epochs():

        si = self._sweep_handler.get_sweep_information(epoch)
        intgr = si.get_integrater()
        hklin = si.get_reflections()

        reindex_op = reindexing_dict.get(os.path.abspath(hklin))
        assert reindex_op is not None

        if 1 or reindex_op != 'h,k,l':
          # apply the reindexing operator
          intgr.set_integrater_reindex_operator(
            reindex_op, reason='match reference')
          si.set_reflections(intgr.get_integrater_intensities())

    elif len(self._sweep_handler.get_epochs()) > 1 and \
           not self._reference:

      first = self._sweep_handler.get_epochs()[0]
      si = self._sweep_handler.get_sweep_information(first)
      self._reference = si.get_reflections()

    if self._reference:

      md = self._factory.Mtzdump()
      md.set_hklin(self._reference)
      md.dump()

      if md.get_batches() and False:
        raise RuntimeError, 'reference reflection file %s unmerged' % \
              self._reference

      datasets = md.get_datasets()

      if len(datasets) > 1 and False:
        raise RuntimeError, 'more than one dataset in %s' % \
              self._reference

      # then get the unit cell, lattice etc.

      reference_lattice = Syminfo.get_lattice(md.get_spacegroup())
      reference_cell = md.get_dataset_info(datasets[0])['cell']

      # then compute the pointgroup from this...

      # ---------- REINDEX TO CORRECT (REFERENCE) SETTING ----------

      for epoch in self._sweep_handler.get_epochs():
        pl = self._factory.Pointless()

        si = self._sweep_handler.get_sweep_information(epoch)
        hklin = si.get_reflections()

        pl.set_hklin(self._prepare_pointless_hklin(
            hklin, si.get_integrater().get_phi_width()))

        hklout = os.path.join(
            self.get_working_directory(),
            '%s_rdx2.mtz' % os.path.split(hklin)[-1][:-4])

        # we will want to delete this one exit
        FileHandler.record_temporary_file(hklout)

        # now set the initial reflection set as a reference...

        pl.set_hklref(self._reference)

        # write a pointless log file...
        pl.decide_pointgroup()

        Debug.write('Reindexing analysis of %s' % pl.get_hklin())

        pointgroup = pl.get_pointgroup()
        reindex_op = pl.get_reindex_operator()

        Debug.write('Operator: %s' % reindex_op)

        # apply this...

        integrater = si.get_integrater()

        integrater.set_integrater_reindex_operator(reindex_op,
                                                   reason='match reference')
        integrater.set_integrater_spacegroup_number(
            Syminfo.spacegroup_name_to_number(pointgroup))
        si.set_reflections(integrater.get_integrater_intensities())

        md = self._factory.Mtzdump()
        md.set_hklin(si.get_reflections())
        md.dump()

        datasets = md.get_datasets()

        if len(datasets) > 1:
          raise RuntimeError, 'more than one dataset in %s' % \
                si.get_reflections()

        # then get the unit cell, lattice etc.

        lattice = Syminfo.get_lattice(md.get_spacegroup())
        cell = md.get_dataset_info(datasets[0])['cell']

        if lattice != reference_lattice:
          raise RuntimeError, 'lattices differ in %s and %s' % \
                (self._reference, si.get_reflections())

        for j in range(6):
          if math.fabs((cell[j] - reference_cell[j]) /
                       reference_cell[j]) > 0.1:
            raise RuntimeError, \
                  'unit cell parameters differ in %s and %s' % \
                  (self._reference, si.get_reflections())

    # ---------- SORT TOGETHER DATA ----------

    self._sort_together_data_ccp4()

    self._scalr_resolution_limits = { }

    # store central resolution limit estimates

    batch_ranges = [self._sweep_handler.get_sweep_information(
        epoch).get_batch_range() for epoch in
                    self._sweep_handler.get_epochs()]

    self._resolution_limit_estimates = erzatz_resolution(
        self._prepared_reflections, batch_ranges)


    return

  def _scale(self):
    '''Perform all of the operations required to deliver the scaled
    data.'''

    epochs = self._sweep_handler.get_epochs()

    if PhilIndex.params.xia2.settings.optimize_scaling:
      self._determine_best_scale_model_8way()
    else:
      self._scalr_corrections = True
      self._scalr_correct_absorption = True
      self._scalr_correct_partiality = False
      self._scalr_correct_decay = True

    if self._scalr_corrections:
      Journal.block(
          'scaling', self.get_scaler_xcrystal().get_name(), 'CCP4',
          {'scaling model':'automatic',
           'absorption':self._scalr_correct_absorption,
           'tails':self._scalr_correct_partiality,
           'decay':self._scalr_correct_decay
           })

    else:
      Journal.block(
          'scaling', self.get_scaler_xcrystal().get_name(), 'CCP4',
          {'scaling model':'default'})

    sc = self._updated_aimless()
    sc.set_hklin(self._prepared_reflections)
    sc.set_intensities(PhilIndex.params.ccp4.aimless.intensities)

    sc.set_chef_unmerged(True)

    sc.set_new_scales_file('%s.scales' % self._scalr_xname)

    user_resolution_limits = { }

    for epoch in epochs:

      si = self._sweep_handler.get_sweep_information(epoch)
      pname, xname, dname = si.get_project_info()
      sname = si.get_sweep_name()
      intgr = si.get_integrater()

      if intgr.get_integrater_user_resolution():
        dmin = intgr.get_integrater_high_resolution()

        if not user_resolution_limits.has_key((dname, sname)):
          user_resolution_limits[(dname, sname)] = dmin
        elif dmin < user_resolution_limits[(dname, sname)]:
          user_resolution_limits[(dname, sname)] = dmin

      start, end = si.get_batch_range()

      if (dname, sname) in self._scalr_resolution_limits:
        resolution = self._scalr_resolution_limits[(dname, sname)]
        sc.add_run(start, end, exclude = False,
                   resolution = resolution, name = sname)
      else:
        sc.add_run(start, end, name = sname)

    sc.set_hklout(os.path.join(self.get_working_directory(),
                               '%s_%s_scaled_test.mtz' % \
                               (self._scalr_pname, self._scalr_xname)))

    if self.get_scaler_anomalous():
      sc.set_anomalous()

    # what follows, sucks

    if Flags.get_failover():

      try:
        sc.scale()
      except RuntimeError, e:

        es = str(e)

        if 'bad batch' in es or \
               'negative scales run' in es or \
               'no observations' in es:

          # first ID the sweep from the batch no

          batch = int(es.split()[-1])
          epoch = self._identify_sweep_epoch(batch)
          sweep = self._scalr_integraters[
              epoch].get_integrater_sweep()

          # then remove it from my parent xcrystal

          self.get_scaler_xcrystal().remove_sweep(sweep)

          # then remove it from the scaler list of intergraters
          # - this should really be a scaler interface method

          del(self._scalr_integraters[epoch])

          # then tell the user what is happening

          Chatter.write(
              'Sweep %s gave negative scales - removing' % \
              sweep.get_name())

          # then reset the prepare, do, finish flags

          self.set_scaler_prepare_done(False)
          self.set_scaler_done(False)
          self.set_scaler_finish_done(False)

          # and return

          return

        else:

          raise e


    else:
      sc.scale()

    # then gather up all of the resulting reflection files
    # and convert them into the required formats (.sca, .mtz.)

    data = sc.get_summary()

    loggraph = sc.parse_ccp4_loggraph()

    resolution_info = { }

    reflection_files = sc.get_scaled_reflection_files()

    for dataset in reflection_files:
      FileHandler.record_temporary_file(reflection_files[dataset])

    for key in loggraph:
      if 'Analysis against resolution' in key:
        dataset = key.split(',')[-1].strip()
        resolution_info[dataset] = transpose_loggraph(
            loggraph[key])

    highest_resolution = 100.0

    # check in here that there is actually some data to scale..!

    if len(resolution_info) == 0:
      raise RuntimeError, 'no resolution info'

    for epoch in epochs:

      si = self._sweep_handler.get_sweep_information(epoch)
      pname, xname, dname = si.get_project_info()
      sname = si.get_sweep_name()
      intgr = si.get_integrater()
      start, end = si.get_batch_range()

      if (dname, sname) in user_resolution_limits:
        resolution = user_resolution_limits[(dname, sname)]
        self._scalr_resolution_limits[(dname, sname)] = resolution
        if resolution < highest_resolution:
          highest_resolution = resolution
        Chatter.write('Resolution limit for %s: %5.2f' % \
                      (dname, resolution))
        continue

      hklin = sc.get_unmerged_reflection_file()
      resolution = self._estimate_resolution_limit(
        hklin, batch_range=(start, end))
      Debug.write('Resolution for sweep %s: %.2f' % \
                  (sname, resolution))

      if not (dname, sname) in self._scalr_resolution_limits:
        self._scalr_resolution_limits[(dname, sname)] = resolution
        self.set_scaler_done(False)

      if resolution < highest_resolution:
        highest_resolution = resolution

      Chatter.write('Resolution limit for %s/%s: %5.2f' % \
                    (dname, sname,
                     self._scalr_resolution_limits[(dname, sname)]))

    self._scalr_highest_resolution = highest_resolution

    Debug.write('Scaler highest resolution set to %5.2f' % \
                highest_resolution)

    if not self.get_scaler_done():
      Debug.write('Returning as scaling not finished...')
      return

    batch_info = { }

    for key in loggraph:
      if 'Analysis against Batch' in key:
        dataset = key.split(',')[-1].strip()
        batch_info[dataset] = transpose_loggraph(
            loggraph[key])

    sc = self._updated_aimless()

    FileHandler.record_log_file('%s %s aimless' % (self._scalr_pname,
                                                   self._scalr_xname),
                                sc.get_log_file())

    highest_resolution = 100.0

    sc.set_hklin(self._prepared_reflections)
    sc.set_intensities(PhilIndex.params.ccp4.aimless.intensities)
    sc.set_new_scales_file('%s_final.scales' % self._scalr_xname)

    for epoch in epochs:

      si = self._sweep_handler.get_sweep_information(epoch)
      pname, xname, dname = si.get_project_info()
      sname = si.get_sweep_name()
      start, end = si.get_batch_range()

      resolution_limit = self._scalr_resolution_limits[(dname, sname)]

      if resolution_limit < highest_resolution:
        highest_resolution = resolution_limit

      sc.add_run(start, end, exclude = False,
                 resolution = resolution_limit, name = xname)

    sc.set_hklout(os.path.join(self.get_working_directory(),
                               '%s_%s_scaled.mtz' % \
                               (self._scalr_pname, self._scalr_xname)))

    if self.get_scaler_anomalous():
      sc.set_anomalous()

    sc.scale()

    FileHandler.record_xml_file('%s %s aimless xml' % (self._scalr_pname,
                                                       self._scalr_xname),
                                sc.get_xmlout())

    data = sc.get_summary()
    scales_file = sc.get_new_scales_file()
    loggraph = sc.parse_ccp4_loggraph()

    standard_deviation_info = { }

    for key in loggraph:
      if 'standard deviation v. Intensity' in key:
        dataset = key.split(',')[-1].strip()
        standard_deviation_info[dataset] = transpose_loggraph(
            loggraph[key])

    resolution_info = { }

    for key in loggraph:
      if 'Analysis against resolution' in key:
        dataset = key.split(',')[-1].strip()
        resolution_info[dataset] = transpose_loggraph(
            loggraph[key])

    batch_info = { }

    for key in loggraph:
      if 'Analysis against Batch' in key:
        dataset = key.split(',')[-1].strip()
        batch_info[dataset] = transpose_loggraph(
            loggraph[key])

    # finally put all of the results "somewhere useful"

    self._scalr_statistics = data

    self._scalr_scaled_refl_files = copy.deepcopy(
        sc.get_scaled_reflection_files())

    self._scalr_scaled_reflection_files = { }
    self._scalr_scaled_reflection_files['sca'] = { }

    for key in self._scalr_scaled_refl_files:
      f = self._scalr_scaled_refl_files[key]
      scaout = '%s.sca' % f[:-4]

      m2v = self._factory.Mtz2various()
      m2v.set_hklin(f)
      m2v.set_hklout(scaout)
      m2v.convert()

      self._scalr_scaled_reflection_files['sca'][key] = scaout

      FileHandler.record_data_file(scaout)

    sc = self._updated_aimless()
    sc.set_hklin(self._prepared_reflections)
    sc.set_intensities(PhilIndex.params.ccp4.aimless.intensities)
    sc.set_scales_file(scales_file)

    self._wavelengths_in_order = []

    for epoch in epochs:
      si = self._sweep_handler.get_sweep_information(epoch)
      pname, xname, dname = si.get_project_info()
      sname = si.get_sweep_name()
      start, end = si.get_batch_range()

      resolution_limit = self._scalr_resolution_limits[(dname, sname)]

      sc.add_run(start, end, exclude = False,
                 resolution = resolution_limit, name = sname)

      if not dname in self._wavelengths_in_order:
        self._wavelengths_in_order.append(dname)

    sc.set_hklout(os.path.join(self.get_working_directory(),
                               '%s_%s_scaled.mtz' % \
                               (self._scalr_pname,
                                self._scalr_xname)))

    sc.set_scalepack()

    if self.get_scaler_anomalous():
      sc.set_anomalous()
    sc.scale()

    self._scalr_scaled_reflection_files['sca_unmerged'] = { }
    self._scalr_scaled_reflection_files['mtz_unmerged'] = { }
    for key in self._scalr_scaled_refl_files:
      f = self._scalr_scaled_refl_files[key]
      scalepack = os.path.join(os.path.split(f)[0],
                               os.path.split(f)[1].replace(
          '_scaled', '_scaled_unmerged').replace('.mtz', '.sca'))
      self._scalr_scaled_reflection_files['sca_unmerged'][key] = scalepack
      FileHandler.record_data_file(scalepack)
      mtz_unmerged = os.path.splitext(scalepack)[0] + '.mtz'
      self._scalr_scaled_reflection_files['mtz_unmerged'][key] = mtz_unmerged
      FileHandler.record_data_file(mtz_unmerged)

    if PhilIndex.params.xia2.settings.merging_statistics.source == 'cctbx':
      for key in self._scalr_scaled_refl_files:
        stats = self._compute_scaler_statistics(
          self._scalr_scaled_reflection_files['mtz_unmerged'][key])
        self._scalr_statistics[
          (self._scalr_pname, self._scalr_xname, key)] = stats

    sc = self._updated_aimless()
    sc.set_hklin(self._prepared_reflections)
    sc.set_intensities(PhilIndex.params.ccp4.aimless.intensities)
    sc.set_scales_file(scales_file)

    self._wavelengths_in_order = []

    for epoch in epochs:

      si = self._sweep_handler.get_sweep_information(epoch)
      pname, xname, dname = si.get_project_info()
      sname = si.get_sweep_name()
      start, end = si.get_batch_range()

      resolution_limit = self._scalr_resolution_limits[(dname, sname)]

      sc.add_run(start, end, exclude = False,
                 resolution = resolution_limit, name = sname)

      if not dname in self._wavelengths_in_order:
        self._wavelengths_in_order.append(dname)

    sc.set_hklout(os.path.join(self.get_working_directory(),
                               '%s_%s_chef.mtz' % \
                               (self._scalr_pname,
                                self._scalr_xname)))

    sc.set_chef_unmerged(True)

    if self.get_scaler_anomalous():
      sc.set_anomalous()
    sc.scale()

    # FIXME this could be brought in-house

    ami = AnalyseMyIntensities()
    ami.set_working_directory(self.get_working_directory())

    average_unit_cell, ignore_sg = ami.compute_average_cell(
        [self._scalr_scaled_refl_files[key] for key in
         self._scalr_scaled_refl_files])

    Debug.write('Computed average unit cell (will use in all files)')
    Debug.write('%6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % \
                average_unit_cell)

    self._scalr_cell = average_unit_cell

    return

  def _identify_sweep_epoch(self, batch):
    '''Identify the sweep epoch a given batch came from - N.B.
    this assumes that the data are rebatched, will raise an exception if
    more than one candidate is present.'''

    epochs = []

    for epoch in self._sweep_handler.get_epochs():
      si = self._sweep_handler.get_sweep_information(epoch)
      if batch in si.get_batches():
        epochs.append(epoch)

    if len(epochs) > 1:
      raise RuntimeError, 'batch %d found in multiple sweeps' % batch

    return epochs[0]

  def _prepare_pointless_hklin(self, hklin, phi_width):
    return _prepare_pointless_hklin(self.get_working_directory(),
                                    hklin, phi_width)

  def get_batch_to_dose(self):
    batch_to_dose = {}
    epoch_to_dose = {}
    for xsample in self.get_scaler_xcrystal()._samples.values():
      epoch_to_dose.update(xsample.get_epoch_to_dose())
    for si in self._sweep_handler._sweep_information.values():
      batch_offset = si.get_batch_offset()
      for b in range(si.get_batches()[0], si.get_batches()[1]+1):
        if len(epoch_to_dose):
          batch_to_dose[b] = epoch_to_dose[si._image_to_epoch[b-batch_offset]]
        else:
          # backwards compatibility 2015-12-11
          batch_to_dose[b] = b
    return batch_to_dose
