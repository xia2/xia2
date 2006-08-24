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

            self.setExecutable('labelit.screen')

            # control over the behaviour

            self._refine_beam = True

            self._solutions = { }

            self._solution = None

            return

        # this is not defined in the Indexer interface :o(
        # FIXME should it be???

        def setRefine_beam(self, refine_beam):
            self._refine_beam = refine_beam
            return

        def _write_dataset_preferences(self):
            '''Write the dataset_preferences.py file in the working
            directory - this will include the beam centres etc.'''

            out = open(os.path.join(self.getWorking_directory(),
                                    'dataset_preferences.py'), 'w')

            # only write things out if they have been overridden
            # from what is in the header...

            if self.getDistance_prov() == 'user':
                out.write('autoindex_override_distance = %f\n' %
                          self.getDistance())
            if self.getWavelength_prov() == 'user':
                out.write('autoindex_override_wavelength = %f\n' %
                          self.getWavelength())
            if self.getBeam_prov() == 'user':
                out.write('autoindex_override_beam = (%f, %f)\n' % \
                          self.getBeam())
            if self._refine_beam is False:
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
            '''FIXME this needs to be implemented.'''

            raise RuntimeError, 'I need implementing'

        def _index(self):
            '''Actually index the diffraction pattern. Note well that
            this is not going to compute the matrix...'''

            _images = []
            for i in self._indxr_images:
                for j in i:
                    if not j in _images:
                        _images.append(j)
                    
            _images.sort()

            if len(_images) > 2:
                raise RuntimeError, 'cannot use more than 2 images'

            task = 'Autoindex from images:'

            for i in _images:
                task += ' %s' % self.getImage_name(i)

            self.setTask(task)

            self.addCommand_line('--index_only')

            for i in _images:
                self.addCommand_line(self.getImage_name(i))

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

            for i in range(counter + 1, len(output)):
                o = output[i][3:]
                smiley = output[i][:3]
                l = o.split()
                if l:
                    self._solutions[int(l[0])] = {'number':int(l[0]),
                                                  'mosaic':self._mosaic,
                                                  'rmsd':float(l[3]),
                                                  'nspots':int(l[4]),
                                                  'lattice':l[6],
                                                  'cell':map(float, l[7:13]),
                                                  'volume':int(l[-1]),
                                                  'smiley':smiley}

            # configure the "right" solution
            self._solution = self.getSolution()

            self._indxr_lattice = self._solution['lattice']
            self._indxr_cell = tuple(self._solution['cell'])
            self._indxr_mosaic = self._solution['mosaic']

            lms = LabelitMosflmScript()
            lms.setSolution(self._solution['number'])
            self._indxr_payload['mosflm_orientation_matrix'] = lms.calculate()

            return 'ok'

        # things to get results from the indexing

        def getSolution(self):
            '''Get the best solution from autoindexing.'''
            if self._indxr_lattice is None:
                # FIXME in here I need to check that there is a
                # "good" smiley
                return copy.deepcopy(
                    self._solutions[max(self._solutions.keys())])
            else:
                # look through for a solution for this lattice
                for s in self._solutions.keys():
                    if self._solutions[s]['lattice'] == self._indxr_lattice:
                        return copy.deepcopy(self._solutions[s])

            raise RuntimeError, 'no solution for lattice %s' % \
                  self._indxr_lattice

    return LabelitScreenWrapper()

if __name__ == '__main__':

    # run a demo test

    if not os.environ.has_key('DPA_ROOT'):
        raise RuntimeError, 'DPA_ROOT not defined'

    l = LabelitScreen()

    directory = os.path.join(os.environ['DPA_ROOT'],
                             'Data', 'Test', 'Images')

    l.setup_from_image(os.path.join(directory, '12287_1_E1_001.img'))

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
