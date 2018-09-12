#An implementation of the scaler interface for dials.scale

from __future__ import absolute_import, division, print_function
import os
import copy as copy

from xia2.Handlers.CIF import CIF, mmCIF
from xia2.Handlers.Citations import Citations
from xia2.Handlers.Files import FileHandler
from xia2.lib.bits import auto_logfiler
from xia2.Handlers.Phil import PhilIndex
from xia2.lib.SymmetryLib import sort_lattices
from xia2.Handlers.Streams import Chatter, Debug, Journal
from xia2.Modules.Scaler.CommonScaler import CommonScaler as Scaler
from xia2.Wrappers.Dials.Scale import DialsScale
from xia2.Modules.AnalyseMyIntensities import AnalyseMyIntensities
from xia2.Wrappers.CCP4.CCP4Factory import CCP4Factory
from xia2.Modules.Scaler.CCP4ScalerHelpers import SweepInformationHandler
from xia2.Wrappers.Dials.Symmetry import DialsSymmetry
from xia2.Wrappers.Dials.Reindex import Reindex as DialsReindex
from xia2.Handlers.Syminfo import Syminfo

def clean_reindex_operator(reindex_operator):
  return reindex_operator.replace('[', '').replace(']', '')

class DialsScaler(Scaler):

  def __init__(self):
    super(DialsScaler, self).__init__()

    self._scalr_scaled_refl_files = {}
    self._scalr_statistics = {}
    self._factory = CCP4Factory() # allows lots of post scaling calculations
    self._scaler = DialsScale()
    self._res_limit = None # Don't call _resolution_limit else causes bug

  # Schema/Sweep.py wants these two methods need to be implemented by subclasses,
  # but are not actually used at the moment?
  def _scale_list_likely_pointgroups(self):
    pass

  def _scale_reindex_to_reference(self):
    pass

  def _updated_dials_scaler(self):

    if PhilIndex.params.xia2.settings.resolution.d_min:
      self._scaler.set_resolution(PhilIndex.params.xia2.settings.resolution.d_min)

    return self._scaler

  def _scale_prepare(self):
    '''Perform all of the preparation required to deliver the scaled
    data. This should sort together the reflection files, ensure that
    they are correctly indexed (via dials.symmetry) and generally tidy
    things up.'''

    need_to_return = False

    self._scaler.clear_datafiles()
    self._sweep_handler = SweepInformationHandler(self._scalr_integraters)

    Journal.block(
        'gathering', self.get_scaler_xcrystal().get_name(), 'Dials',
        {'working directory':self.get_working_directory()})

    # First do stuff to work out if excluding any data
    # Note - does this actually work? I couldn't seem to get it to work
    # in either this pipleline or the standard dials pipeline
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
        Debug.write('Excluding sweep %s' % sname)
      else:
        Journal.entry({'adding data from':'%s/%s/%s' % \
                       (xname, dname, sname)})


    # In here, we don't want to be starting from scratch each time, so if
    # scaled_experiments already exists, then do symmetry on this

    # Run dials.symmetry

    # If multiple files, want to run symmetry to check for consistent indexing
    # also
    self._symmetry_analyser = DialsSymmetry()

    multi_sweep_indexing = \
      PhilIndex.params.xia2.settings.multi_sweep_indexing == True

    # try to reproduce what CCP4ScalerA is doing

    # START OF if more than one epoch
    if len(self._sweep_handler.get_epochs()) > 1:

      # First - force all lattices to be same and hope its okay.
      #START OF if multi_sweep indexing and not input pg
      if multi_sweep_indexing and not self._scalr_input_pointgroup:

        refiners = []
        experiments = []
        reflections = []

        for epoch in self._sweep_handler.get_epochs():
          si = self._sweep_handler.get_sweep_information(epoch)
          integrater = si.get_integrater()
          experiments.append(integrater.get_integrated_experiments())
          reflections.append(integrater.get_integrated_reflections())
          refiners.append(integrater.get_integrater_refiner())

        #SUMMARY - have added all sweeps to exps, refls, refiners

        Debug.write('Running multisweep dials.symmetry for %d sweeps' %
                    len(refiners))
        pointgroup, reindex_op, ntr, pt = \
                    symmetry_indexer_multisweep(experiments, reflections, refiners)

        Debug.write('X1698: %s: %s' % (pointgroup, reindex_op))

        lattices = [Syminfo.get_lattice(pointgroup)]

        for epoch in self._sweep_handler.get_epochs():
          si = self._sweep_handler.get_sweep_information(epoch)
          intgr = si.get_integrater()
          if ntr:
            intgr.integrater_reset_reindex_operator()
            need_to_return = True

        #SUMMARY - got data from all sweeps, ran _symmetry_indexer_multisweep
        # on this, made a list of one lattice and potentially reset reindex op?
      #END OF if multi_sweep indexing and not input pg

      #START OF if not multi_sweep, or input pg given
      else:
        lattices = []

        for epoch in self._sweep_handler.get_epochs():

          si = self._sweep_handler.get_sweep_information(epoch)
          intgr = si.get_integrater()
          experiment = intgr.get_integrated_experiments()
          reflections = intgr.get_integrated_reflections()
          refiner = intgr.get_integrater_refiner()

          if self._scalr_input_pointgroup:
            pointgroup = self._scalr_input_pointgroup
            reindex_op = 'h,k,l'
            ntr = False

          else:

            pointgroup, reindex_op, ntr, pt = \
              dials_symmetry_indexer_jiffy(experiment, reflections, refiner)

            Debug.write('X1698: %s: %s' % (pointgroup, reindex_op))

          lattice = Syminfo.get_lattice(pointgroup)

          if not lattice in lattices:
            lattices.append(lattice)

          if ntr:

            intgr.integrater_reset_reindex_operator()
            need_to_return = True
        #SUMMARY do dials.symmetry on each sweep, get lattices and make a list
        # of unique lattices, potentially reset reindex op.
      #END OF if not multi_sweep, or input pg given

      #SUMMARY - still within if more than one epoch, now have a list of number
      # of lattices

      # START OF if multiple-lattices
      if len(lattices) > 1:
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
            raise RuntimeError('Lattice %s impossible for %s' \
                  % (correct_lattice, sname))
          elif state == refiner.LATTICE_POSSIBLE:
            Chatter.write('Lattice %s assigned for sweep %s' % \
                          (correct_lattice, sname))
            need_to_return = True
      # END OF if multiple-lattices
      #SUMMARY - forced all lattices to be same and hope its okay.
    # END OF if more than one epoch

    # if one or more of them was not in the lowest lattice,
    # need to return here to allow reprocessing

    if need_to_return:
      self.set_scaler_done(False)
      self.set_scaler_prepare_done(False)
      return

    # ---------- REINDEX ALL DATA TO CORRECT POINTGROUP ----------

    # all should share the same pointgroup, unless twinned... in which
    # case force them to be...

    pointgroups = {}
    reindex_ops = {}
    probably_twinned = False

    need_to_return = False

    multi_sweep_indexing = \
      PhilIndex.params.xia2.settings.multi_sweep_indexing == True

    # START OF if multi-sweep and not input pg
    if multi_sweep_indexing and not self._scalr_input_pointgroup:

      refiners = []
      experiments = []
      reflections = []

      for epoch in self._sweep_handler.get_epochs():
        si = self._sweep_handler.get_sweep_information(epoch)
        integrater = si.get_integrater()
        experiments.append(integrater.get_integrated_experiments())
        reflections.append(integrater.get_integrated_reflections())
        refiners.append(integrater.get_integrater_refiner())

      pointgroup, reindex_op, ntr, pt = \
        symmetry_indexer_multisweep(experiments, reflections, refiners)

      for epoch in self._sweep_handler.get_epochs():
        pointgroups[epoch] = pointgroup
        reindex_ops[epoch] = reindex_op
      #SUMMARY ran dials.symmetry multisweep and made a dict
      # of pointgroups and reindex_ops (all same??)
    #END OF if multi-sweep and not input pg

    #START OF if not mulit-sweep or pg given
    else:

      for epoch in self._sweep_handler.get_epochs():
        si = self._sweep_handler.get_sweep_information(epoch)
        intgr = si.get_integrater()
        experiment = intgr.get_integrated_experiments()
        reflections = intgr.get_integrated_reflections()
        refiner = intgr.get_integrater_refiner()

        if self._scalr_input_pointgroup:
          Debug.write('Using input pointgroup: %s' % \
                      self._scalr_input_pointgroup)
          pointgroup = self._scalr_input_pointgroup
          reindex_op = 'h,k,l'
          pt = False

        else:
          pointgroup, reindex_op, ntr, pt = \
            dials_symmetry_indexer_jiffy(experiment, reflections, refiner)

          Debug.write('X1698: %s: %s' % (pointgroup, reindex_op))

          if ntr:
            integrater.integrater_reset_reindex_operator()
            need_to_return = True

        if pt and not probably_twinned:
          probably_twinned = True

        Debug.write('Pointgroup: %s (%s)' % (pointgroup, reindex_op))

        pointgroups[epoch] = pointgroup
        reindex_ops[epoch] = reindex_op
      #SUMMARY - for each sweep, run indexer jiffy and get reindex operators
      # and pointgroups dictionaries (could be different between sweeps)

    #END OF if not mulit-sweep or pg given

    overall_pointgroup = None

    pointgroup_set = {pointgroups[e] for e in pointgroups}

    if len(pointgroup_set) > 1 and \
       not probably_twinned:
      raise RuntimeError('non uniform pointgroups')

    if len(pointgroup_set) > 1:
      Debug.write('Probably twinned, pointgroups: %s' % \
                  ' '.join([p.replace(' ', '') for p in \
                            list(pointgroup_set)]))
      numbers = [Syminfo.spacegroup_name_to_number(s) for s in \
                 pointgroup_set]
      overall_pointgroup = Syminfo.spacegroup_number_to_name(min(numbers))
      self._scalr_input_pointgroup = overall_pointgroup

      Chatter.write('Twinning detected, assume pointgroup %s' % \
                    overall_pointgroup)

      need_to_return = True

    else:
      overall_pointgroup = pointgroup_set.pop()
    # SUMMARY - Have handled if different pointgroups & chosen an overall_pointgroup
    # which is the lowest symmetry

    self._reference_reflections = None
    self._reference_experiments = None

    # Now go through sweeps and do reindexing
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
    self._reference = None
    if PhilIndex.params.xia2.settings.unify_setting:
      pass
      #copy code from CCP4scalerA

    if self.get_scaler_reference_reflection_file():
      self._reference = self.get_scaler_reference_reflection_file()
      Debug.write('Using HKLREF %s' % self._reference)

    elif PhilIndex.params.xia2.settings.scale.reference_reflection_file:
      self._reference = PhilIndex.params.xia2.settings.scale.reference_reflection_file
      Debug.write('Using HKLREF %s' % self._reference)

    params = PhilIndex.params
    use_brehm_diederichs = params.xia2.settings.use_brehm_diederichs
    if len(self._sweep_handler.get_epochs()) > 1 and use_brehm_diederichs and False:
      pass
      #group code later with CCP4scalerA
    # If not Brehm-deidrichs, set reference as first sweep
    elif len(self._sweep_handler.get_epochs()) > 1 and \
           not self._reference:

      first = self._sweep_handler.get_epochs()[0]
      si = self._sweep_handler.get_sweep_information(first)
      self._reference_experiments = si.get_integrater().get_integrated_experiments()
      self._reference_reflections = si.get_integrater().get_integrated_reflections()
      #self._reference = si.get_reflections()

    # Now reindex to be consistent with first dataset - run reindex on each
    # dataset with reference
    if self._reference_reflections:
      assert self._reference_experiments

      '''md = self._factory.Mtzdump()
      md.set_hklin(self._reference)
      md.dump()

      if md.get_batches() and False:
        raise RuntimeError('reference reflection file %s unmerged' % \
              self._reference)

      datasets = md.get_datasets()

      if len(datasets) > 1 and False:
        raise RuntimeError('more than one dataset in %s' % \
              self._reference)'''

      # then get the unit cell, lattice etc.

      # Need to get spacegroup and lattice by loading experiments file
      #reference_lattice = Syminfo.get_lattice(self._reference_experiments.crsytal.get_spacegroup())

      #reference_cell = md.get_dataset_info(datasets[0])['cell'] #FIXME how to get this from exp?

      # then compute the pointgroup from this...

      # ---------- REINDEX TO CORRECT (REFERENCE) SETTING ----------
      Chatter.write('Reindexing all datasets to common reference')
      counter = 0
      for epoch in self._sweep_handler.get_epochs():
        reindexed_exp_fpath = str(counter) + '_reindexed_experiments.json'
        reindexed_refl_fpath = str(counter) + '_reindexed_reflections.pickle'

        # if we are working with unified UB matrix then this should not
        # be a problem here (note, *if*; *should*)

        # what about e.g. alternative P1 settings?
        # see JIRA MXSW-904
        if PhilIndex.params.xia2.settings.unify_setting:
          continue

        reindexer = DialsReindex()

        si = self._sweep_handler.get_sweep_information(epoch)
        exp = si.get_integrater().get_integrated_experiments()
        refl = si.get_integrater().get_integrated_experiments()

        reindexer.set_reference_filename(self._reference_experiments)
        reindexer.set_reference_reflections(self._reference_reflections)
        reindexer.set_indexed_filename(refl)
        reindexer.set_experiments_filename(exp)
        reindexer.set_reindexed_experiments_filename(reindexed_exp_fpath)
        reindexer.set_reindexed_reflections_filename(reindexed_refl_fpath)

        reindexer.run()

        Debug.write('Reindexing analysis of %s' % ' '.join([exp, refl]))

        '''pointgroup = pl.get_pointgroup()
        reindex_op = pl.get_reindex_operator()

        Debug.write('Operator: %s' % reindex_op)'''

        # apply this...

        integrater = si.get_integrater()
        integrater.set_integrated_reflections(reindexed_refl_fpath)
        integrater.set_integrated_experiments(reindexed_exp_fpath)

        '''integrater.set_integrater_reindex_operator(reindex_op,
                                                   reason='match reference')'''
        #integrater.set_integrater_spacegroup_number(
        #    Syminfo.spacegroup_name_to_number(pointgroup))
        si.set_reflections(integrater.get_integrater_intensities())
        counter += 1
        '''md = self._factory.Mtzdump()
        md.set_hklin(si.get_reflections())
        md.dump()

        datasets = md.get_datasets()

        if len(datasets) > 1:
          raise RuntimeError('more than one dataset in %s' % \
                si.get_reflections())

        # then get the unit cell, lattice etc.

        lattice = Syminfo.get_lattice(md.get_spacegroup())
        cell = md.get_dataset_info(datasets[0])['cell']

        if lattice != reference_lattice:
          raise RuntimeError('lattices differ in %s and %s' % \
                (self._reference, si.get_reflections()))

        Debug.write('Cell: %.2f %.2f %.2f %.2f %.2f %.2f' % cell)
        Debug.write('Ref:  %.2f %.2f %.2f %.2f %.2f %.2f' % reference_cell)

        for j in range(6):
          if math.fabs((cell[j] - reference_cell[j]) /
                       reference_cell[j]) > 0.1:
            raise RuntimeError( \
                  'unit cell parameters differ in %s and %s' % \
                  (self._reference, si.get_reflections()))'''

    # Now all have been reindexed, run a round of space group determination on
    # joint set.
    # FIXME not yet implemented for dials.symmetry? just take point group now
    epoch = self._sweep_handler.get_epochs()[0]
    symmetry_analyser = DialsSymmetry()

    si = self._sweep_handler.get_sweep_information(epoch)
    exp = si.get_integrater().get_integrated_experiments()
    refl = si.get_integrater().get_integrated_reflections()
    symmetry_analyser.add_experiments(exp)
    symmetry_analyser.add_reflections(refl)
    symmetry_analyser.decide_pointgroup()
    spacegroup = symmetry_analyser.get_pointgroup()
    self._scalr_likely_spacegroups = [spacegroup]
    Chatter.write('Likely spacegroups:')
    for spag in self._scalr_likely_spacegroups:
      Chatter.write('%s' % spag)


    '''exp_path = os.path.join(self.get_working_directory(), 'scaled_experiments.json')
    refl_path = os.path.join(self.get_working_directory(), 'scaled_reflections.pickle')

    if not os.path.exists(exp_path):
      #no files currently in symmetry analyser,  so populate from integraters
      for integrater in self._scalr_integraters.itervalues():
        self._symmetry_analyser = DialsSymmetry()
        self._symmetry_analyser.add_experiments(integrater.get_integrated_experiments())
        self._symmetry_analyser.add_reflections(integrater.get_integrated_reflections())
        reind_exp = os.path.join(self.get_working_directory(), 'reindexed_experiments.json')
        reind_refl = os.path.join(self.get_working_directory(), 'reindexed_reflections.pickle')
        reind_json = os.path.join(self.get_working_directory(), 'dials_symmetry.json')
        self._symmetry_analyser.set_json(reind_json)
        self._symmetry_analyser.set_output_experiments_filename(reind_exp)
        self._symmetry_analyser.set_output_reflections_filename(reind_refl)
        self._symmetry_analyser.decide_pointgroup()
        self._scalr_likely_spacegroups = self._symmetry_analyser.get_likely_spacegroups()
        Chatter.write('Likely spacegroups:')
        for spag in self._scalr_likely_spacegroups:
          Chatter.write('%s' % spag)
    else:
      self._symmetry_analyser.add_experiments(exp_path)
      self._symmetry_analyser.add_reflections(refl_path)

    # set output filepaths
    reind_exp = os.path.join(self.get_working_directory(), 'reindexed_experiments.json')
    reind_refl = os.path.join(self.get_working_directory(), 'reindexed_reflections.pickle')
    reind_json = os.path.join(self.get_working_directory(), 'dials_symmetry.json')
    self._symmetry_analyser.set_json(reind_json)
    self._symmetry_analyser.set_output_experiments_filename(reind_exp)
    self._symmetry_analyser.set_output_reflections_filename(reind_refl)

    # do the symmetry analysis
    self._symmetry_analyser.decide_pointgroup()

    self._scalr_likely_spacegroups = self._symmetry_analyser.get_likely_spacegroups()

    Chatter.write('Likely spacegroups:')
    for spag in self._scalr_likely_spacegroups:
      Chatter.write('%s' % spag)

    spacegroup = self._symmetry_analyser.get_spacegroup()
    reindex_operator = self._symmetry_analyser.get_spacegroup_reindex_operator()
    Chatter.write(
        'Reindexing to first spacegroup setting: %s (%s)' % \
        (spacegroup, clean_reindex_operator(reindex_operator)))'''

    #Now add files to scaler
    #self._scaler.add_experiments_json(reind_exp)
    #self._scaler.add_reflections_pickle(reind_refl)

    p, x = self._sweep_handler.get_project_info()
    self._scalr_pname = p
    self._scalr_xname = x


  def _scale(self):
    '''Perform all of the operations required to deliver the scaled
    data.'''

    epochs = self._sweep_handler.get_epochs()

    if self._scalr_corrections:
      Journal.block(
          'scaling', self.get_scaler_xcrystal().get_name(), 'Dials',
          {'scaling model':'automatic',
           'absorption':self._scalr_correct_absorption,
           'decay':self._scalr_correct_decay
           })

    else:
      Journal.block(
          'scaling', self.get_scaler_xcrystal().get_name(), 'Dials',
          {'scaling model':'default'})

    sc = self._updated_dials_scaler()

    # Set paths
    scaled_mtz_path = os.path.join(self.get_working_directory(),
                               '%s_%s_scaled.mtz' % \
                               (self._scalr_pname,
                                self._scalr_xname))
    scaled_unmerged_mtz_path = os.path.join(self.get_working_directory(),
                               '%s_%s_scaled_unmerged.mtz' % \
                               (self._scalr_pname,
                                self._scalr_xname))

    exp_path = os.path.join(self.get_working_directory(), 'scaled_experiments.json')
    refl_path = os.path.join(self.get_working_directory(), 'scaled_reflections.pickle')
    if not os.path.exists(exp_path): # FIXME What about if the data have been reindexed
      #inbetween runs, such that we need to reload the data and start again?
      for epoch in self._sweep_handler.get_epochs():
        si = self._sweep_handler.get_sweep_information(epoch)
        intgr = si.get_integrater()
        experiment = intgr.get_integrated_experiments()
        reflections = intgr.get_integrated_reflections()
        self._scaler.add_experiments_json(experiment)
        self._scaler.add_reflections_pickle(reflections)
    self._scaler.set_scaled_experiments(exp_path)
    self._scaler.set_scaled_reflections(refl_path)
    self._scaler.set_scaled_unmerged_mtz(scaled_unmerged_mtz_path)
    self._scaler.set_scaled_mtz(scaled_mtz_path)
    self._scalr_scaled_reflection_files = {}
    self._scalr_scaled_reflection_files['mtz_unmerged'] = {'NATIVE' : scaled_unmerged_mtz_path}
    self._scalr_scaled_reflection_files['mtz'] = {'NATIVE' : scaled_mtz_path}

    user_resolution_limits = {}

    for epoch in epochs:

      si = self._sweep_handler.get_sweep_information(epoch)
      pname, xname, dname = si.get_project_info()
      sname = si.get_sweep_name()
      intgr = si.get_integrater()

      if intgr.get_integrater_user_resolution():
        # record user resolution here but don't use it until later - why?
        dmin = intgr.get_integrater_high_resolution()

        if (dname, sname) not in user_resolution_limits:
          user_resolution_limits[(dname, sname)] = dmin
        elif dmin < user_resolution_limits[(dname, sname)]:
          user_resolution_limits[(dname, sname)] = dmin

      if (dname, sname) in self._scalr_resolution_limits:
        resolution, _ = self._scalr_resolution_limits[(dname, sname)]
        sc.set_resolution(resolution)
        #self._res_limit = resolution

    sc.scale()

    # make it so that only scaled.pickle and scaled_experiments.json are
    # the files that dials.scale knows about, so that if scale is called again,
    # scaling resumes from where it left off.
    self._scaler.clear_datafiles()
    self._scaler.add_experiments_json(exp_path)
    self._scaler.add_reflections_pickle(refl_path)

    # Run twotheta refine
    self._update_scaled_unit_cell()

    hklout = copy.deepcopy(self._scaler.get_scaled_mtz())
    self._scalr_scaled_refl_files = {'NATIVE' : hklout}
    FileHandler.record_data_file(hklout)

    highest_suggested_resolution = None
    highest_resolution = 100.0

    #copypasta from CCP4ScalerA - could be grouped into common method?
    for epoch in epochs:

      si = self._sweep_handler.get_sweep_information(epoch)
      pname, xname, dname = si.get_project_info()
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
        Chatter.write('Resolution limit for %s: %5.2f (user provided)' % \
                      (dname, limit))
        continue

      #FIXME need to separate out data into different sweeps based on experiment
      #id in order to calculate a res limit for each dataset.

      hklin = sc.get_unmerged_reflection_file() #combined for all datasets
      # Need to get an individual mtz for each dataset
      limit, reasoning = self._estimate_resolution_limit(
        hklin, batch_range=None)

      if PhilIndex.params.xia2.settings.resolution.keep_all_reflections == True:
        suggested = limit
        if highest_suggested_resolution is None or limit < highest_suggested_resolution:
          highest_suggested_resolution = limit
        limit = intgr.get_detector().get_max_resolution(intgr.get_beam_obj().get_s0())
        self._scalr_resolution_limits[(dname, sname)] = (limit, suggested)
        Debug.write('keep_all_reflections set, using detector limits')
      Debug.write('Resolution for sweep %s: %.2f' % \
                  (sname, limit))

      if not (dname, sname) in self._scalr_resolution_limits:
        self._scalr_resolution_limits[(dname, sname)] = (limit, None)
        self.set_scaler_done(False)

      if limit < highest_resolution:
        highest_resolution = limit

      limit, suggested = self._scalr_resolution_limits[(dname, sname)]
      if suggested is None or limit == suggested:
        reasoning_str = ''
        if reasoning:
          reasoning_str = ' (%s)' % reasoning
        Chatter.write('Resolution for sweep %s/%s: %.2f%s' % \
                      (dname, sname, limit, reasoning_str))
      else:
        Chatter.write('Resolution limit for %s/%s: %5.2f (%5.2f suggested)' % \
                      (dname, sname, limit, suggested))

    if highest_suggested_resolution is not None and \
        highest_resolution >= (highest_suggested_resolution - 0.004):
      Debug.write('Dropping resolution cut-off suggestion since it is'
                  ' essentially identical to the actual resolution limit.')
      highest_suggested_resolution = None
    self._scalr_highest_resolution = highest_resolution
    self._scalr_highest_suggested_resolution = highest_suggested_resolution
    if highest_suggested_resolution is not None:
      Debug.write('Suggested highest resolution is %5.2f (%5.2f suggested)' % \
                (highest_resolution, highest_suggested_resolution))
    else:
      Debug.write('Scaler highest resolution set to %5.2f' % \
                highest_resolution)
    # Resolution code same as CCP4ScalerA down to here?

    # Adds merging statistics to be reported later in output - in log and html
    if PhilIndex.params.xia2.settings.merging_statistics.source == 'cctbx':
      for key in self._scalr_scaled_refl_files:
        stats = self._compute_scaler_statistics(
          self._scalr_scaled_reflection_files['mtz_unmerged'][key],
          selected_band=(highest_suggested_resolution, None), wave=key)
        self._scalr_statistics[
          (self._scalr_pname, self._scalr_xname, key)] = stats #adds here

  #more copypasta - exactly same as CCP4ScalerA, move to CommonScaler?
  def _update_scaled_unit_cell(self):
        # FIXME this could be brought in-house

    params = PhilIndex.params
    fast_mode = params.dials.fast_mode
    if (params.xia2.settings.integrater == 'dials' and not fast_mode
        and params.xia2.settings.scale.two_theta_refine):
      from xia2.Wrappers.Dials.TwoThetaRefine import TwoThetaRefine
      from xia2.lib.bits import auto_logfiler

      Chatter.banner('Unit cell refinement')

      # Collect a list of all sweeps, grouped by project, crystal, wavelength
      groups = {}
      self._scalr_cell_dict = {}
      tt_refine_experiments = []
      tt_refine_pickles = []
      tt_refine_reindex_ops = []
      for epoch in self._sweep_handler.get_epochs():
        si = self._sweep_handler.get_sweep_information(epoch)
        pi = '_'.join(si.get_project_info())
        intgr = si.get_integrater()
        groups[pi] = groups.get(pi, []) + \
          [(intgr.get_integrated_experiments(),
            intgr.get_integrated_reflections(),
            intgr.get_integrater_reindex_operator())]

      # Two theta refine the unit cell for each group
      p4p_file = os.path.join(self.get_working_directory(),
                              '%s_%s.p4p' % (self._scalr_pname, self._scalr_xname))
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
          reindex_ops = [(
            cb_op(str(self._spacegroup_reindex_operator)) * cb_op(str(op))).as_hkl()
            if op is not None else self._spacegroup_reindex_operator
            for op in reindex_ops]
        tt_grouprefiner.set_reindex_operators(reindex_ops)
        tt_grouprefiner.run()
        Chatter.write('%s: %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % \
          tuple([''.join(pi.split('_')[2:])] + list(tt_grouprefiner.get_unit_cell())))
        self._scalr_cell_dict[pi] = (tt_grouprefiner.get_unit_cell(), tt_grouprefiner.get_unit_cell_esd(), tt_grouprefiner.import_cif(), tt_grouprefiner.import_mmcif())
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
          reindex_ops = [(
            cb_op(str(self._spacegroup_reindex_operator)) * cb_op(str(op))).as_hkl()
            if op is not None else self._spacegroup_reindex_operator
            for op in tt_refine_reindex_ops]
        tt_refiner.set_reindex_operators(reindex_ops)
        tt_refiner.run()
        self._scalr_cell = tt_refiner.get_unit_cell()
        Chatter.write('Overall: %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % tt_refiner.get_unit_cell())
        self._scalr_cell_esd = tt_refiner.get_unit_cell_esd()
        cif_in = tt_refiner.import_cif()
        mmcif_in = tt_refiner.import_mmcif()
      else:
        self._scalr_cell, self._scalr_cell_esd, cif_in, mmcif_in = self._scalr_cell_dict.values()[0]
      if params.xia2.settings.small_molecule == True:
        FileHandler.record_data_file(p4p_file)

      import dials.util.version
      cif_out = CIF.get_block('xia2')
      mmcif_out = mmCIF.get_block('xia2')
      cif_out['_computing_cell_refinement'] = mmcif_out['_computing.cell_refinement'] = 'DIALS 2theta refinement, %s' % dials.util.version.dials_version()
      for key in sorted(cif_in.keys()):
        cif_out[key] = cif_in[key]
      for key in sorted(mmcif_in.keys()):
        mmcif_out[key] = mmcif_in[key]

      Debug.write('Unit cell obtained by two-theta refinement')

    else:
      ami = AnalyseMyIntensities()
      ami.set_working_directory(self.get_working_directory())

      average_unit_cell, ignore_sg = ami.compute_average_cell(
        [self._scalr_scaled_refl_files[key] for key in
        self._scalr_scaled_refl_files])

      Debug.write('Computed average unit cell (will use in all files)')
      self._scalr_cell = average_unit_cell
      self._scalr_cell_esd = None

      # Write average unit cell to .cif
      cif_out = CIF.get_block('xia2')
      cif_out['_computing_cell_refinement'] = 'AIMLESS averaged unit cell'
      for cell, cifname in zip(self._scalr_cell,
                              ['length_a', 'length_b', 'length_c', 'angle_alpha', 'angle_beta', 'angle_gamma']):
        cif_out['_cell_%s' % cifname] = cell

    Debug.write('%7.3f %7.3f %7.3f %7.3f %7.3f %7.3f' % \
              self._scalr_cell)

def symmetry_indexer_multisweep(experiments, reflections, refiners):
  '''A jiffy to centralise the interactions between dials.symmetry
  and the Indexer, multisweep edition.'''

  need_to_return = False
  probably_twinned = False

  symmetry_analyser = DialsSymmetry()
  for (exp, refl) in zip(experiments, reflections):
    symmetry_analyser.add_experiments(exp)
    symmetry_analyser.add_reflections(refl)
  symmetry_analyser.decide_pointgroup()

  rerun_symmetry = False

  possible = symmetry_analyser.get_possible_lattices()

  correct_lattice = None

  Debug.write('Possible lattices (dials.symmetry):')

  Debug.write(' '.join(possible))

  # any of them contain the same indexer link, so all good here.
  refiner = refiners[0]

  for lattice in possible:
    state = refiner.set_refiner_asserted_lattice(lattice)
    if state == refiner.LATTICE_CORRECT:
      Debug.write('Agreed lattice %s' % lattice)
      correct_lattice = lattice
      break

    elif state == refiner.LATTICE_IMPOSSIBLE:
      Debug.write('Rejected lattice %s' % lattice)
      rerun_symmetry = True
      continue

    elif state == refiner.LATTICE_POSSIBLE:
      Debug.write('Accepted lattice %s, will reprocess' % lattice)
      need_to_return = True
      correct_lattice = lattice
      break

  if correct_lattice is None:
    correct_lattice = refiner.get_refiner_lattice()
    rerun_symmetry = True

    Debug.write('No solution found: assuming lattice from refiner')

  if need_to_return:
    if (PhilIndex.params.xia2.settings.integrate_p1 and not
        PhilIndex.params.xia2.settings.reintegrate_correct_lattice):
      need_to_return = False
      rerun_symmetry = True
    else:
      for refiner in refiners[1:]:
        refiner.refiner_reset()

  if rerun_symmetry:
    symmetry_analyser.set_correct_lattice(correct_lattice)
    symmetry_analyser.decide_pointgroup()

  Debug.write('Symmetry analysis of %s' % ' '.join(experiments) + ' '.join(reflections))

  pointgroup = symmetry_analyser.get_pointgroup()
  reindex_op = symmetry_analyser.get_reindex_operator()
  probably_twinned = symmetry_analyser.get_probably_twinned()

  Debug.write('Pointgroup: %s (%s)' % (pointgroup, reindex_op))

  return pointgroup, reindex_op, need_to_return, probably_twinned

def dials_symmetry_indexer_jiffy(experiment, reflection, refiner):
  '''A jiffy to centralise the interactions between pointless
  and the Indexer.'''

  need_to_return = False
  probably_twinned = False

  symmetry_analyser = DialsSymmetry()

  symmetry_analyser.add_experiments(experiment)
  symmetry_analyser.add_reflections(reflection)
  symmetry_analyser.decide_pointgroup()

  rerun_symmetry = False

  possible = symmetry_analyser.get_possible_lattices()

  correct_lattice = None

  Debug.write('Possible lattices (dials.symmetry):')

  Debug.write(' '.join(possible))

  for lattice in possible:
    state = refiner.set_refiner_asserted_lattice(lattice)
    if state == refiner.LATTICE_CORRECT:
      Debug.write('Agreed lattice %s' % lattice)
      correct_lattice = lattice
      break

    elif state == refiner.LATTICE_IMPOSSIBLE:
      Debug.write('Rejected lattice %s' % lattice)
      rerun_symmetry = True
      continue

    elif state == refiner.LATTICE_POSSIBLE:
      Debug.write('Accepted lattice %s, will reprocess' % lattice)
      need_to_return = True
      correct_lattice = lattice
      break

  if correct_lattice is None:
    correct_lattice = refiner.get_refiner_lattice()
    rerun_symmetry = True

    Debug.write('No solution found: assuming lattice from refiner')

  if rerun_symmetry:
    symmetry_analyser.set_correct_lattice(correct_lattice)
    symmetry_analyser.decide_pointgroup()

  Debug.write('dial.symmetry analysis of %s' % ' '.join([experiment, reflection]))

  pointgroup = symmetry_analyser.get_pointgroup()
  reindex_op = symmetry_analyser.get_reindex_operator()
  probably_twinned = symmetry_analyser.get_probably_twinned()

  Debug.write('Pointgroup: %s (%s)' % (pointgroup, reindex_op))

  return pointgroup, reindex_op, need_to_return, probably_twinned
