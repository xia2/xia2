#!/usr/bin/env python
# LabelitScreen.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 2nd June 2006
# 
# A wrapper for labelit.screen - this will provide functionality to:
#
# Decide the beam centre.
# Index the lattce.
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
#                 fit in with LabelitMosflmScript.
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

import os
import sys
import copy
import math

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'],
                    'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                                 'Python'))
    
if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Driver.DriverFactory import DriverFactory

from Handlers.Syminfo import Syminfo

# interfaces that this inherits from ...
from Schema.Interfaces.FrameProcessor import FrameProcessor
from Schema.Interfaces.Indexer import Indexer

# other labelit things that this uses
from Wrappers.Labelit.LabelitMosflmScript import LabelitMosflmScript
from Wrappers.Labelit.LabelitStats_distl import LabelitStats_distl

from lib.Guff import auto_logfiler
from Handlers.Streams import Chatter, Debug
from Handlers.Citations import Citations

def LabelitScreen(DriverType = None):
    '''Factory for LabelitScreen wrapper classes, with the specified
    Driver type.'''

    DriverInstance = DriverFactory.Driver(DriverType)

    class LabelitScreenWrapper(DriverInstance.__class__,
                               FrameProcessor,
                               Indexer):
        '''A wrapper for the program labelit.screen - which will provide
        functionality for deciding the beam centre and indexing the
        diffraction pattern.'''

        def __init__(self):

            DriverInstance.__class__.__init__(self)
            
            # interface constructor calls
            FrameProcessor.__init__(self)
            Indexer.__init__(self)

            self.set_executable('labelit.screen')

            # control over the behaviour

            self._refine_beam = True

            # this is linked to the above!
            
            self._beam_search_scope = 0.0

            self._solutions = { }

            self._solution = None

            return

        # this is not defined in the Indexer interface :o(
        # FIXME should it be???

        def set_refine_beam(self, refine_beam):
            self._refine_beam = refine_beam
            return

        def _write_dataset_preferences(self):
            '''Write the dataset_preferences.py file in the working
            directory - this will include the beam centres etc.'''

            out = open(os.path.join(self.get_working_directory(),
                                    'dataset_preferences.py'), 'w')

            # only write things out if they have been overridden
            # from what is in the header...

            if self.get_distance_prov() == 'user':
                out.write('autoindex_override_distance = %f\n' %
                          self.get_distance())
            if self.get_wavelength_prov() == 'user':
                out.write('autoindex_override_wavelength = %f\n' %
                          self.get_wavelength())
            if self.get_beam_prov() == 'user':
                out.write('autoindex_override_beam = (%f, %f)\n' % \
                          self.get_beam())
            if self._refine_beam is False:
                out.write('beam_search_scope = 0.0\n')
            else:
                # FIXME latest version of labelit has messed up the beam
                # centre finding :o( so add this for the moment until that
                # is fixed
                
                out.write('beam_search_scope = %f\n' % \
                          self._beam_search_scope)

            # check to see if this is an image plate *or* the
            # wavelength corresponds to Cu KA (1.54A) or Cr KA (2.29 A).
            # numbers from rigaku americas web page.

            if math.fabs(self.get_wavelength() - 1.54) < 0.01:
                out.write('distl_force_binning = True')
                out.write('distl_profile_bumpiness = 10\n')
                out.write('distl_binned_image_spot_size = 10\n')
            if math.fabs(self.get_wavelength() - 2.29) < 0.01:
                out.write('distl_force_binning = True')
                out.write('distl_profile_bumpiness = 10\n')
                out.write('distl_binned_image_spot_size = 10\n')

            # presume that we won't be using more than four
            # images...
            out.write('wedgelimit = 4\n')

            # new feature - index on the spot centre of mass, not the
            # highest pixel (should improve the RMS deviation reports.)

            out.write('distl_spotfinder_algorithm = "maximum_pixel"\n')

            # 03/NOV/06 looks like this can be "fixed" by the following:
            # out.write('percent_overlap_forcing_detail = 1\n')
            # nope!
            
            out.close()

            return

        def check_labelit_errors(self):
            '''Check through the standard output for error reports.'''

            output = self.get_all_output()

            for o in output:
                if 'No_Indexing_Solution' in o:
                    raise RuntimeError, 'indexing failed: %s' % \
                          o.split(':')[-1].strip()
                if 'InputFileError' in o:
                    raise RuntimeError, 'indexing failed: %s' % \
                          o.split(':')[-1].strip()
                if 'INDEXING UNRELIABLE' in o:
                    raise RuntimeError, 'indexing failed: %s' % \
                          o.split(':')[-1].strip()
                    
            return

        def _index_prepare(self):
            # prepare to do some autoindexing
            
            if self._indxr_images == []:
                self._index_select_images()
            return

        def _index_select_images(self):
            '''Select correct images based on image headers.'''

            # FIXME perhaps this should be somewhere central, because
            # Mosflm will share the same implementation

            phi_width = self.get_header_item('phi_width')
            images = self.get_matching_images()

            if len(images) < 4:
                for image in images:
                    self.add_indexer_image_wedge(image)

                return

            Debug.write('Selected image %s' % images[0])

            self.add_indexer_image_wedge(images[0])

            # FIXME what to do if phi_width is recorded as zero?
            # perhaps assume that it is 1.0!

            if phi_width == 0.0:
                Chatter.write('Phi width 0.0? Assuming 1.0!')
                phi_width = 1.0

            if int(90.0 / phi_width) in images:
                Debug.write('Selected image %s' % int(45.0 / phi_width))
                Debug.write('Selected image %s' % int(90.0 / phi_width))
                self.add_indexer_image_wedge(int(45.0 / phi_width))
                self.add_indexer_image_wedge(int(90.0 / phi_width))
            else:
                middle = len(images) / 2
                if len(images) >= 3:
                    Debug.write('Selected image %s' % images[middle])
                    self.add_indexer_image_wedge(images[middle])
                Debug.write('Selected image %s' % images[-1])
                self.add_indexer_image_wedge(images[-1])

            return

        def _index(self):
            '''Actually index the diffraction pattern. Note well that
            this is not going to compute the matrix...'''

            # acknowledge this program

            Citations.cite('labelit')
            Citations.cite('distl')

            self.reset()

            _images = []
            for i in self._indxr_images:
                for j in i:
                    if not j in _images:
                        _images.append(j)
                    
            _images.sort()

            if len(_images) > 4:
                raise RuntimeError, 'cannot use more than 4 images'

            auto_logfiler(self)

            task = 'Autoindex from images:'

            for i in _images:
                task += ' %s' % self.get_image_name(i)

            self.set_task(task)

            self.add_command_line('--index_only')

            Debug.write('Indexing from images:')
            for i in _images:
                self.add_command_line(self.get_image_name(i))
                Debug.write('%s' % self.get_image_name(i))

            if self._indxr_input_lattice and False:
                lattice_to_spacegroup = {'aP':1,
                                         'mP':3,
                                         'mC':5,
                                         'oP':16,
                                         'oC':20,
                                         'oF':22,
                                         'oI':23,
                                         'tP':75,
                                         'tI':79,
                                         'hP':143,
                                         'hR':146,
                                         'cP':195,
                                         'cF':196,
                                         'cI':197}
                
                self.add_command_line(
                    'known_symmetry=%d' % \
                    lattice_to_spacegroup[self._indxr_input_lattice])

            if self._indxr_input_cell and False:
                self.add_command_line('known_cell=%f,%f,%f,%f,%f,%f' % \
                                      self._indxr_input_cell)

            self._write_dataset_preferences()

            self.start()
            self.close_wait()

            # check for errors
            self.check_for_errors()

            # check for labelit errors - if something went wrong, then
            # try to address it by e.g. extending the beam search area...

            try:
                
                self.check_labelit_errors()
                
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

                    
            # ok now we're done, let's look through for some useful stuff
            output = self.get_all_output()

            counter = 0

            # FIXME 03/NOV/06 something to do with the new centre search...

            # example output:

            # Beam center is not immediately clear; rigorously retesting \
            #                                             2 solutions
            # Beam x 109.0 y 105.1, initial score 538; refined rmsd: 0.1969
            # Beam x 108.8 y 106.1, initial score 354; refined rmsd: 0.1792
            
            # in here want to parse the beam centre search if it was done,
            # and check that the highest scoring solution was declared
            # the "best" - though should also have a check on the
            # R.M.S. deviation of that solution...

            # do this first!

            for j in range(len(output)):
                o = output[j]
                if 'Beam centre is not immediately clear' in o:
                    # read the solutions that it has found and parse the
                    # information

                    centres = []
                    scores = []
                    rmsds = []

                    num_solutions = int(o.split()[-2])

                    for n in range(num_solutions):
                        record = output[j + n + 1].replace(',', ' ').replace(
                            ';', ' ').split()
                        x, y = float(record[2]), \
                               float(record[4])

                        centres.append((x, y))
                        scores.append(int(record[7]))
                        rmsds.append(float(record[-1]))

                    # next perform some analysis and perhaps assert the
                    # correct solution - for the moment just raise a warning
                    # if it looks like wrong solution may have been picked

                    best_beam_score = (0.0, 0.0, 0)
                    best_beam_rms = (0.0, 0.0, 1.0e8)

                    for n in range(num_solutions):
                        beam = centres[n]
                        score = scores[n]
                        rmsd = rmsds[n]

                        if score > best_beam_score[2]:
                            best_beam_score = (beam[0], beam[1], score)

                        if rmsd < best_beam_rmsd[2]:
                            best_beam_rmsd = (beam[0], beam[1], rmsd)

                    # allow a difference of 0.1mm in either direction...
                    if math.fabs(
                        best_beam_score[0] -
                        best_beam_rmsd[0]) > 0.1 or \
                        math.fabs(best_beam_score[1] -
                                  best_beam_rmsd[1]) > 0.1:
                        Chatter.write(
                            'Labelit may have picked the wrong beam centre')

                        # FIXME as soon as I get the indexing loop
                        # structure set up, this should reset the
                        # indexing done flag, set the search range to
                        # 0, correct beam and then return...

                        # should also allow for the possibility that
                        # labelit has selected the best solution - so this
                        # will need to remember the stats for this solution,
                        # then compare them against the stats (one day) from
                        # running with the other solution - eventually the
                        # correct solution will result...
                    
            for o in output:
                l = o.split()

                if l[:3] == ['Beam', 'center', 'x']:
                    x = float(l[3].replace('mm,', ''))
                    y = float(l[5].replace('mm,', ''))
                    
                    self._indxr_refined_beam = (x, y)
                    self._indxr_refined_distance = float(l[7].replace('mm', ''))

                    self._mosaic = float(l[10].replace('mosaicity=', ''))


                if l[:3] == ['Solution', 'Metric', 'fit']:
                    break

                counter += 1

            # if we've just broken out (counter < len(output)) then
            # we need to gather the output

            if counter >= len(output):
                raise RuntimeError, 'error in indexing'

            # FIXME this needs to check the smilie status e.g.
            # ":)" or ";(" or "  ".

            # FIXME need to check the value of the RMSD and raise an
            # exception if the P1 solution has an RMSD > 1.0...

            # Change 27/FEB/08 to support user assigned spacegroups
            # (euugh!) have to "ignore" solutions with higher symmetry
            # otherwise the rest of xia will override us. Bummer.

            lattice_to_spacegroup = {'aP':1, 'mP':3, 'mC':5, 'oP':16,
                                     'oC':20, 'oF':22, 'oI':23, 'tP':75,
                                     'tI':79, 'hP':143, 'hR':146, 'cP':195,
                                     'cF':196, 'cI':197}

            for i in range(counter + 1, len(output)):
                o = output[i][3:]
                smiley = output[i][:3]
                l = o.split()
                if l:

                    if self._indxr_input_lattice:
                        if lattice_to_spacegroup[l[6]] > \
                           lattice_to_spacegroup[self._indxr_input_lattice]:
                            Debug.write('Ignoring solution: %s' % l[6])
                            continue

                    
                    self._solutions[int(l[0])] = {'number':int(l[0]),
                                                  'mosaic':self._mosaic,
                                                  'metric':float(l[1]),
                                                  'rmsd':float(l[3]),
                                                  'nspots':int(l[4]),
                                                  'lattice':l[6],
                                                  'cell':map(float, l[7:13]),
                                                  'volume':int(l[-1]),
                                                  'smiley':smiley}

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
                if self._indxr_other_lattice_cell.has_key(lattice):
                    if self._indxr_other_lattice_cell[lattice]['goodness'] < \
                       self._solutions[solution]['metric']:
                        continue

                self._indxr_other_lattice_cell[lattice] = {
                    'goodness':self._solutions[solution]['metric'],
                    'cell':self._solutions[solution]['cell']}

            self._indxr_lattice = self._solution['lattice']
            self._indxr_cell = tuple(self._solution['cell'])
            self._indxr_mosaic = self._solution['mosaic']

            lms = LabelitMosflmScript()
            lms.set_working_directory(self.get_working_directory())
            lms.set_solution(self._solution['number'])
            self._indxr_payload['mosflm_orientation_matrix'] = lms.calculate()

            # get the beam centre from the mosflm script - mosflm
            # may have inverted the beam centre and labelit will know
            # this!

            mosflm_beam = lms.get_mosflm_beam()

            if mosflm_beam:
                self._indxr_payload['mosflm_beam_centre'] = tuple(mosflm_beam)

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
        
        # things to get results from the indexing

        def get_solutions(self):
            return self._solutions

        def get_solution(self):
            '''Get the best solution from autoindexing.'''
            if self._indxr_input_lattice is None:
                # FIXME in here I need to check that there is a
                # "good" smiley
                return copy.deepcopy(
                    self._solutions[max(self._solutions.keys())])
            else:
                # look through for a solution for this lattice -
                # FIXME should it delete all other solutions?
                # c/f eliminate.
                
                for s in self._solutions.keys():
                    if self._solutions[s]['lattice'] == \
                       self._indxr_input_lattice:
                        return copy.deepcopy(self._solutions[s])
                    else:
                        del(self._solutions[s])

                raise RuntimeError, 'no solution for lattice %s' % \
                      self._indxr_input_lattice

    return LabelitScreenWrapper()

if __name__ == '__main__':

    # run a demo test

    if not os.environ.has_key('XIA2_ROOT'):
        raise RuntimeError, 'XIA2_ROOT not defined'

    l = LabelitScreen()

    directory = os.path.join(os.environ['XIA2_ROOT'],
                             'Data', 'Test', 'Images')

    l.setup_from_image(os.path.join(directory, '12287_1_E1_001.img'))

    # FIXME shouldn't need to do this any more
    l.add_indexer_image_wedge(1)
    l.add_indexer_image_wedge(90)

    l.set_indexer_input_lattice('aP')

    l.index()

    print 'Refined beam is: %6.2f %6.2f' % l.get_indexer_beam()
    print 'Distance:        %6.2f' % l.get_indexer_distance()
    print 'Cell: %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % l.get_indexer_cell()
    print 'Lattice: %s' % l.get_indexer_lattice()
    print 'Mosaic: %6.2f' % l.get_indexer_mosaic()

    print 'Matrix:'
    for m in l.get_indexer_payload('mosflm_orientation_matrix'):
        print m[:-1]
