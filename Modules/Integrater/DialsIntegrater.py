#!/usr/bin/env python
# DialsIntegrater.py
#   Copyright (C) 2014 Diamond Light Source, Richard Gildea & Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# An implementation of the Integrater interface using Dials. This depends on the
# Dials wrappers to actually implement the functionality.
#

import os
import sys
import math
import copy
import shutil

if not os.environ.has_key('XIA2_ROOT'):
  raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
  sys.path.append(os.environ['XIA2_ROOT'])

# wrappers for programs that this needs

from Wrappers.Dials.Refine import Refine as _Refine
from Wrappers.Dials.Integrate import Integrate as _Integrate
from Wrappers.Dials.ExportMtz import ExportMtz as _ExportMtz
from Wrappers.Dials.ShowIsigRmsd import ShowIsigRmsd as _ShowIsigRmsd

# interfaces that this must implement to be an integrater

from Schema.Interfaces.Integrater import Integrater

from Schema.Exceptions.BadLatticeError import BadLatticeError

# indexing functionality if not already provided - even if it is
# we still need to reindex with DIALS.

from Modules.Indexer.DialsIndexer import DialsIndexer
from Wrappers.CCP4.Reindex import Reindex

# odds and sods that are needed

from lib.bits import auto_logfiler
from lib.SymmetryLib import lattice_to_spacegroup
from Handlers.Streams import Chatter, Debug, Journal
from Handlers.Flags import Flags
from Handlers.Files import FileHandler
from Handlers.Phil import PhilIndex

from Experts.SymmetryExpert import lattice_to_spacegroup_number

class DialsIntegrater(Integrater):
  '''A class to implement the Integrater interface using *only* DIALS
  programs.'''

  def __init__(self):
    super(DialsIntegrater, self).__init__()

    # check that the programs exist - this will raise an exception if
    # they do not...

    integrate = _Integrate()

    # place to store working data
    self._data_files = { }

    # internal parameters to pass around
    self._integrate_parameters = { }
    self._intgr_integrated_filename = None

    return

  # overload these methods as we don't want the resolution range
  # feeding back... aha - but we may want to assign them
  # from outside!

  def set_integrater_resolution(self, dmin, dmax, user = False):
    if user:
      Integrater.set_integrater_resolution(self, dmin, dmax, user)
    return

  def set_integrater_high_resolution(self, dmin, user = False):
    if user:
      Integrater.set_integrater_high_resolution(self, dmin, user)
    return

  def set_integrater_low_resolution(self, dmax, user = False):
    self._intgr_reso_low = dmax
    return

  # admin functions

  def get_integrated_filename(self):
    return self._intgr_integrated_filename

  # factory functions

  def Integrate(self, indexed_filename=None):
    params = PhilIndex.params.dials.integrate
    integrate = _Integrate()
    integrate.set_phil_file(params.phil_file)
    integrate.set_intensity_algorithm(params.intensity_algorithm)
    integrate.set_background_outlier_algorithm(
      params.background_outlier_algorithm)
    integrate.set_working_directory(self.get_working_directory())

    integrate.set_experiments_filename(self._intgr_experiments_filename)

    integrate.set_reflections_filename(self._intgr_indexed_filename)

    integrate.set_use_threading(params.use_threading)

    auto_logfiler(integrate, 'INTEGRATE')

    return integrate

  def ExportMtz(self):
    params = PhilIndex.params.dials.integrate
    export = _ExportMtz()
    export.set_working_directory(self.get_working_directory())

    export.set_experiments_filename(self._intgr_experiments_filename)
    export.set_include_partials(params.include_partials)

    auto_logfiler(export, 'EXPORTMTZ')

    return export

  def ShowIsigRmsd(self):
    show = _ShowIsigRmsd()
    show.set_working_directory(self.get_working_directory())
    auto_logfiler(show, 'SHOWISIGRMSD')
    return show

  # now some real functions, which do useful things

  def _integrater_reset_callback(self):
    '''Delete all results on a reset.'''
    Debug.write('Deleting all stored results.')
    self._data_files = { }
    self._integrate_parameters = { }
    return

  def _integrate_prepare(self):
    '''Prepare for integration - in XDS terms this may mean rerunning
    IDXREF to get the XPARM etc. DEFPIX is considered part of the full
    integration as it is resolution dependent.'''

    from Handlers.Citations import Citations
    Citations.cite('dials')

    # decide what images we are going to process, if not already
    # specified
    if not self._intgr_wedge:
      images = self.get_matching_images()
      self.set_integrater_wedge(min(images),
                                max(images))

    Debug.write('DIALS INTEGRATE PREPARE:')
    Debug.write('Wavelength: %.6f' % self.get_wavelength())
    Debug.write('Distance: %.2f' % self.get_distance())

    #if not self._intgr_indexer:
      #self.set_integrater_indexer(DialsIndexer())
      #self.get_integrater_indexer().set_indexer_sweep(
          #self.get_integrater_sweep())

      #self._intgr_indexer.set_working_directory(
          #self.get_working_directory())

      #self._intgr_indexer.setup_from_imageset(self.get_imageset())

      #if self.get_frame_wedge():
        #wedge = self.get_frame_wedge()
        #Debug.write('Propogating wedge limit: %d %d' % wedge)
        #self._intgr_indexer.set_frame_wedge(wedge[0], wedge[1],
                                            #apply_offset = False)

      ## this needs to be set up from the contents of the
      ## Integrater frame processer - wavelength &c.

      #if self.get_beam_centre():
        #self._intgr_indexer.set_beam_centre(self.get_beam_centre())

      #if self.get_distance():
        #self._intgr_indexer.set_distance(self.get_distance())

      #if self.get_wavelength():
        #self._intgr_indexer.set_wavelength(
            #self.get_wavelength())

    ## get the unit cell from this indexer to initiate processing
    ## if it is new... and also copy out all of the information for
    ## the Dials indexer if not...

    #experiments = self._intgr_indexer.get_indexer_experiment_list()
    #assert len(experiments) == 1 # currently only handle one lattice/sweep
    #experiment = experiments[0]
    #crystal_model = experiment.crystal
    #lattice = self._intgr_indexer.get_indexer_lattice()

    ## check if the lattice was user assigned...
    #user_assigned = self._intgr_indexer.get_indexer_user_input_lattice()

    # XXX check that the indexer is an Dials indexer - if not then
    # create one...

    # set a low resolution limit (which isn't really used...)
    # this should perhaps be done more intelligently from an
    # analysis of the spot list or something...?

    if not self.get_integrater_low_resolution():

      dmax = self._intgr_refiner.get_indexer_low_resolution(
        self.get_integrater_epoch())
      self.set_integrater_low_resolution(dmax)

      Debug.write('Low resolution set to: %s' % \
                  self.get_integrater_low_resolution())

    ## copy the data across
    from dxtbx.serialize import load

    refiner = self.get_integrater_refiner()
    self._intgr_experiments_filename = refiner.get_refiner_payload(
      "experiments.json")
    experiments = load.experiment_list(self._intgr_experiments_filename)
    experiment = experiments[0]
    self._intgr_indexed_filename = refiner.get_refiner_payload(
      "reflections.pickle")

    # this is the result of the cell refinement
    self._intgr_cell = experiment.crystal.get_unit_cell().parameters()

    Debug.write('Files available at the end of DIALS integrate prepare:')
    for f in self._data_files.keys():
      Debug.write('%s' % f)

    self.set_detector(experiment.detector)
    self.set_beam_obj(experiment.beam)
    self.set_goniometer(experiment.goniometer)

    return

  def _integrate(self):
    '''Actually do the integration - in XDS terms this will mean running
    DEFPIX and INTEGRATE to measure all the reflections.'''

    images_str = '%d to %d' % tuple(self._intgr_wedge)
    cell_str = '%.2f %.2f %.2f %.2f %.2f %.2f' % tuple(self._intgr_cell)

    if len(self._fp_directory) <= 50:
      dirname = self._fp_directory
    else:
      dirname = '...%s' % self._fp_directory[-46:]

    Journal.block(
        'integrating', self._intgr_sweep_name, 'DIALS',
        {'images':images_str,
         'cell':cell_str,
         'lattice':self.get_integrater_refiner().get_refiner_lattice(),
         'template':self._fp_template,
         'directory':dirname,
         'resolution':'%.2f' % self._intgr_reso_high})

    integrate = self.Integrate()

    if self._integrate_parameters:
      integrate.set_updates(self._integrate_parameters)

    # decide what images we are going to process, if not already
    # specified

    if not self._intgr_wedge:
      images = self.get_matching_images()
      self.set_integrater_wedge(min(images),
                                max(images))

    first_image_in_wedge = self.get_image_name(self._intgr_wedge[0])

    integrate.set_experiments_filename(self._intgr_experiments_filename)
    integrate.set_reflections_filename(self._intgr_indexed_filename)
    integrate.set_dmax(self._intgr_reso_low)

    integrate.run()

    # also record the batch range - needed for the analysis of the
    # radiation damage in chef...

    self._intgr_batches_out = (self._intgr_wedge[0], self._intgr_wedge[1])

    # FIXME (i) record the log file, (ii) get more information out from the
    # integration log on the quality of the data and (iii) the mosaic spread
    # range observed and R.M.S. deviations.

    self._intgr_integrated_pickle = integrate.get_integrated_filename()
    if not os.path.isfile(self._intgr_integrated_pickle):
      raise RuntimeError("Integration failed: %s does not exist."
                         %self._intgr_integrated_pickle)

    show = self.ShowIsigRmsd()
    show.set_reflections_filename(self._intgr_integrated_pickle)
    show.run()
    data = show.data()

    spot_status = ''

    for frame in range(self._intgr_wedge[0], self._intgr_wedge[1] + 1):
      n, isig, rmsd = data.get(frame, (0, 0.0, 0.0))

      if isig < 1.0:
        status = '.'
      elif rmsd > 2.5:
        status = '!'
      elif rmsd > 1.0:
        status = '%'
      else:
        status = 'o'

      spot_status += status


    if len(spot_status) > 60:
      Chatter.write('Integration status per image (60/record):')
    else:
      Chatter.write('Integration status per image:')

    for chunk in [spot_status[i:i + 60] \
                  for i in range(0, len(spot_status), 60)]:
      Chatter.write(chunk)

    Chatter.write(
      '"o" => good        "%" => ok        "!" => bad rmsd')
    Chatter.write(
      '"O" => overloaded  "#" => many bad  "." => weak')
    Chatter.write(
      '"@" => abandoned')

    mosaic = integrate.get_mosaic()
    Chatter.write('Mosaic spread: %.3f < %.3f < %.3f' % \
                  (mosaic, mosaic, mosaic))

    return self._intgr_integrated_pickle

  def _integrate_finish(self):
    '''Finish off the integration by running dials.export_mtz.'''

    exporter = self.ExportMtz()
    exporter.set_reflections_filename(self._intgr_integrated_pickle)
    mtz_filename = os.path.join(
      self.get_working_directory(), '%s_integrated.mtz' %exporter.get_xpid())
    exporter.set_mtz_filename(mtz_filename)
    exporter.run()
    self._intgr_integrated_filename = mtz_filename
    if not os.path.isfile(self._intgr_integrated_filename):
      raise RuntimeError("dials.export_mtz failed: %s does not exist."
                         % self._intgr_integrated_filename)

    if self._intgr_reindex_operator is None and \
      self._intgr_spacegroup_number == lattice_to_spacegroup(
        self.get_integrater_refiner().get_refiner_lattice()):
      return mtz_filename

    if self._intgr_reindex_operator is None and \
      self._intgr_spacegroup_number == 0:
      return mtz_filename

    Debug.write('Reindexing to spacegroup %d (%s)' % \
                (self._intgr_spacegroup_number,
                 self._intgr_reindex_operator))

    hklin = mtz_filename
    reindex = Reindex()
    reindex.set_working_directory(self.get_working_directory())
    auto_logfiler(reindex)

    reindex.set_operator(self._intgr_reindex_operator)

    if self._intgr_spacegroup_number:
      reindex.set_spacegroup(self._intgr_spacegroup_number)
    hklout = '%s_reindex.mtz' % hklin[:-4]
    reindex.set_hklin(hklin)
    reindex.set_hklout(hklout)
    reindex.reindex()
    self._intgr_integrated_filename = hklout
    self._intgr_cell = reindex.get_cell()

    return hklout

if __name__ == '__main__':

  # run a demo test

  if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

  di = DialsIntegrater()
  di.setup_from_image(sys.argv[1])
  from Schema.XCrystal import XCrystal
  from Schema.XWavelength import XWavelength
  from Schema.XSweep import XSweep
  cryst = XCrystal("CRYST1", None)
  wav = XWavelength("WAVE1", cryst, di.get_wavelength())
  directory, image = os.path.split(sys.argv[1])
  sweep = XSweep('SWEEP1', wav, directory=directory, image=image)
  di.set_integrater_sweep(sweep)
  di.integrate()
