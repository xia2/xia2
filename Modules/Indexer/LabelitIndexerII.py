#!/usr/bin/env python
# LabelitIndexerII.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 2nd June 2006
#
# A wrapper for labelit.index - this will provide functionality to:
#
# Decide the beam centre.
# Index the lattce.
#
# Using all of the images and (as of 9/JUN/10) a development version of
# Labelit. This takes into account partiality of reflections.
#
# Now done...
#
# (1) Implement setting of beam, wavelength, distance via labelit parameter
#     .py file. [dataset_preferences.py] autoindex_override_beam = (x, y)
#     distance wavelength etc.
#
# (2) Implement profile bumpiness handling if the detector is an image plate.
#     (this goes in the same file...) this is distl_profile_bumpiness = 5
#
# Modifications:
#
# 13/JUN/06: Added mosaic spread getting
# 21/JUN/06: Added unit cell volume getting
# 23/JUN/06: FIXME should the images to index be specified by number or
#            by name? No implementation change, Q needs answering.
#            c/f Mosflm wrapper.
# 07/JUL/06: write_ds_preferences now "protected".
# 10/JUL/06: Modified to inherit from FrameProcessor interface to provide
#            all of the guff to handle the images etc. Though this handles
#            only the template &c., not the image selections for indexing.
#
# FIXME 24/AUG/06 Need to be able to get the raster & separation parameters
#                 from the integrationNN.sh script, so that I can reproduce
#                 the interface now provided by the Mosflm implementation
#                 (this adds a dictionary with a few extra parameters - dead
#                 useful under some circumstances) - Oh, I can't do this
#                 because Labelit doesn't produce these parameters!
#
# FIXED 06/SEP/06 Need to update interface to handle unit cell input as
#                 described in an email from Nick:
#
#                 known_symmetry=P4 known_cell=a,b,c,alpha,beta,gamma
#
#                 Though this will depend on installing the latest CVS
#                 version (funfunfun) [or the 1.0.0a3 source tarball, easier!]
#
#                 Ok, doing this will simply assign the smiley correctly -
#                 the other solutions are also displayed. I guess that this
#                 will be useful for indexing multiple sets though.
#
# FIXME 06/SEP/06 This needs to have an indentity change to LabelitIndex
#                 Combine this with the renaming of LabelitStats_distl to
#                 fit in with LabelitMosflmMatrix.
#
# FIXED 18/SEP/06 pass on the working directory to sub processes...
#
# FIXME 19/SEP/06 need to inspect the metric fit parameters - for 1vr9/native
#                 labelit now happily indexes in I222 not correctly in C2 -
#                 this is shown by a poor metric penalty. Also need to
#                 implement lattice reduction. Follow up 16/OCT/06 discussed
#                 with Nick S about this and not sure what parameters have
#                 changed but is still interested in making this work properly.
#
# FIXME 16/OCT/06 if more than two images are passed in for indexing can cope,
#                 just need to assign wedge_limit = N where N is the number
#                 of images in dataset_preferences.py... apparently this is
#                 there for "historical reasons"...
#
# FIXME 07/NOV/06 new error message encountered trying to index 1VP4 LREM LR
#                 in oC lattice:
#
#                 No_Lattice_Selection: In this case 3 of 12 lattice \
#                 solutions have the oC Bravais type and nearly
#                 the same cell.  Run labelit again without the \
#                 known_symmetry and known_cell keywords.
#
#                 Need to be able to handle this...

from __future__ import absolute_import, division

import copy
import math

# other labelit things that this uses
from xia2.Wrappers.Labelit.LabelitMosflmMatrix import LabelitMosflmMatrix
from xia2.Wrappers.Labelit.LabelitStats_distl import LabelitStats_distl
from xia2.Wrappers.Labelit.LabelitDistl import LabelitDistl
from xia2.Wrappers.Phenix.LatticeSymmetry import LatticeSymmetry

from xia2.lib.bits import auto_logfiler
from xia2.lib.SymmetryLib import lattice_to_spacegroup
from xia2.Handlers.Streams import Chatter, Debug, Journal
from xia2.Handlers.Citations import Citations
from xia2.Modules.Indexer.MosflmCheckIndexerSolution import \
     mosflm_check_indexer_solution
from xia2.Modules.Indexer.LabelitIndexer import LabelitIndexer

class LabelitIndexerII(LabelitIndexer):
  '''A wrapper for the program labelit.index - which will provide
  functionality for deciding the beam centre and indexing the
  diffraction pattern.'''

  def __init__(self, indxr_print=True):
    super(LabelitIndexerII, self).__init__(indxr_print=indxr_print)
    self._primitive_unit_cell = []
    return

  def _index_prepare(self):
    # prepare to do some autoindexing

    super(LabelitIndexerII, self)._index_prepare()

    assert self._indxr_input_cell is not None, "Unit cell required for LabelitIndexerII"

    # calculate the correct primitive unit cell
    if self._indxr_input_cell and self._indxr_input_lattice:
      ls = LatticeSymmetry()
      ls.set_lattice(self._indxr_input_lattice)
      ls.set_cell(self._indxr_input_cell)
      ls.generate()
      self._primitive_unit_cell = ls.get_cell('aP')

      Debug.write('Given lattice %s and unit cell:' % \
                  self._indxr_input_lattice)
      Debug.write('%7.2f %7.2f %7.2f %6.2f %6.2f %6.2f' % \
                  tuple(self._indxr_input_cell))
      Debug.write('Derived primitive cell:')

      Debug.write('%7.2f %7.2f %7.2f %6.2f %6.2f %6.2f' % \
                  tuple(self._primitive_unit_cell))

    return

  def _index_select_images(self):
    '''Select correct images based on image headers. This will in
    general use the 20 frames. N.B. only if they have good
    spots on them!'''

    phi_width = self.get_phi_width()
    images = self.get_matching_images()

    # N.B. now bodging this to use up to 20 frames which have decent
    # spots on, spaced from throughout the data set.

    spacing = max(1, int(len(images) // 20))

    selected = []

    for j in range(0, len(images), spacing):
      selected.append(images[j])

    for image in selected[:20]:
      ld = LabelitDistl()
      ld.set_working_directory(self.get_working_directory())
      auto_logfiler(ld)
      ld.add_image(self.get_image_name(image))
      ld.distl()
      spots = ld.get_statistics(
          self.get_image_name(image))['spots_good']
      Debug.write('Image %d good spots %d' % (image, spots))
      if spots > 10:
        self.add_indexer_image_wedge(image)

    return

  def _index(self):
    '''Actually index the diffraction pattern. Note well that
    this is not going to compute the matrix...'''

    # acknowledge this program

    if not self._indxr_images:
      raise RuntimeError, 'No good spots found on any images'

    Citations.cite('labelit')
    Citations.cite('distl')

    _images = []
    for i in self._indxr_images:
      for j in i:
        if not j in _images:
          _images.append(j)

    _images.sort()

    images_str = '%d' % _images[0]
    for i in _images[1:]:
      images_str += ', %d' % i

    cell_str = None
    if self._indxr_input_cell:
      cell_str = '%.2f %.2f %.2f %.2f %.2f %.2f' % \
                  self._indxr_input_cell

    if self._indxr_sweep_name:

      # then this is a proper autoindexing run - describe this
      # to the journal entry

      if len(self._fp_directory) <= 50:
        dirname = self._fp_directory
      else:
        dirname = '...%s' % self._fp_directory[-46:]

      Journal.block(
          'autoindexing', self._indxr_sweep_name, 'labelit',
          {'images':images_str,
           'target cell':cell_str,
           'target lattice':self._indxr_input_lattice,
           'template':self._fp_template,
           'directory':dirname})

    #auto_logfiler(self)

    from xia2.Wrappers.Labelit.LabelitIndex import LabelitIndex
    index = LabelitIndex()
    index.set_working_directory(self.get_working_directory())
    auto_logfiler(index)

    #task = 'Autoindex from images:'

    #for i in _images:
      #task += ' %s' % self.get_image_name(i)

    #self.set_task(task)

    #self.add_command_line('--index_only')

    Debug.write('Indexing from images:')
    for i in _images:
      index.add_image(self.get_image_name(i))
      Debug.write('%s' % self.get_image_name(i))

    if self._indxr_input_lattice and False:
      index.set_space_group_number(
        lattice_to_spacegroup(self._indxr_input_lattice))

    if self._primitive_unit_cell:
      index.set_primitive_unit_cell(self._primitive_unit_cell)

    if self._indxr_input_cell:
      index.set_max_cell(1.25 * max(self._indxr_input_cell[:3]))

    xsweep = self.get_indexer_sweep()
    if xsweep is not None:
      if xsweep.get_distance() is not None:
        index.set_distance(xsweep.get_distance())
      #if self.get_wavelength_prov() == 'user':
        #index.set_wavelength(self.get_wavelength())
      if xsweep.get_beam_centre() is not None:
        index.set_beam_centre(xsweep.get_beam_centre())

    if self._refine_beam is False:
      index.set_refine_beam(False)
    else:
      index.set_refine_beam(True)
      index.set_beam_search_scope(self._beam_search_scope)

    if ((math.fabs(self.get_wavelength() - 1.54) < 0.01) or
        (math.fabs(self.get_wavelength() - 2.29) < 0.01)):
      index.set_Cu_KA_or_Cr_KA(True)

    try:
      index.run()
    except RuntimeError, e:

      if self._refine_beam is False:
        raise e

      # can we improve the situation?

      if self._beam_search_scope < 4.0:
        self._beam_search_scope += 4.0

        # try repeating the indexing!

        self.set_indexer_done(False)
        return 'failed'

      # otherwise this is beyond redemption

      raise e

    self._solutions = index.get_solutions()

    # FIXME this needs to check the smilie status e.g.
    # ":)" or ";(" or "  ".

    # FIXME need to check the value of the RMSD and raise an
    # exception if the P1 solution has an RMSD > 1.0...

    # Change 27/FEB/08 to support user assigned spacegroups
    # (euugh!) have to "ignore" solutions with higher symmetry
    # otherwise the rest of xia will override us. Bummer.

    for i, solution in self._solutions.iteritems():
      if self._indxr_user_input_lattice:
        if (lattice_to_spacegroup(solution['lattice']) >
            lattice_to_spacegroup(self._indxr_input_lattice)):
          Debug.write('Ignoring solution: %s' % solution['lattice'])
          del self._solutions[i]

    # check the RMSD from the triclinic unit cell
    if self._solutions[1]['rmsd'] > 1.0 and False:
      # don't know when this is useful - but I know when it is not!
      raise RuntimeError, 'high RMSD for triclinic solution'

    # configure the "right" solution
    self._solution = self.get_solution()

    # now store also all of the other solutions... keyed by the
    # lattice - however these should only be added if they
    # have a smiley in the appropriate record, perhaps?

    for solution in self._solutions.keys():
      lattice = self._solutions[solution]['lattice']
      if lattice in self._indxr_other_lattice_cell:
        if self._indxr_other_lattice_cell[lattice]['goodness'] < \
           self._solutions[solution]['metric']:
          continue

      self._indxr_other_lattice_cell[lattice] = {
          'goodness':self._solutions[solution]['metric'],
          'cell':self._solutions[solution]['cell']}

    self._indxr_lattice = self._solution['lattice']
    self._indxr_cell = tuple(self._solution['cell'])
    self._indxr_mosaic = self._solution['mosaic']

    lms = LabelitMosflmMatrix()
    lms.set_working_directory(self.get_working_directory())
    lms.set_solution(self._solution['number'])
    self._indxr_payload['mosflm_orientation_matrix'] = lms.calculate()

    # get the beam centre from the mosflm script - mosflm
    # may have inverted the beam centre and labelit will know
    # this!

    mosflm_beam_centre = lms.get_mosflm_beam()

    if mosflm_beam_centre:
      self._indxr_payload['mosflm_beam_centre'] = tuple(mosflm_beam_centre)

    import copy
    detector = copy.deepcopy(self.get_detector())
    beam = copy.deepcopy(self.get_beam())
    from dxtbx.model.detector_helpers import set_mosflm_beam_centre
    set_mosflm_beam_centre(detector, beam, mosflm_beam_centre)

    from xia2.Experts.SymmetryExpert import lattice_to_spacegroup_number
    from scitbx import matrix
    from cctbx import sgtbx, uctbx
    from dxtbx.model.crystal import crystal_model_from_mosflm_matrix
    mosflm_matrix = matrix.sqr(
      [float(i) for line in lms.calculate()
       for i in line.replace("-", " -").split() ][:9])

    space_group = sgtbx.space_group_info(lattice_to_spacegroup_number(
      self._solution['lattice'])).group()
    crystal_model = crystal_model_from_mosflm_matrix(
      mosflm_matrix,
      unit_cell=uctbx.unit_cell(
        tuple(self._solution['cell'])),
      space_group=space_group)

    from dxtbx.model import Experiment, ExperimentList
    experiment = Experiment(beam=beam,
                            detector=detector,
                            goniometer=self.get_goniometer(),
                            scan=self.get_scan(),
                            crystal=crystal_model,
                            )

    experiment_list = ExperimentList([experiment])
    self.set_indexer_experiment_list(experiment_list)

    # also get an estimate of the resolution limit from the
    # labelit.stats_distl output... FIXME the name is wrong!

    lsd = LabelitStats_distl()
    lsd.set_working_directory(self.get_working_directory())
    lsd.stats_distl()

    resolution = 1.0e6
    for i in _images:
      stats = lsd.get_statistics(self.get_image_name(i))

      resol = 0.5 * (stats['resol_one'] + stats['resol_two'])

      if resol < resolution:
        resolution = resol

    self._indxr_resolution_estimate = resolution

    return 'ok'

  def _index_finish(self):
    '''Check that the autoindexing gave a convincing result, and
    if not (i.e. it gave a centred lattice where a primitive one
    would be correct) pick up the correct solution.'''

    # strictly speaking, given the right input there should be
    # no need to test...

    if self._indxr_input_lattice:
      return

    if self.get_indexer_sweep().get_user_lattice():
      return

    status, lattice, matrix, cell = mosflm_check_indexer_solution(
        self)

    if status is None:

      # basis is primitive

      return

    if status is False:

      # basis is centred, and passes test

      return

    # ok need to update internals...

    self._indxr_lattice = lattice
    self._indxr_cell = cell

    Debug.write('Inserting solution: %s ' % lattice +
                '%6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % cell)

    self._indxr_replace(lattice, cell)

    self._indxr_payload['mosflm_orientation_matrix'] = matrix

    return
