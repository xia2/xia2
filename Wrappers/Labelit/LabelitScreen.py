#!/usr/bin/env python
# LabelitScreen.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
#
# 2nd June 2006
# 
# A wrapper for labelit.screen - this will provide functionality to:
#
# Decide the beam centre.
# Index the lattce.
# 
# To do:
# 
# (1) Implement setting of beam, wavelength, distance via labelit parameter
#     .py file. [dataset_preferences.py] autoindex_override_beam = (x, y)
#     distance wavelength etc.
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

import os
import sys
import copy

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'
if not os.environ.has_key('DPA_ROOT'):
    raise RuntimeError, 'DPA_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'],
                    'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                                 'Python'))
    
if not os.environ['DPA_ROOT'] in sys.path:
    sys.path.append(os.environ['DPA_ROOT'])

from Driver.DriverFactory import DriverFactory

from Handlers.Syminfo import Syminfo

# interfaces that this inherits from ...
from Schema.Interfaces.FrameProcessor import FrameProcessor
from Schema.Interfaces.Indexer import Indexer

# other labelit things that this uses
from Wrappers.Labelit.LabelitMosflmScript import LabelitMosflmScript
from Wrappers.Labelit.LabelitStats_distl import LabelitStats_distl

from lib.Guff import auto_logfiler

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

            # new feature - index on the spot centre of mass, not the
            # highest pixel (should improve the RMS deviation reports.)

            out.write('distl_spotfinder_algorithm = "maximum_pixel"\n')

            # FIXME latest version of labelit has messed up the beam
            # centre finding :o( so add this for the moment until that
            # is fixed
            
            out.write('beam_search_scope = 0.0\n')
            
            out.close()

            return

        def check_labelit_errors(self):
            '''Check through the standard output for error reports.'''

            output = self.get_all_output()

            for o in output:
                if 'No_Indexing_Solution' in o:
                    raise RuntimeError, 'indexing failed: %s' % \
                          o.split(':')

            return

        def _index_select_images(self):
            '''Select correct images based on image headers.'''

            # FIXME perhaps this should be somewhere central, because
            # Mosflm will share the same implementation

            phi_width = self.get_header_item('phi_width')
            images = self.get_matching_images()

            self.add_indexer_image_wedge(images[0])
            if int(90.0 / phi_width) in images:
                self.add_indexer_image_wedge(int(90.0 / phi_width))
            else:
                self.add_indexer_image_wedge(images[-1])

            return

        def _index(self):
            '''Actually index the diffraction pattern. Note well that
            this is not going to compute the matrix...'''

            self.reset()

            _images = []
            for i in self._indxr_images:
                for j in i:
                    if not j in _images:
                        _images.append(j)
                    
            _images.sort()

            if len(_images) > 2:
                raise RuntimeError, 'cannot use more than 2 images'

            auto_logfiler(self)

            task = 'Autoindex from images:'

            for i in _images:
                task += ' %s' % self.get_image_name(i)

            self.set_task(task)

            self.add_command_line('--index_only')

            for i in _images:
                self.add_command_line(self.get_image_name(i))

            if self._indxr_input_lattice:
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
                                         'cP':195,
                                         'cF':196,
                                         'cI':197}
                
                self.add_command_line(
                    'known_symmetry=%d' % \
                    lattice_to_spacegroup[self._indxr_input_lattice])

            if self._indxr_input_cell:
                self.add_command_line('known_cell=%f,%f,%f,%f,%f,%f' % \
                                      self._indxr_input_cell)

            self._write_dataset_preferences()

            self.start()
            self.close_wait()

            # check for errors
            self.check_for_errors()

            # check for labelit errors
            self.check_labelit_errors()

            # ok now we're done, let's look through for some useful stuff
            output = self.get_all_output()

            counter = 0

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

            for i in range(counter + 1, len(output)):
                o = output[i][3:]
                smiley = output[i][:3]
                l = o.split()
                if l:
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
            if self._solutions[1]['rmsd'] > 1.0:
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

            # also get an estimate of the resolution limit from the
            # labelit.stats_distl output... FIXME the name is wrong!

            lsd = LabelitStats_distl()
            lsd.set_working_directory(self.get_working_directory())
            lsd.stats_distl()

            resolution = 1.0e6
            for i in _images:
                stats = lsd.get_statistics(self.get_image_name(i))
                if stats['resol_one'] < resolution:
                    resolution = stats['resol_one']
                if stats['resol_two'] < resolution:
                    resolution = stats['resol_two']
                    
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
                # look through for a solution for this lattice
                for s in self._solutions.keys():
                    if self._solutions[s]['lattice'] == \
                       self._indxr_input_lattice:
                        return copy.deepcopy(self._solutions[s])

            raise RuntimeError, 'no solution for lattice %s' % \
                  self._indxr_input_lattice

    return LabelitScreenWrapper()

if __name__ == '__main__':

    # run a demo test

    if not os.environ.has_key('DPA_ROOT'):
        raise RuntimeError, 'DPA_ROOT not defined'

    l = LabelitScreen()

    directory = os.path.join(os.environ['DPA_ROOT'],
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
