#An implementation of the scaler interface for dials.scale

from __future__ import absolute_import, division, print_function
import os
import copy as copy

from xia2.Handlers.CIF import CIF, mmCIF
from xia2.Handlers.Citations import Citations
from xia2.Handlers.Files import FileHandler
from xia2.lib.bits import is_mtz_file, auto_logfiler
from xia2.Handlers.Phil import PhilIndex
from xia2.Handlers.Streams import Chatter, Debug, Journal
from xia2.Modules.Scaler.CommonScaler import CommonScaler as Scaler
from xia2.Wrappers.Dials.Scale import DialsScale
from xia2.Modules.AnalyseMyIntensities import AnalyseMyIntensities
from xia2.Wrappers.CCP4.CCP4Factory import CCP4Factory
from xia2.Modules.Scaler.CCP4ScalerHelpers import SweepInformationHandler, _prepare_pointless_hklin
from xia2.Wrappers.Dials.Symmetry import DialsSymmetry
from xia2.Wrappers.Dials.CombineExperiments import CombineExperiments

def clean_reindex_operator(reindex_operator):
  return reindex_operator.replace('[', '').replace(']', '')

class DialsScaler(Scaler):

  def __init__(self):
    super(DialsScaler, self).__init__()

    self._scalr_scaled_refl_files = {} #dials.scale outputs all data into one file,
    #so behaviour is different to other scaling methods perhaps.
    self._scalr_statistics = {}
    self._factory = CCP4Factory()
    self._scaler = DialsScale()
    self._res_limit = None # Don't call _resolution_limit else causes bug

  # return the dials.scale wrapper with the correct setup

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

    self._scaler.clear_datafiles()
    self._sweep_handler = SweepInformationHandler(self._scalr_integraters)

    Journal.block(
        'gathering', self.get_scaler_xcrystal().get_name(), 'Dials',
        {'working directory':self.get_working_directory()})

    '''# First do stuff to work out if excluding any data

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

    for e in self._sweep_handler.get_epochs():
      si = self._sweep_handler.get_sweep_information(e)
      assert is_mtz_file(si.get_reflections())'''

    #Run dials.symmetry
    exp_path = os.path.join(self.get_working_directory(), 'scaled_experiments.json')
    refl_path = os.path.join(self.get_working_directory(), 'scaled_reflections.pickle')
    if not os.path.exists(exp_path):
      self._symmetry_analyser = DialsSymmetry()
      #no files currently in scaler,  so populate from integraters
      for integrater in self._scalr_integraters.itervalues():
        self._symmetry_analyser.add_experiments(integrater.get_integrated_experiments())
        self._symmetry_analyser.add_reflections(integrater.get_integrated_reflections())
    else:
      self._symmetry_analyser = DialsSymmetry()
      self._symmetry_analyser.add_experiments(exp_path)
      self._symmetry_analyser.add_reflections(refl_path)

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

    spacegroup = self._symmetry_analyser.get_spacegroup()
    reindex_operator = self._symmetry_analyser.get_spacegroup_reindex_operator()
    Chatter.write(
        'Reindexing to first spacegroup setting: %s (%s)' % \
        (spacegroup, clean_reindex_operator(reindex_operator)))

    #Now add files to scaler
    self._scaler.add_experiments_json(reind_exp)
    self._scaler.add_reflections_pickle(reind_refl)

    p, x = self._sweep_handler.get_project_info()
    self._scalr_pname = p
    self._scalr_xname = x

    #self._sort_together_data_ccp4()

  def _prepare_pointless_hklin(self, hklin, phi_width):
    return _prepare_pointless_hklin(self.get_working_directory(),
                                    hklin, phi_width)

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
    self._scaler.set_scaled_experiments(exp_path)
    self._scaler.set_scaled_reflections(refl_path)
    self._scaler.set_scaled_unmerged_mtz(scaled_unmerged_mtz_path)
    self._scaler.set_scaled_mtz(scaled_mtz_path)
    self._scalr_scaled_reflection_files = {}
    self._scalr_scaled_reflection_files['mtz_unmerged'] = {'NATIVE' : scaled_unmerged_mtz_path}
    self._scalr_scaled_reflection_files['mtz'] = {'NATIVE' : scaled_mtz_path}

    for epoch in epochs:

      si = self._sweep_handler.get_sweep_information(epoch)
      pname, xname, dname = si.get_project_info()
      sname = si.get_sweep_name()
      intgr = si.get_integrater()

      '''if intgr.get_integrater_user_resolution():
        dmin = intgr.get_integrater_high_resolution()

        if (dname, sname) not in user_resolution_limits:
          user_resolution_limits[(dname, sname)] = dmin
        elif dmin < user_resolution_limits[(dname, sname)]:
          user_resolution_limits[(dname, sname)] = dmin'''

      start, end = si.get_batch_range()

      if (dname, sname) in self._scalr_resolution_limits:
        resolution, _ = self._scalr_resolution_limits[(dname, sname)]
        sc.set_resolution(resolution)
        self._res_limit = resolution

    sc.scale()

    self._scaler.clear_datafiles()
    self._scaler.add_experiments_json(exp_path)
    self._scaler.add_reflections_pickle(refl_path)

    self._update_scaled_unit_cell()

    hklout = copy.deepcopy(self._scaler.get_scaled_mtz())
    self._scalr_scaled_refl_files = {'NATIVE' : hklout}
    FileHandler.record_data_file(hklout)

    highest_suggested_resolution = None
    highest_resolution = 100.0
    user_resolution_limits = {}

    epochs = self._sweep_handler.get_epochs()

    #copypasta from CCP4ScalerA
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

      hklin = sc.get_unmerged_reflection_file()
      limit, reasoning = self._estimate_resolution_limit(
        hklin, batch_range=(start, end))

      if not (dname, sname) in self._scalr_resolution_limits:
        self._scalr_resolution_limits[(dname, sname)] = (limit, None)
        self.set_scaler_done(False)

      if reasoning:
        reasoning_str = ' (%s)' % reasoning
        Chatter.write('Resolution for sweep %s/%s: %.2f%s' % \
                      (dname, sname, limit, reasoning_str))

    # Adds merging statistics to be reported later in output - in log and html
    if PhilIndex.params.xia2.settings.merging_statistics.source == 'cctbx':
      for key in self._scalr_scaled_refl_files:
        stats = self._compute_scaler_statistics(
          self._scalr_scaled_reflection_files['mtz_unmerged'][key],
          selected_band=(self._res_limit, None), wave=key)
        self._scalr_statistics[
          (self._scalr_pname, self._scalr_xname, key)] = stats #adds here

  def _analyse_resolution_cutoff(self):

    highest_suggested_resolution = None
    highest_resolution = 100.0
    user_resolution_limits = {}

    epochs = self._sweep_handler.get_epochs()

    #copypasta from CCP4ScalerA
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

      hklin = sc.get_unmerged_reflection_file()
      limit, reasoning = self._estimate_resolution_limit(
        hklin, batch_range=(start, end))

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
        self._scaler.clear_datafiles()
        #self.set_scaler_prepare_done(False)

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


  #more copypasta
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
