#!/usr/bin/env python
# MosflmIndexer.py
#   Copyright (C) 2006-2014 CCLRC, Graeme Winter & Richard Gildea
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 23rd June 2006
#
# A wrapper for the data processing program Mosflm, with the following
# methods to provide functionality:

import os
import sys
import math

if not os.environ.has_key('XIA2CORE_ROOT'):
  raise RuntimeError, 'XIA2CORE_ROOT not defined'
if not os.environ.has_key('XIA2_ROOT'):
  raise RuntimeError, 'XIA2_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
  sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))
if not os.environ['XIA2_ROOT'] in sys.path:
  sys.path.append(os.environ['XIA2_ROOT'])

# interfaces that this will present
from Schema.Interfaces.Indexer import IndexerSingleSweep

# output streams &c.
from Handlers.Streams import Chatter, Debug, Journal
from Handlers.Citations import Citations
from Handlers.Flags import Flags
#from Handlers.Executables import Executables
from Handlers.Files import FileHandler

# helpers
from Wrappers.CCP4.MosflmHelpers import _get_indexing_solution_number
from Wrappers.Mosflm.MosflmIndex import MosflmIndex

# things we are moving towards...
from Modules.Indexer.IndexerSelectImages import index_select_images_lone, \
     index_select_images_user

from lib.bits import auto_logfiler
from lib.SymmetryLib import lattice_to_spacegroup

# exceptions
#from Schema.Exceptions.BadLatticeError import BadLatticeError
#from Schema.Exceptions.NegativeMosaicError import NegativeMosaicError
#from Schema.Exceptions.IndexingError import IndexingError

from Wrappers.XIA.Printpeaks import Printpeaks

# cell refinement image helpers
from Modules.Indexer.MosflmCheckIndexerSolution import \
     mosflm_check_indexer_solution


class MosflmIndexer(IndexerSingleSweep):
  '''A wrapper for Mosflm indexing'''

  def __init__(self):
    super(MosflmIndexer, self).__init__()

    # local parameters used in autoindexing
    self._mosflm_autoindex_sol = 0
    self._mosflm_autoindex_thresh = None
    #self._mosflm_spot_file = None

    return

  def _index_prepare(self):

    if self._indxr_images == []:
      self._index_select_images()

    if self._mosflm_autoindex_thresh is None and \
           Flags.get_microcrystal():
      self._mosflm_autoindex_thresh = 5

    return

  def _index_select_images(self):
    '''Select correct images based on image headers.'''

    if Flags.get_small_molecule():
      return self._index_select_images_small_molecule()

    if Flags.get_microcrystal():
      return self._index_select_images_microcrystal()

    phi_width = self.get_phi_width()
    images = self.get_matching_images()

    if Flags.get_interactive():
      selected_images = index_select_images_user(phi_width, images,
                                                 Chatter)
    else:
      selected_images = index_select_images_lone(phi_width, images)

    for image in selected_images:
      Debug.write('Selected image %s' % image)
      self.add_indexer_image_wedge(image)

    return

  def _index_select_images_small_molecule(self):
    '''Select correct images based on image headers. This one is for
    when you have small molecule data so want more images.'''

    phi_width = self.get_phi_width()
    images = self.get_matching_images()

    Debug.write('Selected image %s' % images[0])

    self.add_indexer_image_wedge(images[0])

    offset = images[0] - 1

    # add an image every 15 degrees up to 90 degrees

    for j in range(6):

      image_number = offset + int(15 * (j + 1) / phi_width)

      if not image_number in images:
        break

      Debug.write('Selected image %s' % image_number)
      self.add_indexer_image_wedge(image_number)

    return

  def _index_select_images_microcrystal(self):
    '''Select images for more difficult cases e.g. microcrystal
    work. Will apply (up to) 20 images to the task.'''

    phi_width = self.get_phi_width()
    images = self.get_matching_images()

    spacing = max(1, int(len(images) / 20))

    selected = []

    for j in range(0, len(images), spacing):
      selected.append(images[j])

    for image in selected[:20]:
      self.add_indexer_image_wedge(image)

    return

  def _index(self):
    '''Implement the indexer interface.'''

    Citations.cite('mosflm')

    indexer = MosflmIndex()
    indexer.set_working_directory(self.get_working_directory())
    auto_logfiler(indexer)

    from lib.bits import unique_elements
    _images = unique_elements(self._indxr_images)
    indexer.set_images(_images)
    images_str = ', '.join(map(str, _images))

    cell_str = None
    if self._indxr_input_cell:
      cell_str = '%.2f %.2f %.2f %.2f %.2f %.2f' % \
                  self._indxr_input_cell

    if self._indxr_sweep_name:

      #if len(self._fp_directory) <= 50:
        #dirname = self._fp_directory
      #else:
        #dirname = '...%s' % self._fp_directory[-46:]
      dirname = os.path.dirname(self.get_imageset().get_template())

      Journal.block(
          'autoindexing', self._indxr_sweep_name, 'mosflm',
          {'images':images_str,
           'target cell':self._indxr_input_cell,
           'target lattice':self._indxr_input_lattice,
           'template':self.get_imageset().get_template(),
           'directory':dirname})

    #task = 'Autoindex from images:'

    #for i in _images:
      #task += ' %s' % self.get_image_name(i)

    #self.set_task(task)

    indexer.set_template(self.get_imageset().get_template())
    indexer.set_directory(os.path.dirname(self.get_imageset().get_template()))

    xsweep = self.get_indexer_sweep()
    if xsweep is not None:
      if xsweep.get_distance() is not None:
        index.set_distance(self.get_distance())
      #if self.get_wavelength_prov() == 'user':
        #index.set_wavelength(self.get_wavelength())
      if xsweep.get_beam_centre() is not None:
        index.set_beam_centre(self.get_beam_centre())

    if self._indxr_input_cell:
      indexer.set_unit_cell(self._indxr_input_cell)

    if self._indxr_input_lattice != None:
      spacegroup_number = lattice_to_spacegroup(
          self._indxr_input_lattice)
      indexer.set_space_group_number(spacegroup_number)

    if not self._mosflm_autoindex_thresh:

      try:

        min_peaks = 200

        Debug.write('Aiming for at least %d spots...' % min_peaks)

        thresholds = []

        for i in _images:

          p = Printpeaks()
          p.set_working_directory(self.get_working_directory())
          auto_logfiler(p)
          p.set_image(self.get_image_name(i))
          thresh = p.threshold(min_peaks)

          Debug.write('Autoindex threshold for image %d: %d' % \
                      (i, thresh))

          thresholds.append(thresh)

        thresh = min(thresholds)
        self._mosflm_autoindex_thresh = thresh

      except Exception as e:
        print str(e) #XXX this should disappear!
        Debug.write('Error computing threshold: %s' % str(e))
        Debug.write('Using default of 20.0')
        thresh = 20.0

    else:
      thresh = self._mosflm_autoindex_thresh

    Debug.write('Using autoindex threshold: %d' % thresh)

    if self._mosflm_autoindex_sol:
      indexer.set_solution_number(self._mosflm_autoindex_sol)
    indexer.set_threshold(thresh)

    # now forget this to prevent weird things happening later on
    if self._mosflm_autoindex_sol:
      self._mosflm_autoindex_sol = 0

    indexer.run()

    #sweep = self.get_indexer_sweep_name()
    #FileHandler.record_log_file(
        #'%s INDEX' % (sweep), self.get_log_file())

    indxr_cell = indexer.get_refined_unit_cell()
    self._indxr_lattice = indexer.get_lattice()
    space_group_number = indexer.get_indexed_space_group_number()
    detector_distance = indexer.get_refined_distance()
    beam_centre = indexer.get_refined_beam_centre()
    mosaic_spreads = indexer.get_mosaic_spreads()

    if min(list(indxr_cell)) < 10.0 and \
       indxr_cell[2] / indxr_cell[0] > 6:

      Debug.write(
          'Unrealistic autoindexing solution: ' +
          '%.2f %.2f %.2f %.2f %.2f %.2f' % indxr_cell)

      # tweak some parameters and try again...
      self._mosflm_autoindex_thresh *= 1.5
      self.set_indexer_done(False)

      return

    intgr_params = { }

    # look up other possible indexing solutions (not well - in
    # standard settings only!) This is moved earlier as it could
    # result in returning if Mosflm has selected the wrong
    # solution!

    try:
      self._indxr_other_lattice_cell = indexer.get_solutions()

      # Change 27/FEB/08 to support user assigned spacegroups
      if self._indxr_user_input_lattice:
        lattice_to_spacegroup_dict = {
            'aP':1, 'mP':3, 'mC':5, 'oP':16, 'oC':20, 'oF':22,
            'oI':23, 'tP':75, 'tI':79, 'hP':143, 'hR':146,
            'cP':195, 'cF':196, 'cI':197}
        for k in self._indxr_other_lattice_cell.keys():
          if lattice_to_spacegroup_dict[k] > \
                 lattice_to_spacegroup_dict[
              self._indxr_input_lattice]:
            del(self._indxr_other_lattice_cell[k])

      # check that the selected unit cell matches - and if
      # not raise a "horrible" exception

      if self._indxr_input_cell:
        assert indxr_cell is not None
        for j in range(6):
          if math.fabs(self._indxr_input_cell[j] - indxr_cell[j]) > 2.0:
            Chatter.write(
                'Mosflm autoindexing did not select ' +
                'correct (target) unit cell')
            raise RuntimeError, \
                  'something horrible happened in indexing'

    except RuntimeError, e:
      # check if mosflm rejected a solution we have it
      if 'horribl' in str(e):
        # ok it did - time to break out the big guns...
        if not self._indxr_input_cell:
          raise RuntimeError, \
                'error in solution selection when not preset'

        # XXX FIXME
        self._mosflm_autoindex_sol = _get_indexing_solution_number(
          indexer.get_all_output(),
          self._indxr_input_cell,
          self._indxr_input_lattice)

        # set the fact that we are not done...
        self.set_indexer_done(False)

        # and return - hopefully this will restart everything
        return
      else:
        raise e

    if len(mosaic_spreads) == 0:
      # then consider setting it do a default value...
      # equal to the oscillation width (a good guess)
      phi_width = self.get_phi_width()
      Chatter.write(
          'Mosaic estimation failed, so guessing at %4.2f' % \
          phi_width)
      # only consider this if we have thus far no idea on the
      # mosaic spread...
      mosaic_spreads.append(phi_width)

    #if Flags.get_microcrystal():
      #self._indxr_mosaic = 0.5
    #else:
      #raise IndexingError, 'mosaicity estimation failed'

    intgr_params['raster'] = indexer.get_raster()

    intgr_params['separation'] = indexer.get_separation()

    self._indxr_resolution_estimate = indexer.get_resolution_estimate()

    # compute mosaic as mean(mosaic_spreads)

    self._indxr_mosaic = sum(mosaic_spreads) / len(mosaic_spreads)

    self._indxr_payload['mosflm_integration_parameters'] = intgr_params

    self._indxr_payload['mosflm_orientation_matrix'] = open(
        os.path.join(self.get_working_directory(),
                     'xiaindex.mat'), 'r').readlines()

    import copy
    from dxtbx.model.detector_helpers import set_mosflm_beam_centre
    from Wrappers.Mosflm.AutoindexHelpers import set_distance
    from Wrappers.Mosflm.AutoindexHelpers import crystal_model_from_mosflm_mat
    from cctbx import sgtbx, uctbx
    from dxtbx.model.crystal import crystal_model_from_mosflm_matrix

    # update the beam centre (i.e. shift the origin of the detector)
    detector = copy.deepcopy(self.get_detector())
    beam = copy.deepcopy(self.get_beam())
    set_mosflm_beam_centre(detector, beam, beam_centre)
    if detector_distance is not None:
      set_distance(detector, detector_distance)

    # make a dxtbx crystal_model object from the mosflm matrix
    space_group = sgtbx.space_group_info(number=space_group_number).group()
    crystal_model = crystal_model_from_mosflm_mat(
      self._indxr_payload['mosflm_orientation_matrix'],
      unit_cell=uctbx.unit_cell(tuple(indxr_cell)),
      space_group=space_group)

    # construct an experiment_list
    from dxtbx.model.experiment.experiment_list import Experiment, ExperimentList
    experiment = Experiment(beam=beam,
                            detector=detector,
                            goniometer=self.get_goniometer(),
                            scan=self.get_scan(),
                            crystal=crystal_model,
                            )

    experiment_list = ExperimentList([experiment])
    self.set_indexer_experiment_list(experiment_list)
    return

  def _index_finish(self):
    '''Check that the autoindexing gave a convincing result, and
    if not (i.e. it gave a centred lattice where a primitive one
    would be correct) pick up the correct solution.'''

    if self._indxr_input_lattice:
      return

    if self.get_indexer_sweep():
      if self.get_indexer_sweep().get_user_lattice():
        return

    try:
      status, lattice, matrix, cell = mosflm_check_indexer_solution(
          self)
    except:
      return

    if status is False or status is None:
      return

    # ok need to update internals...

    self._indxr_lattice = lattice
    self._indxr_cell = cell

    Debug.write('Inserting solution: %s ' % lattice +
                '%6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % cell)

    self._indxr_replace(lattice, cell)

    self._indxr_payload['mosflm_orientation_matrix'] = matrix

    return
