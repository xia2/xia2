#!/usr/bin/env python
# XDSIndexerII.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 4th June 2008
#
# An reimplementation of the XDS indexer to work for harder cases, for example
# cases where the whole sweep needs to be read into memory in IDXREF to get
# a decent indexing solution (these do happen) and also cases where the
# crystal is highly mosaic. Perhaps. This will now be directly inherited from
# the original XDSIndexer and only the necessary method overloaded (as I
# should have done this in the first place.)

import os
import sys
import math
import exceptions

# the class that we are extending

from XDSIndexer import XDSIndexer

# helper functions

#from xia2.Wrappers.XDS.XDS import beam_centre_mosflm_to_xds
from xia2.Wrappers.XDS.XDS import beam_centre_xds_to_mosflm
from xia2.Wrappers.XDS.XDS import XDSException
from xia2.Modules.Indexer.XDSCheckIndexerSolution import xds_check_indexer_solution

# odds and sods that are needed

from xia2.lib.bits import auto_logfiler, nint
from xia2.Handlers.Streams import Chatter, Debug, Journal
from xia2.Handlers.Files import FileHandler
from xia2.Handlers.Phil import PhilIndex

class XDSIndexerII(XDSIndexer):
  '''An extension of XDSIndexer using all available images.'''

  def __init__(self):
    super(XDSIndexerII, self).__init__()

    self._index_select_images = 'ii'

    self._i_or_ii = None

    return

  # helper functions

  def _index_select_images_ii(self):
    '''Select correct images based on image headers.'''

    phi_width = self.get_phi_width()

    if phi_width == 0.0:
      raise RuntimeError, 'cannot use still images'

    # use five degrees for the background calculation

    five_deg = int(round(5.0 / phi_width)) - 1

    if five_deg < 5:
      five_deg = 5

    images = self.get_matching_images()

    # characterise the images - are there just two (e.g. dna-style
    # reference images) or is there a full block? if it is the
    # former then we have a problem, as we want *all* the images in the
    # sweep...

    wedges = []

    min_images = PhilIndex.params.xia2.settings.input.min_images

    if len(images) < 3 and len(images) < min_images:
      raise RuntimeError, \
            'This INDEXER cannot be used for only %d images' % \
            len(images)

    Debug.write('Adding images for indexer: %d -> %d' % \
                (min(images), max(images)))

    wedges.append((min(images), max(images)))

    # FIXME this should have a wrapper function!

    if min(images) + five_deg in images:
      self._background_images = (min(images), min(images) + five_deg)
    else:
      self._background_images = (min(images), max(images))

    return wedges

  def _index_prepare(self):
    Chatter.banner('Spotfinding %s' %self.get_indexer_sweep_name())
    super(XDSIndexerII, self)._index_prepare()

    from dials.array_family import flex
    from dials.util.ascii_art import spot_counts_per_image_plot
    reflection_pickle = spot_xds_to_reflection_pickle(
      self._indxr_payload['SPOT.XDS'],
      working_directory=self.get_working_directory())
    refl = flex.reflection_table.from_pickle(reflection_pickle)
    Chatter.write(spot_counts_per_image_plot(refl), strip=False)


  def _index(self):
    '''Actually do the autoindexing using the data prepared by the
    previous method.'''

    images_str = '%d to %d' % tuple(self._indxr_images[0])
    for i in self._indxr_images[1:]:
      images_str += ', %d to %d' % tuple(i)

    cell_str = None
    if self._indxr_input_cell:
      cell_str = '%.2f %.2f %.2f %.2f %.2f %.2f' % \
                 self._indxr_input_cell

    # then this is a proper autoindexing run - describe this
    # to the journal entry

    #if len(self._fp_directory) <= 50:
      #dirname = self._fp_directory
    #else:
      #dirname = '...%s' % self._fp_directory[-46:]
    dirname = self.get_directory()

    Journal.block('autoindexing', self._indxr_sweep_name, 'XDS',
                  {'images':images_str,
                   'target cell':cell_str,
                   'target lattice':self._indxr_input_lattice,
                   'template':self.get_template(),
                   'directory':dirname})

    idxref = self.Idxref()

    self._index_remove_masked_regions()
    for file in ['SPOT.XDS']:
      idxref.set_input_data_file(file, self._indxr_payload[file])

    idxref.set_data_range(self._indxr_images[0][0],
                          self._indxr_images[0][1])
    idxref.set_background_range(self._indxr_images[0][0],
                                self._indxr_images[0][1])

    # set the phi start etc correctly

    if self._i_or_ii is None:
      self._i_or_ii = self.decide_i_or_ii()
      Debug.write('Selecting I or II, chose %s' % self._i_or_ii)

    if self._i_or_ii == 'i':
      blocks = self._index_select_images_i()
      for block in blocks[:1]:
        starting_frame = block[0]
        starting_angle = self.get_scan().get_angle_from_image_index(starting_frame)

        idxref.set_starting_frame(starting_frame)
        idxref.set_starting_angle(starting_angle)

        idxref.add_spot_range(block[0], block[1])

      for block in blocks[1:]:
        idxref.add_spot_range(block[0], block[1])
    else:
      for block in self._indxr_images[:1]:
        starting_frame = block[0]
        starting_angle = self.get_scan().get_angle_from_image_index(starting_frame)

        idxref.set_starting_frame(starting_frame)
        idxref.set_starting_angle(starting_angle)

        idxref.add_spot_range(block[0], block[1])

      for block in self._indxr_images[1:]:
        idxref.add_spot_range(block[0], block[1])

    # FIXME need to also be able to pass in the known unit
    # cell and lattice if already available e.g. from
    # the helper... indirectly

    if self._indxr_user_input_lattice:
      idxref.set_indexer_user_input_lattice(True)

    if self._indxr_input_lattice and self._indxr_input_cell:
      idxref.set_indexer_input_lattice(self._indxr_input_lattice)
      idxref.set_indexer_input_cell(self._indxr_input_cell)

      Debug.write('Set lattice: %s' % self._indxr_input_lattice)
      Debug.write('Set cell: %f %f %f %f %f %f' % \
                  self._indxr_input_cell)

      original_cell = self._indxr_input_cell
    elif self._indxr_input_lattice:
      idxref.set_indexer_input_lattice(self._indxr_input_lattice)
      original_cell = None
    else:
      original_cell = None

    # FIXED need to set the beam centre here - this needs to come
    # from the input .xinfo object or header, and be converted
    # to the XDS frame... done.

    #mosflm_beam_centre = self.get_beam_centre()
    #xds_beam_centre = beam_centre_mosflm_to_xds(
        #mosflm_beam_centre[0], mosflm_beam_centre[1], self.get_header())
    from dxtbx.serialize.xds import to_xds
    converter = to_xds(self.get_imageset())
    xds_beam_centre = converter.detector_origin

    idxref.set_beam_centre(xds_beam_centre[0],
                           xds_beam_centre[1])

    # fixme need to check if the lattice, cell have been set already,
    # and if they have, pass these in as input to the indexing job.

    done = False

    while not done:
      try:
        done = idxref.run()

        # N.B. in here if the IDXREF step was being run in the first
        # pass done is FALSE however there should be a refined
        # P1 orientation matrix etc. available - so keep it!

      except XDSException, e:
        # inspect this - if we have complaints about not
        # enough reflections indexed, and we have a target
        # unit cell, and they are the same, well ignore it

        if 'solution is inaccurate' in str(e):
          Debug.write(
              'XDS complains solution inaccurate - ignoring')
          done = idxref.continue_from_error()
        elif ('insufficient percentage (< 70%)' in str(e) or
              'insufficient percentage (< 50%)' in str(e)) and \
                 original_cell:
          done = idxref.continue_from_error()
          lattice, cell, mosaic = \
                   idxref.get_indexing_solution()
          # compare solutions
          check = PhilIndex.params.xia2.settings.xds_check_cell_deviation
          for j in range(3):
            # allow two percent variation in unit cell length
            if math.fabs((cell[j] - original_cell[j]) / \
                         original_cell[j]) > 0.02 and check:
              Debug.write('XDS unhappy and solution wrong')
              raise e
            # and two degree difference in angle
            if math.fabs(cell[j + 3] - original_cell[j + 3]) \
                   > 2.0 and check:
              Debug.write('XDS unhappy and solution wrong')
              raise e
          Debug.write('XDS unhappy but solution ok')
        elif 'insufficient percentage (< 70%)' in str(e) or \
                 'insufficient percentage (< 50%)' in str(e):
          Debug.write('XDS unhappy but solution probably ok')
          done = idxref.continue_from_error()
        else:
          raise e

    FileHandler.record_log_file('%s INDEX' % self.get_indexer_full_name(),
                                os.path.join(self.get_working_directory(),
                                             'IDXREF.LP'))

    for file in ['SPOT.XDS',
                 'XPARM.XDS']:
      self._indxr_payload[file] = idxref.get_output_data_file(file)

    # need to get the indexing solutions out somehow...

    self._indxr_other_lattice_cell = idxref.get_indexing_solutions()

    self._indxr_lattice, self._indxr_cell, self._indxr_mosaic = \
                         idxref.get_indexing_solution()

    import dxtbx
    from dxtbx.serialize.xds import to_crystal
    xparm_file = os.path.join(self.get_working_directory(), 'XPARM.XDS')
    models = dxtbx.load(xparm_file)
    crystal_model = to_crystal(xparm_file)

    from dxtbx.model.experiment.experiment_list import Experiment, ExperimentList
    experiment = Experiment(beam=models.get_beam(),
                            detector=models.get_detector(),
                            goniometer=models.get_goniometer(),
                            scan=models.get_scan(),
                            crystal=crystal_model,
                            #imageset=self.get_imageset(),
                            )

    experiment_list = ExperimentList([experiment])
    self.set_indexer_experiment_list(experiment_list)

    # I will want this later on to check that the lattice was ok
    self._idxref_subtree_problem = idxref.get_index_tree_problem()

    return

  def decide_i_or_ii(self):
    Debug.write('Testing II or I indexing')

    try:
      fraction_etc_i = self.test_i()
      fraction_etc_ii = self.test_ii()

      if not fraction_etc_i and fraction_etc_ii:
        return 'ii'
      if fraction_etc_i and not fraction_etc_ii:
        return 'i'

      Debug.write('I:  %.2f %.2f %.2f' % fraction_etc_i)
      Debug.write('II: %.2f %.2f %.2f' % fraction_etc_ii)

      if fraction_etc_i[0] > fraction_etc_ii[0] and \
          fraction_etc_i[1] < fraction_etc_ii[1] and \
          fraction_etc_i[2] < fraction_etc_ii[2]:
        return 'i'

      return 'ii'

    except exceptions.Exception, e:
      Debug.write(str(e))
      return 'ii'

  def test_i(self):
    idxref = self.Idxref()

    self._index_remove_masked_regions()
    for file in ['SPOT.XDS']:
      idxref.set_input_data_file(file, self._indxr_payload[file])

    idxref.set_data_range(self._indxr_images[0][0],
                          self._indxr_images[0][1])
    idxref.set_background_range(self._indxr_images[0][0],
                                self._indxr_images[0][1])

    # set the phi start etc correctly

    blocks = self._index_select_images_i()

    for block in blocks[:1]:
      starting_frame = block[0]
      starting_angle = self.get_scan().get_angle_from_image_index(starting_frame)

      idxref.set_starting_frame(starting_frame)
      idxref.set_starting_angle(starting_angle)

      idxref.add_spot_range(block[0], block[1])

    for block in blocks[1:]:
      idxref.add_spot_range(block[0], block[1])

    #mosflm_beam_centre = self.get_beam_centre()
    #xds_beam_centre = beam_centre_mosflm_to_xds(
        #mosflm_beam_centre[0], mosflm_beam_centre[1], self.get_header())
    from dxtbx.serialize.xds import to_xds
    converter = to_xds(self.get_imageset())
    xds_beam_centre = converter.detector_origin

    idxref.set_beam_centre(xds_beam_centre[0],
                           xds_beam_centre[1])

    idxref.run()

    return idxref.get_fraction_rmsd_rmsphi()

  def test_ii(self):
    idxref = self.Idxref()

    self._index_remove_masked_regions()
    for file in ['SPOT.XDS']:
      idxref.set_input_data_file(file, self._indxr_payload[file])

    idxref.set_data_range(self._indxr_images[0][0],
                          self._indxr_images[0][1])
    idxref.set_background_range(self._indxr_images[0][0],
                                self._indxr_images[0][1])

    for block in self._indxr_images[:1]:
      starting_frame = block[0]
      starting_angle = self.get_scan().get_angle_from_image_index(starting_frame)

      idxref.set_starting_frame(starting_frame)
      idxref.set_starting_angle(starting_angle)

      idxref.add_spot_range(block[0], block[1])

    #mosflm_beam_centre = self.get_beam_centre()
    #xds_beam_centre = beam_centre_mosflm_to_xds(
        #mosflm_beam_centre[0], mosflm_beam_centre[1], self.get_header())
    from dxtbx.serialize.xds import to_xds
    converter = to_xds(self.get_imageset())
    xds_beam_centre = converter.detector_origin

    idxref.set_beam_centre(xds_beam_centre[0],
                           xds_beam_centre[1])

    idxref.run()

    return idxref.get_fraction_rmsd_rmsphi()


def spot_xds_to_reflection_pickle(spot_xds, working_directory):
  from xia2.Wrappers.Dials.ImportXDS import ImportXDS
  importer = ImportXDS()
  importer.set_working_directory(working_directory)
  auto_logfiler(importer)
  importer.set_spot_xds(spot_xds)
  importer.run()
  return importer.get_reflection_filename()
