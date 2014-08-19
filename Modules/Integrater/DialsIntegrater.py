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

from Wrappers.Dials.Integrate import Integrate as _Integrate
from Wrappers.Dials.ExportMtz import ExportMtz as _ExportMtz

# interfaces that this must implement to be an integrater

from Schema.Interfaces.Integrater import Integrater
from Schema.Interfaces.FrameProcessor import FrameProcessor
from Schema.Exceptions.BadLatticeError import BadLatticeError

# indexing functionality if not already provided - even if it is
# we still need to reindex with XDS.

from Modules.Indexer.DialsIndexer import DialsIndexer

# odds and sods that are needed

from lib.bits import auto_logfiler
from Handlers.Streams import Chatter, Debug, Journal
from Handlers.Flags import Flags
from Handlers.Files import FileHandler
from Handlers.Phil import PhilIndex

from Experts.SymmetryExpert import lattice_to_spacegroup_number

class DialsIntegrater(FrameProcessor,
                      Integrater):
  '''A class to implement the Integrater interface using *only* XDS
  programs.'''

  def __init__(self):

    # set up the inherited objects

    FrameProcessor.__init__(self)
    Integrater.__init__(self)

    # check that the programs exist - this will raise an exception if
    # they do not...

    integrate = _Integrate()

    # admin junk
    self._working_directory = os.getcwd()

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

  def set_working_directory(self, working_directory):
    self._working_directory = working_directory
    return

  def get_working_directory(self):
    return self._working_directory

  def get_integrated_filename(self):
    return self._intgr_integrated_filename

  #def _set_integrater_reindex_operator_callback(self):
    #'''If a REMOVE.HKL file exists in the working
    #directory, remove it...'''
    #if os.path.exists(os.path.join(
        #self.get_working_directory(),
        #'REMOVE.HKL')):
      #os.remove(os.path.join(
          #self.get_working_directory(),
          #'REMOVE.HKL'))
      #Debug.write('Deleting REMOVE.HKL as reindex op set.')
    #return

  # factory functions

  def Integrate(self):
    integrate = _Integrate()
    integrate.set_phil_file(PhilIndex.params.dials.integrate.phil_file)
    integrate.set_working_directory(self.get_working_directory())

    integrate.setup_from_image(self.get_image_name(
        self._intgr_wedge[0]))
    integrate.set_experiments_filename(self._intgr_experiments_filename)
    integrate.set_reflections_filename(
      self._intgr_indexer.get_indexed_filename())

    if self.get_distance():
      integrate.set_distance(self.get_distance())

    if self.get_wavelength():
      integrate.set_wavelength(self.get_wavelength())

    auto_logfiler(integrate, 'INTEGRATE')

    return integrate

  def ExportMtz(self):
    export = _ExportMtz()
    export.set_working_directory(self.get_working_directory())

    export.set_experiments_filename(self._intgr_experiments_filename)

    auto_logfiler(export, 'EXPORTMTZ')

    return export

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

    # decide what images we are going to process, if not already
    # specified
    if not self._intgr_wedge:
      images = self.get_matching_images()
      self.set_integrater_wedge(min(images),
                                max(images))

    Debug.write('DIALS INTEGRATE PREPARE:')
    Debug.write('Wavelength: %.6f' % self.get_wavelength())
    Debug.write('Distance: %.2f' % self.get_distance())

    if not self._intgr_indexer:
      self.set_integrater_indexer(DialsIndexer())
      self.get_integrater_indexer().set_indexer_sweep(
          self.get_integrater_sweep())

      self._intgr_indexer.set_working_directory(
          self.get_working_directory())

      self._intgr_indexer.setup_from_image(self.get_image_name(
          self._intgr_wedge[0]))

      if self.get_frame_wedge():
        wedge = self.get_frame_wedge()
        Debug.write('Propogating wedge limit: %d %d' % wedge)
        self._intgr_indexer.set_frame_wedge(wedge[0], wedge[1],
                                            apply_offset = False)

      # this needs to be set up from the contents of the
      # Integrater frame processer - wavelength &c.

      if self.get_beam_centre():
        self._intgr_indexer.set_beam_centre(self.get_beam_centre())

      if self.get_distance():
        self._intgr_indexer.set_distance(self.get_distance())

      if self.get_wavelength():
        self._intgr_indexer.set_wavelength(
            self.get_wavelength())

      #experiments = self._intgr_indexer.get_indexer_experiment_list()

    # get the unit cell from this indexer to initiate processing
    # if it is new... and also copy out all of the information for
    # the Dials indexer if not...

    experiments = self._intgr_indexer.get_indexer_experiment_list()
    assert len(experiments) == 1 # currently only handle one lattice/sweep
    experiment = experiments[0]
    crystal_model = experiment.crystal
    lattice = self._intgr_indexer.get_indexer_lattice()

    # check if the lattice was user assigned...
    user_assigned = self._intgr_indexer.get_indexer_user_input_lattice()

    # XXX check that the indexer is an Dials indexer - if not then
    # create one...

    # set a low resolution limit (which isn't really used...)
    # this should perhaps be done more intelligently from an
    # analysis of the spot list or something...?

    if not self.get_integrater_low_resolution():

      dmax = self._intgr_indexer.get_indexer_low_resolution()
      self.set_integrater_low_resolution(dmax)

      Debug.write('Low resolution set to: %s' % \
                  self.get_integrater_low_resolution())

    # copy the data across
    from dxtbx.serialize import dump
    self._intgr_experiments_filename = os.path.join(
      self.get_working_directory(), "experiments.json")
    dump.experiment_list(experiments, self._intgr_experiments_filename)
    self._intgr_indexed_filename = os.path.join(
      self.get_working_directory(), os.path.basename(
        self._intgr_indexer.get_indexed_filename()))

    #shutil.copyfile(self._intgr_indexer.get_experiments_filename(),
                #self._intgr_experiments_filename)
    if self._intgr_indexer.get_indexed_filename() != self._intgr_indexed_filename:
      shutil.copyfile(self._intgr_indexer.get_indexed_filename(),
                      self._intgr_indexed_filename)

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

    images_str = '%d to %d' % self._intgr_wedge
    cell_str = '%.2f %.2f %.2f %.2f %.2f %.2f' % \
               self._intgr_indexer.get_indexer_cell()

    if len(self._fp_directory) <= 50:
      dirname = self._fp_directory
    else:
      dirname = '...%s' % self._fp_directory[-46:]

    Journal.block(
        'integrating', self._intgr_sweep_name, 'DIALS',
        {'images':images_str,
         'cell':cell_str,
         'lattice':self.get_integrater_indexer().get_indexer_lattice(),
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

    #integrate.set_data_range(self._intgr_wedge[0],
                             #self._intgr_wedge[1])

    integrate.set_experiments_filename(self._intgr_experiments_filename)
    integrate.set_reflections_filename(self._intgr_indexed_filename)

    #for file in ['X-CORRECTIONS.cbf',
                 #'Y-CORRECTIONS.cbf',
                 #'BLANK.cbf',
                 #'BKGPIX.cbf',
                 #'GAIN.cbf']:
      #integrate.set_input_data_file(file, self._data_files[file])

    integrate.run()

    # record the log file -

    #pname, xname, dname = self.get_integrater_project_info()
    #sweep = self.get_integrater_sweep_name()
    #FileHandler.record_log_file('%s %s %s %s INTEGRATE' % \
                                #(pname, xname, dname, sweep),
                                #os.path.join(self.get_working_directory(),
                                             #'INTEGRATE.LP'))

    ## and copy the first pass INTEGRATE.HKL...

    #lattice = self._intgr_indexer.get_indexer_lattice()
    #if not os.path.exists(os.path.join(
        #self.get_working_directory(),
        #'INTEGRATE-%s.HKL' % lattice)):
      #here = self.get_working_directory()
      #shutil.copyfile(os.path.join(here, 'INTEGRATE.HKL'),
                      #os.path.join(here, 'INTEGRATE-%s.HKL' % lattice))

    ## record INTEGRATE.HKL for e.g. BLEND.

    #FileHandler.record_more_data_file(
        #'%s %s %s %s INTEGRATE' % (pname, xname, dname, sweep),
        #os.path.join(self.get_working_directory(), 'INTEGRATE.HKL'))

    ## should the existence of these require that I rerun the
    ## integration or can we assume that the application of a
    ## sensible resolution limit will achieve this??

    #self._integrate_parameters = integrate.get_updates()

    ## record the mosaic spread &c.

    #m_min, m_mean, m_max = integrate.get_mosaic()
    #self.set_integrater_mosaic_min_mean_max(m_min, m_mean, m_max)

    #Chatter.write('Mosaic spread: %.3f < %.3f < %.3f' % \
                  #self.get_integrater_mosaic_min_mean_max())

    self._intgr_integrated_filename \
      = os.path.join(self.get_working_directory(), 'integrated.pickle')

    return self._intgr_integrated_filename

  def _integrate_finish(self):
    '''Finish off the integration by running correct.'''

    exporter = self.ExportMtz()
    exporter.set_reflections_filename(self.get_integrated_filename())
    mtz_filename = os.path.join(self.get_working_directory(), 'integrated.mtz')
    exporter.set_mtz_filename(mtz_filename)
    exporter.run()
    self._intgr_integrated_filename = mtz_filename

    return mtz_filename

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
