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
#
# 

import os
import sys
import copy

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                             'Python'))

from Driver.DriverFactory import DriverFactory

from Handlers.Syminfo import Syminfo

def LabelitScreen(DriverType = None):
    '''Factory for LabelitScreen wrapper classes, with the specified
    Driver type.'''

    DriverInstance = DriverFactory.Driver(DriverType)

    class LabelitScreenWrapper(DriverInstance.__class__):
        '''A wrapper for the program labelit.screen - which will provide
        functionality for deciding the beam centre and indexing the
        diffraction pattern.'''

        def __init__(self):

            DriverInstance.__class__.__init__(self)

            self.setExecutable('labelit.screen')

            self._images = []
            self._beam = (0.0, 0.0)
            self._distance = 0.0
            self._wavelength = 0.0

            # control over the behaviour

            self._refine_beam = True

            self._solutions = { }
            self._refined_beam = (0.0, 0.0)
            self._refined_distance = 0.0
            self._mosaic = 0.0

            self._lattice = None

            return

        def addImage(self, image):
            '''Add an image for indexing.'''

            if not image in self._images:
                self._images.append(image)

            return

        def setBeam(self, beam_x, beam_y):
            self._beam = beam_x, beam_y

            return

        def setWavelength(self, wavelength):
            self._wavelength = wavelength

            return
        
        def setDistance(self, distance):
            self._distance = distance

            return

        def setRefine_beam(self, refine_beam):
            self._refine_beam = refine_beam
            
            return

        def setLattice(self, lattice):
            self._lattice = lattice
            return

        def write_dataset_preferences(self):
            '''Write the dataset_preferences.py file in the working
            directory - this will include the beam centres etc.'''

            out = open(os.path.join(self.getWorking_directory(),
                                    'dataset_preferences.py'), 'w')

            if self._distance > 0.0:
                out.write('autoindex_override_distance = %f\n' %
                          self._distance)
            if self._wavelength > 0.0:
                out.write('autoindex_override_wavelength = %f\n' %
                          self._wavelength)
            if self._beam[0] > 0.0 and self._beam[1] > 0.0:
                out.write('autoindex_override_beam = (%f, %f)\n' % \
                          self._beam)
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

        def index(self):
            '''Actually index the diffraction pattern. Note well that
            this is not going to compute the matrix...'''

            self._images.sort()

            if len(self._images) > 2:
                raise RuntimeError, 'cannot use more than 2 images'

            task = 'Autoindex from images:'

            for i in self._images:
                task += ' %s' % i

            self.setTask(task)

            self.addCommand_line('--index_only')

            for i in self._images:
                self.addCommand_line(i)

            self.write_dataset_preferences()

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
                    
                    self._refined_beam = (x, y)
                    self._refined_distance = float(l[7].replace('mm', ''))

                    self._mosaic = float(l[10].replace('mosaicity=', ''))


                if l[:3] == ['Solution', 'Metric', 'fit']:
                    break

                counter += 1

            # if we've just broken out (counter < len(output)) then
            # we need to gather the output

            if counter >= len(output):
                raise RuntimeError, 'error in indexing'

            for i in range(counter + 1, len(output)):
                o = output[i][3:]
                l = o.split()
                if l:
                    self._solutions[int(l[0])] = {'mosaic':self._mosaic,
                                                  'rmsd':float(l[3]),
                                                  'nspots':int(l[4]),
                                                  'lattice':l[6],
                                                  'cell':map(float, l[7:13]),
                                                  'volume':int(l[-1])}

            return 'ok'

        # things to get results from the indexing

        def getSolutions(self):
            '''Get the solutions from indexing.'''
            return self._solutions

        def getSolution(self):
            '''Get the best solution from autoindexing.'''
            if self._lattice is None:
                return copy.deepcopy(
                    self._solutions[max(self._solutions.keys())])
            else:
                # look through for a solution for this lattice
                for s in self._solutions.keys():
                    if self._solutions[s]['lattice'] == self._lattice:
                        return copy.deepcopy(self._solutions[s])

            raise RuntimeError, 'no solution for lattice %s' % self._lattice

        def getBeam(self):
            return self._refined_beam

        def getDistance(self):
            return self._refined_distance

    return LabelitScreenWrapper()

if __name__ == '__main__':

    # run a demo test

    if not os.environ.has_key('DPA_ROOT'):
        raise RuntimeError, 'DPA_ROOT not defined'

    l = LabelitScreen()

    directory = os.path.join(os.environ['DPA_ROOT'],
                             'Data', 'Test', 'Images')

    l.addImage(os.path.join(directory, '12287_1_E1_001.img'))
    l.addImage(os.path.join(directory, '12287_1_E1_090.img'))

    l.index()

    print 'Refined beam is: %6.2f %6.2f' % l.getBeam()
    print 'Distance:        %6.2f' % l.getDistance()

    solutions = l.getSolutions()

    keys = solutions.keys()

    keys.sort()
    keys.reverse()

    for k in keys:
        print 'Lattice: %s Cell: %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % \
              (solutions[k]['lattice'], \
               solutions[k]['cell'][0], \
               solutions[k]['cell'][1], \
               solutions[k]['cell'][2], \
               solutions[k]['cell'][3], \
               solutions[k]['cell'][4], \
               solutions[k]['cell'][5])
              
    
