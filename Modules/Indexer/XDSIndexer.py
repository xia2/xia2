#!/usr/bin/env python
# XDSIndexer.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
# 13th December 2006
#
# An implementation of the Indexer interface using XDS. This depends on the
# XDS wrappers to actually implement the functionality.
#
# 03/JAN/07 FIXME - once the indexing step is complete, all of the files
#                   which are needed for integration should be placed in the
#                   indexer "payload".

import os
import sys
import math
import shutil

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

# wrappers for programs that this needs

from Wrappers.XDS.XDSXycorr import XDSXycorr as _Xycorr
from Wrappers.XDS.XDSInit import XDSInit as _Init
from Wrappers.XDS.XDSColspot import XDSColspot as _Colspot
from Wrappers.XDS.XDSIdxref import XDSIdxref as _Idxref
from Wrappers.XDS.XDS import xds_read_xparm

from Wrappers.XIA.Diffdump import Diffdump

# helper functions

from Wrappers.XDS.XDS import beam_centre_mosflm_to_xds
from Wrappers.XDS.XDS import beam_centre_xds_to_mosflm
from Wrappers.XDS.XDS import XDSException
from Modules.Indexer.XDSCheckIndexerSolution import xds_check_indexer_solution

from Toolkit.MendBKGINIT import recompute_BKGINIT

# interfaces that this must implement to be an indexer

from Schema.Interfaces.Indexer import Indexer
from Schema.Interfaces.FrameProcessor import FrameProcessor

# odds and sods that are needed

from lib.bits import auto_logfiler, nint
from Handlers.Streams import Chatter, Debug, Journal
from Handlers.Flags import Flags
from Handlers.Phil import PhilIndex
from Handlers.Files import FileHandler

class XDSIndexer(FrameProcessor,
                 Indexer):
    '''An implementation of the Indexer interface using XDS.'''

    def __init__(self):

        # set up the inherited objects

        FrameProcessor.__init__(self)
        Indexer.__init__(self)

        # check that the programs exist - this will raise an exception if
        # they do not...

        idxref = _Idxref()

        # admin junk
        self._working_directory = os.getcwd()

        self._background_images = None
        self._index_select_images = self._index_select_images_i

        # place to store working data
        self._data_files = { }

        return

    # admin functions

    def set_working_directory(self, working_directory):
        self._working_directory = working_directory
        return

    def get_working_directory(self):
        return self._working_directory

    # factory functions

    def Xycorr(self):
        xycorr = _Xycorr()
        xycorr.set_working_directory(self.get_working_directory())

        xycorr.setup_from_image(self.get_image_name(
            self._indxr_images[0][0]))

        if self.get_distance():
            xycorr.set_distance(self.get_distance())

        if self.get_wavelength():
            xycorr.set_wavelength(self.get_wavelength())

        auto_logfiler(xycorr, 'XYCORR')

        return xycorr

    def Init(self):
        from Handlers.Phil import PhilIndex
        init = _Init(params=PhilIndex.params.xds.init)
        init.set_working_directory(self.get_working_directory())

        init.setup_from_image(self.get_image_name(
            self._indxr_images[0][0]))

        if self.get_distance():
            init.set_distance(self.get_distance())

        if self.get_wavelength():
            init.set_wavelength(self.get_wavelength())

        auto_logfiler(init, 'INIT')

        return init

    def Colspot(self):
        colspot = _Colspot()
        colspot.set_working_directory(self.get_working_directory())

        colspot.setup_from_image(self.get_image_name(
            self._indxr_images[0][0]))

        if self.get_distance():
            colspot.set_distance(self.get_distance())

        if self.get_wavelength():
            colspot.set_wavelength(self.get_wavelength())

        auto_logfiler(colspot, 'COLSPOT')

        return colspot

    def DialsSpotfinder(self):
        from Wrappers.Dials.Spotfinder import Spotfinder
        spotfinder = Spotfinder(params=PhilIndex.params.dials.spotfinder)
        spotfinder.set_working_directory(self.get_working_directory())
        spotfinder.setup_from_image(self.get_image_name(
            self._indxr_images[0][0]))

        auto_logfiler(spotfinder, 'SPOTFINDER')

        return spotfinder

    def DialsExportSpotXDS(self):
        from Wrappers.Dials.ExportSpotXDS import ExportSpotXDS
        export = ExportSpotXDS()
        export.set_working_directory(self.get_working_directory())
        return export

    def Idxref(self):
        from Handlers.Phil import PhilIndex
        idxref = _Idxref(params=PhilIndex.params.xds.index)
        idxref.set_working_directory(self.get_working_directory())

        idxref.setup_from_image(self.get_image_name(
            self._indxr_images[0][0]))

        if self.get_distance():
            idxref.set_distance(self.get_distance())

        if self.get_wavelength():
            idxref.set_wavelength(self.get_wavelength())

        # reverse phi?
        if self.get_reversephi():
            Debug.write('Setting reversephi for IDXREF')
            idxref.set_reversephi()

        # if we have a refined set of parameters to apply, apply these
        if Flags.get_xparm():
            idxref.set_refined_origin(Flags.get_xparm_origin())
            idxref.set_refined_beam_vector(Flags.get_xparm_beam_vector())
            idxref.set_refined_rotation_axis(Flags.get_xparm_rotation_axis())
            idxref.set_refined_distance(Flags.get_xparm_distance())

        # hacks for Jira 493

        if Flags.get_xparm_a():
            idxref.set_a_axis(Flags.get_xparm_a())
        if Flags.get_xparm_b():
            idxref.set_b_axis(Flags.get_xparm_b())
        if Flags.get_xparm_c():
            idxref.set_c_axis(Flags.get_xparm_c())

        auto_logfiler(idxref, 'IDXREF')

        return idxref

    # helper functions

    def _index_remove_masked_regions(self):
        if not PhilIndex.params.xia2.settings.untrusted_rectangle_indexing:
            return

        limits = PhilIndex.params.xia2.settings.untrusted_rectangle_indexing
        spot_xds = ''
        removed = 0
        for record in self._data_files['SPOT.XDS'].split('\n'):
            if not record.strip():
                continue
            x, y, phi, i = map(float, record.split()[:4])
            if x > limits[0] and x < limits[1] and \
                y > limits[2] and y < limits[3]:
                removed += 1
                continue
            spot_xds += '%s\n' % record

        Debug.write('Removed %d peaks from SPOT.XDS' % removed)
        self._data_files['SPOT.XDS'] = spot_xds
        return

    def _index_select_images_i(self):
        '''Select correct images based on image headers.'''

        phi_width = self.get_header_item('phi_width')

        if phi_width == 0.0:
            Debug.write('Phi width 0.0? Assuming 1.0!')
            phi_width = 1.0

        images = self.get_matching_images()

        # characterise the images - are there just two (e.g. dna-style
        # reference images) or is there a full block?

        wedges = []

        if len(images) < 3:
            # work on the assumption that this is a reference pair

            wedges.append(images[0])

            if len(images) > 1:
                wedges.append(images[1])

        else:
            block_size = 5

            Debug.write('Adding images for indexer: %d -> %d' % \
                        (images[0], images[block_size] - 1))

            wedges.append((images[0], images[block_size] - 1))

            if int(90.0 / phi_width) + block_size in images:
                # assume we can add a wedge around 45 degrees as well...
                Debug.write('Adding images for indexer: %d -> %d' % \
                            (int(45.0 / phi_width) + images[0],
                             int(45.0 / phi_width) + images[0] +
                             block_size - 1))
                Debug.write('Adding images for indexer: %d -> %d' % \
                            (int(90.0 / phi_width) + images[0],
                             int(90.0 / phi_width) + images[0] +
                             block_size - 1))
                wedges.append(
                    (int(45.0 / phi_width) + images[0],
                     int(45.0 / phi_width) + images[0] + block_size - 1))
                wedges.append(
                    (int(90.0 / phi_width) + images[0],
                     int(90.0 / phi_width) + images[0] + block_size - 1))

            else:

                # add some half-way anyway
                first = (len(images) // 2) - (block_size // 2) + images[0] - 1
                last = first + block_size - 1

                Debug.write('Adding images for indexer: %d -> %d' % \
                            (first, last))
                wedges.append((first, last))
                Debug.write('Adding images for indexer: %d -> %d' % \
                            (images[- block_size], images[-1]))
                wedges.append((images[- block_size], images[-1]))

        return wedges

    # do-er functions

    def _index_prepare(self):
        '''Prepare to do autoindexing - in XDS terms this will mean
        calling xycorr, init and colspot on the input images.'''

        # decide on images to work with

        Debug.write('XDS INDEX PREPARE:')
        Debug.write('Wavelength: %.6f' % self.get_wavelength())
        Debug.write('Distance: %.2f' % self.get_distance())

        if self._indxr_images == []:
            # note well that this may reset the "done" flag so
            # override this...
            wedges = self._index_select_images()
            for wedge in wedges:
                self.add_indexer_image_wedge(wedge)
            self.set_indexer_prepare_done(True)

        all_images = self.get_matching_images()

        first = min(all_images)
        last = max(all_images)

        # next start to process these - first xycorr

        xycorr = self.Xycorr()

        xycorr.set_data_range(first, last)
        xycorr.set_background_range(self._indxr_images[0][0],
                                    self._indxr_images[0][1])
        mosflm_beam_centre = self.get_beam()
        xds_beam_centre = beam_centre_mosflm_to_xds(
            mosflm_beam_centre[0], mosflm_beam_centre[1], self.get_header())
        xycorr.set_beam_centre(xds_beam_centre[0],
                               xds_beam_centre[1])
        for block in self._indxr_images:
            xycorr.add_spot_range(block[0], block[1])

        # FIXME need to set the origin here

        xycorr.run()

        for file in ['X-CORRECTIONS.cbf',
                     'Y-CORRECTIONS.cbf']:
            self._data_files[file] = xycorr.get_output_data_file(file)

        # next start to process these - then init

        init = self.Init()

        for file in ['X-CORRECTIONS.cbf',
                     'Y-CORRECTIONS.cbf']:
            init.set_input_data_file(file, self._data_files[file])

        init.set_data_range(first, last)

        if self._background_images:
            init.set_background_range(self._background_images[0],
                                      self._background_images[1])
        else:
            init.set_background_range(self._indxr_images[0][0],
                                      self._indxr_images[0][1])

        for block in self._indxr_images:
            init.add_spot_range(block[0], block[1])

        init.run()

        # at this stage, need to (perhaps) modify the BKGINIT.cbf image
        # to mark out the back stop

        if Flags.get_mask():

            Debug.write('Applying mask to BKGINIT.pck')

            # copy the original file
            cbf_old = os.path.join(init.get_working_directory(),
                                   'BKGINIT.cbf')
            cbf_save = os.path.join(init.get_working_directory(),
                                    'BKGINIT.sav')
            shutil.copyfile(cbf_old, cbf_save)

            # modify the file to give the new mask
            Flags.get_mask().apply_mask_xds(self.get_header(),
                                            cbf_save, cbf_old)

            init.reload()

        for file in ['BLANK.cbf',
                     'BKGINIT.cbf',
                     'GAIN.cbf']:
            self._data_files[file] = init.get_output_data_file(file)

        if PhilIndex.params.xia2.settings.developmental.use_dials_spotfinder:

            spotfinder = self.DialsSpotfinder()

            for block in self._indxr_images:
                spotfinder.add_spot_range(block[0], block[1])

            spotfinder.run()
            export = self.DialsExportSpotXDS()
            export.set_input_data_file(
                'reflections.pickle',
                spotfinder.get_output_data_file('reflections.pickle'))
            export.run()

            for file in ['SPOT.XDS']:
                self._data_files[file] = export.get_output_data_file(file)

        else:

            # next start to process these - then colspot

            colspot = self.Colspot()

            for file in ['X-CORRECTIONS.cbf',
                         'Y-CORRECTIONS.cbf',
                         'BLANK.cbf',
                         'BKGINIT.cbf',
                         'GAIN.cbf']:
                colspot.set_input_data_file(file, self._data_files[file])

            colspot.set_data_range(first, last)
            colspot.set_background_range(self._indxr_images[0][0],
                                         self._indxr_images[0][1])
            for block in self._indxr_images:
                colspot.add_spot_range(block[0], block[1])

            colspot.run()

            for file in ['SPOT.XDS']:
                self._data_files[file] = colspot.get_output_data_file(file)

        # that should be everything prepared... all of the important
        # files should be loaded into memory to be able to cope with
        # integration happening somewhere else

        return

    def _index(self):
        '''Actually do the autoindexing using the data prepared by the
        previous method.'''

        images_str = '%d to %d' % self._indxr_images[0]
        for i in self._indxr_images[1:]:
            images_str += ', %d to %d' % i

        cell_str = None
        if self._indxr_input_cell:
            cell_str = '%.2f %.2f %.2f %.2f %.2f %.2f' % \
                       self._indxr_input_cell

        # then this is a proper autoindexing run - describe this
        # to the journal entry

        if len(self._fp_directory) <= 50:
            dirname = self._fp_directory
        else:
            dirname = '...%s' % self._fp_directory[-46:]

        Journal.block('autoindexing', self._indxr_sweep_name, 'XDS',
                      {'images':images_str,
                       'target cell':cell_str,
                       'target lattice':self._indxr_input_lattice,
                       'template':self._fp_template,
                       'directory':dirname})

        idxref = self.Idxref()

        self._index_remove_masked_regions()
        for file in ['SPOT.XDS']:
            idxref.set_input_data_file(file, self._data_files[file])

        # edit SPOT.XDS to remove reflections in untrusted regions of the detector

        idxref.set_data_range(self._indxr_images[0][0],
                              self._indxr_images[0][1])
        idxref.set_background_range(self._indxr_images[0][0],
                                    self._indxr_images[0][1])

        # set the phi start etc correctly

        for block in self._indxr_images[:1]:
            starting_frame = block[0]

            dd = Diffdump()
            dd.set_image(self.get_image_name(starting_frame))
            starting_angle = dd.readheader()['phi_start']

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

        mosflm_beam_centre = self.get_beam()
        xds_beam_centre = beam_centre_mosflm_to_xds(
            mosflm_beam_centre[0], mosflm_beam_centre[1], self.get_header())

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
                    done = idxref.run(ignore_errors = True)
                elif ('insufficient percentage (< 70%)' in str(e) or
                      'insufficient percentage (< 50%)' in str(e)) and \
                         original_cell:
                    done = idxref.run(ignore_errors = True)
                    lattice, cell, mosaic = \
                             idxref.get_indexing_solution()
                    # compare solutions
                    for j in range(3):
                        # allow two percent variation in unit cell length
                        if math.fabs((cell[j] - original_cell[j]) / \
                                     original_cell[j]) > 0.02 and \
                                     not Flags.get_relax():
                            Debug.write('XDS unhappy and solution wrong')
                            raise e
                        # and two degree difference in angle
                        if math.fabs(cell[j + 3] - original_cell[j + 3]) \
                               > 2.0 and not Flags.get_relax():
                            Debug.write('XDS unhappy and solution wrong')
                            raise e
                    Debug.write('XDS unhappy but solution ok')
                elif 'insufficient percentage (< 70%)' in str(e) or \
                         'insufficient percentage (< 50%)' in str(e):
                    done = idxref.run(ignore_errors = True)
                    Debug.write('XDS unhappy but solution probably ok')
                else:
                    raise e

        sweep = self.get_indexer_sweep_name()
        FileHandler.record_log_file('%s INDEX' % (sweep),
                                    os.path.join(self.get_working_directory(),
                                                 'IDXREF.LP'))

        for file in ['SPOT.XDS',
                     'XPARM.XDS']:
            self._data_files[file] = idxref.get_output_data_file(file)

        # need to get the indexing solutions out somehow...

        self._indxr_other_lattice_cell = idxref.get_indexing_solutions()

        self._indxr_lattice, self._indxr_cell, self._indxr_mosaic = \
                             idxref.get_indexing_solution()

        self._indxr_refined_beam = beam_centre_xds_to_mosflm(
            idxref.get_refined_beam()[0], idxref.get_refined_beam()[1],
            self.get_header())
        self._indxr_refined_distance = idxref.get_refined_distance()

        self._indxr_payload['xds_files'] = self._data_files

        # I will want this later on to check that the lattice was ok
        self._idxref_subtree_problem = idxref.get_index_tree_problem()

        return

    def _index_finish(self):
        '''Perform the indexer post-processing as required.'''

        # ok, in here now ask if this solution was sensible!

        if not self.get_indexer_sweep().get_user_lattice():

            lattice = self._indxr_lattice
            cell = self._indxr_cell

            lattice2, cell2 = xds_check_indexer_solution(
                os.path.join(self.get_working_directory(), 'XPARM.XDS'),
                os.path.join(self.get_working_directory(), 'SPOT.XDS'))

            Debug.write('Centring analysis: %s => %s' % \
                        (lattice, lattice2))

            doubled_lattice = False
            for j in range(3):
                if int(round(cell2[j] / cell[j])) == 2:
                    doubled_lattice = True
                    axes = 'A', 'B', 'C'
                    Debug.write('Lattice axis doubled: %s' % axes[j])

            if (self._idxref_subtree_problem and (lattice2 != lattice)) or \
                   doubled_lattice:

                # hmm.... looks like we don't agree on the correct result...
                # update the putative correct result as input

                Debug.write('Detected pseudocentred lattice')
                Debug.write('Inserting solution: %s ' % lattice2 +
                            '%6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % cell2)

                self._indxr_replace(lattice2, cell2)

                Debug.write('Set lattice: %s' % lattice2)
                Debug.write('Set cell: %f %f %f %f %f %f' % \
                            cell2)

                # then rerun

                self.set_indexer_done(False)
                return

        # finally read through SPOT.XDS and XPARM.XDS to get an estimate
        # of the low resolution limit - this should be pretty straightforward
        # since what I want is the resolution of the lowest resolution indexed
        # spot..

        # first parse the numbers from the IDXREF XPARM file

        xparm_dict = xds_read_xparm(os.path.join(self.get_working_directory(),
                                                 'XPARM.XDS'))

        distance = xparm_dict['distance']
        wavelength = xparm_dict['wavelength']
        pixel = xparm_dict['px'], xparm_dict['py']
        beam = xparm_dict['ox'], xparm_dict['oy']

        if distance < 0.0:
            distance *= -1

        # then work through the spot list to find the lowest resolution spot

        dmax = 0.0

        for record in self._data_files['SPOT.XDS'].split('\n'):
            data = map(float, record.split())

            if not data:
                continue

            h, k, l = map(nint, data[4:7])

            if h == 0 and k == 0 and l == 0:
                # this reflection was not indexed
                continue

            x = data[0]
            y = data[1]

            dx = pixel[0] * (x - beam[0])
            dy = pixel[1] * (y - beam[1])

            d = math.sqrt(dx * dx + dy * dy)

            theta = 0.5 * math.atan(d / distance)

            ds = wavelength / (2.0 * math.sin(theta))

            if ds > dmax:
                dmax = ds

        Debug.write('Low resolution limit assigned as: %.2f' % dmax)
        self._indxr_low_resolution = dmax

        return

if __name__ == '__main_old__':

    # run a demo test

    if not os.environ.has_key('XIA2_ROOT'):
        raise RuntimeError, 'XIA2_ROOT not defined'

    xi = XDSIndexer()

    directory = os.path.join(os.environ['XIA2_ROOT'],
                             'Data', 'Test', 'Images')

    # directory = '/data/graeme/12287'
    xi.setup_from_image(os.path.join(directory, '12287_1_E1_001.img'))
    xi.set_beam((108.9, 105.0))

    xi.index()

    print 'Refined beam is: %6.2f %6.2f' % xi.get_indexer_beam()
    print 'Distance:        %6.2f' % xi.get_indexer_distance()
    print 'Cell: %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % xi.get_indexer_cell()
    print 'Lattice: %s' % xi.get_indexer_lattice()
    print 'Mosaic: %6.2f' % xi.get_indexer_mosaic()


if __name__ == '__main__':

    xi = XDSIndexer()

    directory = os.path.join('/data', 'graeme', 'insulin', 'demo')

    xi.setup_from_image(os.path.join(directory, 'insulin_1_001.img'))

    xi.index()

    print 'Refined beam is: %6.2f %6.2f' % xi.get_indexer_beam()
    print 'Distance:        %6.2f' % xi.get_indexer_distance()
    print 'Cell: %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % xi.get_indexer_cell()
    print 'Lattice: %s' % xi.get_indexer_lattice()
    print 'Mosaic: %6.2f' % xi.get_indexer_mosaic()
